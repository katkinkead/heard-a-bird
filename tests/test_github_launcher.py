"""No GitHub, AI session, Terminal window, account login or installer is run."""
import base64
import json
import io
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from songsketch import github_launcher as g


def required_files(directory):
    (directory / ".git").mkdir(exist_ok=True)
    for name in g.REQUIRED_FILES:
        target = directory / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("trusted project material\n")


class FakeGit:
    def __init__(self):
        self.calls = []; self.status = ""; self.branch = "main"; self.origin = g.HTTPS_URL
        self.ancestor = 0; self.clone_code = 0; self.rewrites = ""; self.accessible = True

    def __call__(self, args, cwd=None, env=None, **kwargs):
        self.calls.append((args, cwd, env))
        code, output = 0, ""
        command = next((i for i, arg in enumerate(args) if arg in ("config", "clone", "fetch", "merge", "merge-base", "status", "symbolic-ref", "rev-parse", "ls-remote")), None)
        if command is None: return subprocess.CompletedProcess(args, 0, "", "")
        tail = args[command:]
        if tail[:2] == ["config", "--get-regexp"]: output = self.rewrites
        elif tail[:2] == ["config", "--get-all"]: output = self.origin + "\n"
        elif tail[0] == "symbolic-ref": output = self.branch + "\n"
        elif tail[0] == "status": output = self.status
        elif tail[0] == "merge-base": code = self.ancestor
        elif tail[0] == "rev-parse": output = "a" * 40 + "\n"
        elif tail[0] == "ls-remote":
            code = 0 if self.accessible else 128
            output = "a" * 40 + "\trefs/heads/main\n" if self.accessible else ""
        elif tail[0] == "clone":
            code = self.clone_code
            if code == 0: required_files(Path(tail[-1]))
        return subprocess.CompletedProcess(args, code, output, "")

    def used(self, command): return any(command in args for args, _, _ in self.calls)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name).resolve()
        self.fake = FakeGit(); self.git = g.GitSource("/usr/bin/git", self.fake)

    def tearDown(self): self.temp.cleanup()

    def checkout(self):
        directory = self.root / "setup-source"; directory.mkdir(mode=0o700); required_files(directory)
        return directory

    def test_nonsecret_details_allow_missing_location_and_reject_credentials(self):
        values = {"hostname": "garden.local", "username": "garden", "garden_location": "Dorset; $(not-a-command) 'garden'"}
        self.assertEqual(g.validate_details(values), values)
        self.assertNotIn("latitude", g.validate_details(values))
        for extra in ({"token": "private"}, {"password": "secret"}, {"latitude": float("nan")},
                      {"username": "a;command"}, {"hostname": "pi@other"}, {"server_url": "http://secret:password@host"}):
            with self.assertRaises(g.LaunchError): g.validate_details(dict(values, **extra))

    def test_download_embeds_data_without_shell_interpolation_and_has_valid_syntax(self):
        data = {"garden_location": "Dorset ' $(touch unwanted) `command`", "hostname": "garden.local"}
        payload = g.download_command(data, "claude", self.root / "a folder ' $()")
        line = next(x for x in payload.decode().splitlines() if x.startswith("export SONGSKETCH_LAUNCH_DETAILS_B64="))
        encoded = line.split("='", 1)[1][:-1]
        self.assertEqual(json.loads(base64.b64decode(encoded)), data)
        self.assertNotIn("touch unwanted", payload.decode())
        self.assertIn("export SONGSKETCH_LAUNCH_ASSISTANT='claude'", payload.decode())
        script = self.root / "download.command"; script.write_bytes(payload)
        result = subprocess.run(["/bin/bash", "-n", str(script)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())

    def test_template_has_first_assignment_markers_for_offline_guide(self):
        text = g.download_template().decode()
        for marker in (g.DETAILS_MARKER, g.ASSISTANT_MARKER, g.DATA_MARKER):
            first = text.index(marker)
            self.assertIn("export SONGSKETCH_", text[text.rfind("\n", 0, first) + 1:first])

    def test_zip_preserves_executable_bit_for_browser_delivery(self):
        with zipfile.ZipFile(io.BytesIO(g.download_zip({"hostname": "garden.local"}))) as archive:
            self.assertEqual(archive.namelist(), ["Install Songsketch.command"])
            item = archive.infolist()[0]
            self.assertEqual(item.create_system, 3)
            self.assertEqual((item.external_attr >> 16) & 0o777, 0o700)
            self.assertEqual(archive.read(item), g.download_command({"hostname": "garden.local"}))

    @unittest.skipUnless(shutil.which("node"), "Node is required to exercise the standalone guide's ZIP writer")
    def test_actual_standalone_guide_zip_contains_valid_executable_launcher(self):
        source = (Path(__file__).resolve().parents[1] / "guide/assets/guide.js").read_text()
        function = source[source.index("function launcherZip("):source.index("async function launchAssistant(")]
        command = g.download_command({"hostname": "test-pi.local", "garden_location": "A garden ' $()"}).decode()
        javascript = function + '\nlet data="";process.stdin.on("data",s=>data+=s);process.stdin.on("end",()=>process.stdout.write(Buffer.from(launcherZip(JSON.parse(data)))));'
        result = subprocess.run([shutil.which("node"), "-e", javascript], input=json.dumps(command).encode(), capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        with zipfile.ZipFile(io.BytesIO(result.stdout)) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(archive.namelist(), ["Install Songsketch.command"])
            item = archive.infolist()[0]
            self.assertEqual(item.create_system, 3); self.assertEqual((item.external_attr >> 16) & 0o777, 0o700)
            self.assertEqual(archive.read(item), command.encode())
            target = self.root / "download.command"; target.write_bytes(archive.read(item))
            syntax = subprocess.run(["/bin/bash", "-n", str(target)], capture_output=True)
            self.assertEqual(syntax.returncode, 0, syntax.stderr.decode())

    def test_private_details_and_atomic_status_never_claim_installation(self):
        path = self.root / "setup-details.json"
        g.private_write(path, {"hostname": "garden.local"})
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(g.read_details(path), {"hostname": "garden.local"})
        g.write_status(self.root, "assistant_started", commit="a" * 40)
        result = json.loads((self.root / "launcher-status.json").read_text())
        self.assertFalse(result["installation_verified"])
        self.assertEqual(result["repository"], g.REPOSITORY)
        path.chmod(0o644)
        with self.assertRaises(g.LaunchError): g.read_details(path)

    def test_notification_preference_import_is_private_and_does_not_send_mail(self):
        spec = importlib.util.spec_from_file_location("bootstrap_launcher_test", Path(__file__).resolve().parents[1] / "scripts/ai-bootstrap.py")
        bootstrap = importlib.util.module_from_spec(spec); spec.loader.exec_module(bootstrap)
        g.private_write(self.root / "setup-details.json", {"hostname": "garden.local", "notification_email": "recipient@example.test"})
        client = mock.Mock(); client.request.return_value = {"ok": True}
        result = bootstrap.apply_saved_setup_preferences(client, self.root)
        client.request.assert_called_once_with("/api/admin/settings", {"notification_email": "recipient@example.test"})
        self.assertNotIn("recipient@example.test", json.dumps(result))
        self.assertTrue(result["notification_recipient_saved"]); self.assertFalse(result["email_delivery_verified"])
        with self.assertRaises(g.LaunchError): g.validate_details({"notification_email": "bad\naddress@example.test"})

    def test_terminal_handoff_uses_fixed_argv_and_private_command(self):
        odd_path = self.root / "folder ' $(not-executed)"
        with mock.patch.object(g.sys, "platform", "darwin"), mock.patch.object(g, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            result = g.open_terminal({"hostname": "garden.local"}, "codex", odd_path)
        args = run.call_args.args[0]
        self.assertEqual(args[:3], ["/usr/bin/open", "-a", "Terminal"])
        target = Path(args[3]); self.assertEqual(target.parent, odd_path / "launchers")
        self.assertEqual(target.stat().st_mode & 0o777, 0o700)
        self.assertTrue(result["launched"]); self.assertFalse(result["installation_verified"])
        self.assertFalse((odd_path / "setup-details.json").exists())
        self.assertFalse((odd_path / "launcher-status.json").exists())

    def test_running_assistant_preserves_shared_values_and_rejects_second_terminal(self):
        g.private_write(self.root / "setup-details.json", {"hostname": "first.local"})
        g.write_status(self.root, "assistant_started")
        before = {p.name: p.read_bytes() for p in self.root.glob("*.json")}
        self.assertFalse(g.launcher_running(self.root))
        with g.setup_details_lock(self.root):
            self.assertTrue(g.launcher_running(self.root))
            with mock.patch.object(g.sys, "platform", "darwin"), mock.patch.object(g, "run") as run:
                with self.assertRaises(g.LaunchError) as error:
                    g.open_terminal({"hostname": "second.local"}, data_dir=self.root)
                self.assertEqual(error.exception.code, "launcher_running"); run.assert_not_called()
            with self.assertRaises(g.LaunchError):
                with g.setup_details_lock(self.root): self.fail("Must not acquire active session lock")
        self.assertFalse(g.launcher_running(self.root))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.glob("*.json")})

    def test_git_access_probe_has_short_timeout_and_timeout_allows_auth_fallback(self):
        runner = mock.Mock(side_effect=g.LaunchError("command_unavailable", "timeout"))
        source = g.GitSource("git", runner)
        self.assertFalse(source.accessible(g.HTTPS_URL))
        self.assertEqual(runner.call_args.kwargs["timeout"], 30)
        self.assertIn("ConnectTimeout=10", source.env["GIT_SSH_COMMAND"])

    def test_failure_before_session_lock_cannot_overwrite_another_status(self):
        g.write_status(self.root, "assistant_started")
        before = (self.root / "launcher-status.json").read_bytes()
        with mock.patch.object(g, "data_directory", return_value=self.root), mock.patch.object(g.sys, "platform", "linux"), mock.patch.object(g.sys, "stderr", io.StringIO()):
            self.assertEqual(g.main([]), 1)
        self.assertEqual((self.root / "launcher-status.json").read_bytes(), before)

    def test_foreign_url_ref_and_symlink_are_not_accepted(self):
        for url in ("https://github.com.evil/katkinkead/songsketch.git", "file:///tmp/repo", "https://token@github.com/katkinkead/songsketch.git", g.HTTPS_URL + "#other"):
            with self.assertRaises(g.LaunchError): self.git.prepare(self.root / "checkout", url)
        target = self.root / "target"; target.mkdir(); link = self.root / "link"; link.symlink_to(target)
        with self.assertRaises(g.LaunchError): self.git.prepare(link, g.HTTPS_URL)
        self.assertFalse(self.fake.used("clone"))

    def test_existing_dirty_foreign_or_other_branch_is_preserved(self):
        directory = self.checkout(); marker = directory / "README.md"; before = marker.read_bytes()
        for attr, value, code in (("status", " M README.md\n", "checkout_has_changes"),
                                  ("branch", "my-local-work", "checkout_branch_changed"),
                                  ("origin", "https://github.com/other/project.git", "foreign_checkout")):
            previous = getattr(self.fake, attr); setattr(self.fake, attr, value)
            with self.assertRaises(g.LaunchError) as error: self.git.prepare(directory, g.HTTPS_URL)
            self.assertEqual(error.exception.code, code)
            self.assertFalse(self.fake.used("fetch")); self.assertEqual(marker.read_bytes(), before)
            setattr(self.fake, attr, previous)

    def test_diverged_history_never_resets_or_merges(self):
        directory = self.checkout(); self.fake.ancestor = 1
        with self.assertRaises(g.LaunchError) as error: self.git.prepare(directory, g.HTTPS_URL)
        self.assertEqual(error.exception.code, "checkout_diverged")
        self.assertFalse(self.fake.used("reset")); self.assertFalse(self.fake.used("merge"))

    def test_safe_repeat_is_main_only_fast_forward_and_disables_git_hooks(self):
        directory = self.checkout()
        self.assertEqual(self.git.prepare(directory, g.HTTPS_URL), "a" * 40)
        merge = next(args for args, _, _ in self.fake.calls if "merge" in args)
        self.assertIn("--ff-only", merge); self.assertIn("core.hooksPath=/dev/null", merge)
        fetched = next(args for args, _, _ in self.fake.calls if "fetch" in args)
        self.assertIn(g.HTTPS_URL, fetched)
        self.assertIn("+refs/heads/main:refs/remotes/origin/main", fetched)

    def test_clone_is_atomic_and_failed_stage_cleanup_preserves_other_folders(self):
        directory = self.root / "setup-source"; unrelated = self.root / "keep"; unrelated.write_text("keep")
        self.fake.clone_code = 1
        with self.assertRaises(g.LaunchError): self.git.prepare(directory, g.HTTPS_URL)
        self.assertFalse(directory.exists()); self.assertEqual(unrelated.read_text(), "keep")
        self.assertFalse(list(self.root.glob(".songsketch-source-*")))
        self.fake.clone_code = 0
        self.assertEqual(self.git.prepare(directory, g.HTTPS_URL), "a" * 40)
        self.assertTrue((directory / "AGENTS.md").is_file())

    def test_git_url_rewrite_and_environment_cannot_redirect_the_fixed_repository(self):
        self.fake.rewrites = "url.https://other.invalid/.insteadof https://github.com/\n"
        with self.assertRaises(g.LaunchError) as error: self.git.authenticate()
        self.assertEqual(error.exception.code, "git_url_rewrite")
        self.assertFalse(self.fake.used("ls-remote"))
        with mock.patch.dict(os.environ, {"GIT_DIR": "/other/repo", "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "http.sslVerify", "GIT_CONFIG_VALUE_0": "false"}):
            client = g.GitSource("git", self.fake)
        self.assertNotIn("GIT_DIR", client.env); self.assertNotIn("GIT_CONFIG_COUNT", client.env)
        self.assertIn("StrictHostKeyChecking=yes", client.env["GIT_SSH_COMMAND"])

    def test_normal_interactive_ai_flags_and_short_repo_pointer(self):
        calls = []
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(args, 0, "--cd --sandbox --ask-for-approval --permission-mode \"manual\"")
        for name in ("codex", "claude"):
            calls.clear(); started = []
            result = g.launch_assistant(name, "/a path/" + name, self.root, self.root / "details ' $().json", runner, lambda: started.append(True))
            self.assertEqual(result, 0); self.assertEqual(started, [True])
            args, kwargs = calls[-1]
            self.assertTrue(kwargs["interactive"]); self.assertEqual(kwargs["cwd"], self.root)
            self.assertIn("docs/ai-setup.md", args[-1]); self.assertLess(len(args[-1]), 1000)
            self.assertNotIn("--print", args); self.assertNotIn("--dangerously-skip-permissions", args)
            self.assertNotIn("never", args); self.assertNotIn("danger-full-access", args)
            self.assertIn("on-request" if name == "codex" else "manual", args)

    def test_custom_runtime_directory_reaches_ai_prompt_environment_and_bootstrap(self):
        runtime = self.root / "custom data ' $()"; calls = []
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(args, 0, "--cd --sandbox --ask-for-approval")
        g.launch_assistant("codex", "/tool/codex", self.root / "checkout", None, runner, data_dir=runtime)
        args, options = calls[-1]
        self.assertIn(json.dumps(str(runtime)), args[-1]); self.assertIn("--data-dir", args[-1])
        self.assertEqual(options["env"]["SONGSKETCH_DATA_DIR"], str(runtime))
        from songsketch.config import data_directory
        with mock.patch.dict(os.environ, options["env"], clear=True):
            self.assertEqual(data_directory(), runtime.resolve())
        self.assertFalse(runtime.exists())

    def test_explicit_launcher_path_takes_precedence_over_inherited_runtime_path(self):
        encoded = base64.b64encode(str(self.root / "chosen").encode()).decode()
        with mock.patch.dict(os.environ, {"SONGSKETCH_LAUNCH_DATA_DIR_B64": encoded, "SONGSKETCH_DATA_DIR": str(self.root / "old")}):
            self.assertEqual(g.data_directory(), self.root / "chosen")
        with mock.patch.dict(os.environ, {"SONGSKETCH_LAUNCH_DATA_DIR_B64": "", "SONGSKETCH_DATA_DIR": str(self.root / "old")}):
            self.assertEqual(g.data_directory(), self.root / "old")

    def test_signin_is_normal_interactive_command_without_secret_arguments(self):
        calls = []
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            code = 1 if args[-1] == "status" else 0
            return subprocess.CompletedProcess(args, code, "--cd --sandbox --ask-for-approval")
        g.launch_assistant("codex", "/tool/codex", self.root, None, runner)
        self.assertIn((["/tool/codex", "login"], {"interactive": True}), calls)
        self.assertFalse(any("--with-api-key" in args or "--with-token" in args for args, _ in calls))


if __name__ == "__main__": unittest.main()
