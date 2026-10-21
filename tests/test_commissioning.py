"""Commissioning contract and bounded transport tests; no Pi is contacted."""
import base64
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from songsketch.config import Config, private_json
from songsketch.commissioning import (
    CommissioningManager, PACKAGE_FILES, SetupCancelled, SetupError,
    password_channel, protocol_json, scan_key, validate_inputs,
)

INPUTS = {"hostname": "raspberrypi.local", "username": "garden",
          "server_url": "http://192.168.1.20:8765", "latitude": 50.7, "longitude": -2.4}


def public_key(seed=b"a"):
    kind = b"ssh-ed25519"
    blob = len(kind).to_bytes(4, "big") + kind + (32).to_bytes(4, "big") + seed * 32
    return base64.b64encode(blob).decode()


def scan(seed=b"a"):
    return INPUTS["hostname"] + " ssh-ed25519 " + public_key(seed) + "\n"


def response(stdout="", stderr="", returncode=0):
    return {"stdout": stdout, "stderr": stderr, "returncode": returncode}


class CommissioningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = Config(Path(self.temp.name) / "Application Support" / "Songsketch")
        self.package_root = Path(self.temp.name) / "release"
        for name in PACKAGE_FILES:
            path = self.package_root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# bundled test file " + name + "\n")
        self.manager = CommissioningManager(self.config, self.package_root)
        self.calls = []
        self.key_scan = scan()
        self.remote = {"status": "complete", "stage": "verified", "message": "Software checked.",
                       "checks": {"relay": True}, "human_action": "Listen for a real bird.", "next_actions": []}
        self.failure = None
        self.manager._run = self.fake_run
        self.which = patch("songsketch.commissioning.shutil.which", return_value="/usr/bin/ssh")
        self.which.start()

    def tearDown(self):
        self.manager.close()
        self.which.stop()
        self.temp.cleanup()

    def fake_run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        if argv[0] == "ssh-keyscan":
            return response(self.key_scan)
        command = argv[-1]
        if "SONGSKETCH_SSH_OK" in command:
            return self.failure or response("SONGSKETCH_SSH_OK\n")
        if "commission-pi.py" in command:
            if kwargs.get("on_stdout"):
                kwargs["on_stdout"]('SONGSKETCH_PROGRESS {"stage":"capture","progress":70,"message":"Capture checked."}')
            return response(json.dumps(self.remote) + "\n")
        return response()

    def probe(self):
        return self.manager.action("probe", dict(INPUTS), background=False)["job"]

    def trust(self):
        job = self.probe()
        if job["state"] == "ready":
            return job
        challenge = job["challenge"]
        return self.manager.action("trust", {"job_id": job["id"], "challenge_id": challenge["challenge_id"],
                                             "fingerprint": challenge["fingerprint"], "confirmed": True})["job"]

    def install(self, **extra):
        job = self.trust()
        return self.manager.action("install", {"job_id": job["id"], **extra}, background=False)["job"]

    def test_inputs_reject_shell_syntax_and_invalid_coordinates(self):
        bad = [("hostname", "-oProxyCommand=evil"), ("hostname", "pi;id"), ("hostname", "pi..local"),
               ("hostname", "999.999.999.999"), ("username", "garden;id"), ("username", "root -t"),
               ("latitude", float("nan")), ("longitude", float("inf")), ("latitude", True), ("longitude", 181)]
        for key, value in bad:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_inputs({**INPUTS, key: value})
        with self.assertRaises(ValueError):
            validate_inputs({**INPUTS, "password": "not-accepted-here"})
        with self.assertRaises(ValueError):
            self.manager.action("exec", {"command": "id"})
        self.assertEqual(self.calls, [])

    def test_server_url_requires_reachable_root_without_credentials(self):
        for url in ("http://localhost:8765", "http://127.0.0.1:8765", "http://0.0.0.0:8765",
                    "https://u:p@server.local", "http://server.local/path", "http://server.local?x=1",
                    "ftp://server.local", "http://server.local:0", "http://server.local:65536"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_inputs({**INPUTS, "server_url": url})
        clean = validate_inputs({**INPUTS, "server_url": "http://SERVER.local:8765/"})
        self.assertEqual(clean["server_url"], "http://server.local:8765")

    def test_scan_is_only_identity_discovery_not_trust_or_remote_mutation(self):
        job = self.probe()
        self.assertEqual(job["state"], "awaiting_trust")
        self.assertFalse(job["trusted"])
        self.assertEqual([args[0][0] for args in self.calls], ["ssh-keyscan"])
        self.assertFalse(self.manager.known_hosts.exists())
        self.assertTrue(job["challenge"]["fingerprint"].startswith("SHA256:"))
        with self.assertRaisesRegex(ValueError, "trust"):
            self.manager.action("install", {"job_id": job["id"]}, background=False)

    def test_trust_requires_exact_fresh_challenge_and_explicit_confirmation(self):
        job = self.probe()
        challenge = job["challenge"]
        valid = {"job_id": job["id"], "challenge_id": challenge["challenge_id"],
                 "fingerprint": challenge["fingerprint"], "confirmed": True}
        for changes in ({"confirmed": False}, {"fingerprint": "SHA256:wrong"}, {"challenge_id": "stale"}):
            with self.assertRaises(ValueError):
                self.manager.action("trust", {**valid, **changes})
        with patch("songsketch.commissioning.time.time", return_value=challenge["expires_epoch"] + 1):
            with self.assertRaisesRegex(ValueError, "expired"):
                self.manager.action("trust", valid)
        self.assertFalse(self.manager.known_hosts.exists())

    def test_pin_is_private_and_only_exact_saved_key_is_reused(self):
        self.trust()
        self.assertEqual(stat.S_IMODE(self.manager.known_hosts.stat().st_mode), 0o600)
        self.assertEqual(self.probe()["state"], "ready")
        self.key_scan = scan(b"b")
        changed = self.probe()
        self.assertEqual(changed["state"], "awaiting_trust")
        self.assertTrue(changed["challenge"]["changed"])
        self.assertIn(public_key(), self.manager.known_hosts.read_text())

    def test_ambiguous_or_malformed_scan_is_not_trusted(self):
        for output in (scan() + scan(b"b"), "raspberrypi.local ssh-ed25519 rubbish\n", "somewhere.local ssh-ed25519 " + public_key()):
            with self.subTest(output=output), self.assertRaises(SetupError):
                scan_key(output, INPUTS["hostname"])

    def test_ssh_arguments_enforce_pinning_no_shell_options_or_password(self):
        self.trust()
        argv = self.manager._ssh("sudo -n true", "secret-password")
        joined = " ".join(argv)
        self.assertIn("StrictHostKeyChecking=yes", argv)
        self.assertNotIn("StrictHostKeyChecking=no", joined)
        self.assertIn("BatchMode=no", argv)
        self.assertIn("ClearAllForwardings=yes", argv)
        self.assertIn("PermitLocalCommand=no", argv)
        self.assertIn("UserKnownHostsFile=" + json.dumps(str(self.manager.known_hosts)), argv)
        self.assertNotIn("secret-password", joined)
        self.assertEqual(argv[-2], "raspberrypi.local")

    def test_install_uses_only_bundled_archive_and_secret_stdin(self):
        job = self.install(password="temporary-password")
        self.assertEqual(job["state"], "completed")
        self.assertTrue(job["commissioned"])
        self.assertIsNotNone(job["last_successful_install"])
        self.assertEqual(job["progress"], 100)
        self.assertTrue(job["result"]["checks"]["relay"])
        archive = next(kw["input_bytes"] for argv, kw in self.calls if "tar -xzf" in argv[-1])
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            self.assertEqual(set(bundle.getnames()), set(PACKAGE_FILES))
            self.assertTrue(all(item.mode == 0o600 for item in bundle.getmembers()))
        provision_calls = [(a, k) for a, k in self.calls if a[-1].endswith(" --provision -")]
        self.assertEqual(len(provision_calls), 1)
        argv, kw = provision_calls[0]
        payload = json.loads(kw["input_bytes"])
        self.assertEqual(payload["token"], self.config.secrets["station_token"])
        self.assertEqual(payload["latitude"], 50.7)
        self.assertNotIn("temporary-password", " ".join(argv))
        self.assertNotIn(payload["token"], " ".join(argv))
        saved = self.manager.state_path.read_text()
        self.assertNotIn("temporary-password", saved)
        self.assertNotIn(payload["token"], saved)
        self.assertEqual(stat.S_IMODE(self.manager.state_path.stat().st_mode), 0o600)
        self.assertEqual(job["remote_progress"]["stage"], "capture")

    def test_remote_results_and_logs_redact_nested_credentials(self):
        password = "one-use-password"
        token = self.config.secrets["station_token"]
        self.remote.update(message="Received " + password + " and " + token,
                           checks={"token": token, "nested": {"password": password, "detail": "Bearer private-value"}})
        job = self.install(password=password)
        serialized = json.dumps(job) + self.manager.state_path.read_text()
        self.assertNotIn(password, serialized)
        self.assertNotIn(token, serialized)
        self.assertNotIn("private-value", serialized)
        self.assertNotIn("token", job["result"]["checks"])
        self.assertNotIn("password", job["result"]["checks"]["nested"])

    def test_password_matching_protocol_words_cannot_change_success_or_lock_state(self):
        job = self.install(password="complete")
        self.assertEqual(job["state"], "completed")
        self.assertTrue(job["commissioned"])
        self.assertEqual(job["result"]["status"], "complete")
        self.remote = {"status": "needs_input", "code": "commissioning_in_progress"}
        job = self.manager.action("retry", {"job_id": job["id"], "password": "in"}, background=False)["job"]
        self.assertEqual(job["state"], "needs_input")
        self.assertTrue(job["result"]["operation_running"])
        self.assertEqual(job["next_actions"], ["diagnose"])

    def test_non_finite_remote_json_cannot_poison_public_status(self):
        self.remote = {"status": "complete", "checks": {"bad": float("nan")}}
        job = self.install()
        self.assertEqual(job["state"], "failed")
        self.assertEqual(job["error"]["code"], "missing_result")
        json.dumps(self.manager.status(), allow_nan=False)
        for value in ("NaN", "Infinity", "-Infinity", "1e400", "-1e400"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                protocol_json('{"checks":{"value":' + value + '}}')

    def test_capture_choice_is_exact_discovered_id_and_retry_is_explicit(self):
        self.remote = {"status": "needs_input", "stage": "capture_choice", "message": "Choose a microphone.",
                       "capture_sources": [{"id": "usb:stable-1", "name": "Garden microphone"}]}
        job = self.install()
        self.assertEqual(job["state"], "needs_input")
        installs = len([a for a, _ in self.calls if a[-1].endswith(" --provision -")])
        time.sleep(.01)
        self.assertEqual(installs, 1)
        with self.assertRaisesRegex(ValueError, "exact capture"):
            self.manager.action("retry", {"job_id": job["id"], "capture_device": "usb:evil;id"}, background=False)
        self.remote = {"status": "complete", "message": "Microphone configured."}
        job = self.manager.action("retry", {"job_id": job["id"], "capture_device": "usb:stable-1"}, background=False)["job"]
        self.assertEqual(job["state"], "completed")
        provision = [k for a, k in self.calls if a[-1].endswith(" --provision -")][-1]
        self.assertEqual(json.loads(provision["input_bytes"])["capture_device"], "usb:stable-1")

    def test_auth_hostkey_and_sudo_failures_stop_before_transfer(self):
        for stderr, code in (("Permission denied (publickey).", "authentication_failed"),
                             ("Host key verification failed.", "host_key_changed"),
                             ("sudo: a password is required", "sudo_required")):
            with self.subTest(code=code):
                self.calls.clear()
                self.failure = response(stderr=stderr, returncode=255)
                job = self.install()
                self.assertEqual(job["state"], "failed")
                self.assertEqual(job["error"]["code"], code)
                self.assertFalse(any("tar -xzf" in a[-1] for a, _ in self.calls))

    def test_diagnose_uses_only_fixed_read_only_entrypoint_and_no_token(self):
        job = self.trust()
        self.remote = {"status": "diagnostic", "stage": "diagnostics", "operation_running": False,
                       "checks": {"audio": "unknown"}}
        status = self.manager.action("diagnose", {"job_id": job["id"]}, background=False)["job"]
        self.assertEqual(status["state"], "completed")
        self.assertEqual(status["result"]["status"], "diagnostic")
        self.assertFalse(status["commissioned"])
        self.assertIsNone(status["last_successful_install"])
        self.assertNotIn("installation_result", status)
        diagnostic = [(a, k) for a, k in self.calls if "commission-pi.py" in a[-1]]
        self.assertEqual(len(diagnostic), 1)
        self.assertTrue(diagnostic[0][0][-1].endswith(" --diagnose"))
        self.assertIsNone(diagnostic[0][1]["input_bytes"])
        self.assertFalse(any(a[-1].endswith(" --provision -") for a, _ in self.calls))

    def test_diagnose_preserves_successful_install_evidence_without_claiming_new_install(self):
        installed = self.install()
        evidence = installed["last_successful_install"]
        self.remote = {"status": "diagnostic", "operation_running": False, "checks": {"audio": "unknown"}}
        snapshot = self.manager.action("diagnose", {"job_id": installed["id"]}, background=False)["job"]
        self.assertTrue(snapshot["commissioned"])
        self.assertEqual(snapshot["last_successful_install"], evidence)
        self.assertEqual(snapshot["installation_result"]["status"], "complete")
        self.assertEqual(snapshot["result"]["status"], "diagnostic")

    def test_diagnostic_missing_choices_retains_but_explicit_empty_clears_choices(self):
        self.remote = {"status": "needs_input", "capture_sources": [{"id": "usb:one", "name": "Mic"}]}
        job = self.install()
        self.remote = {"status": "diagnostic", "operation_running": False}
        snapshot = self.manager.action("diagnose", {"job_id": job["id"]}, background=False)["job"]
        self.assertEqual(snapshot["result"]["capture_sources"][0]["id"], "usb:one")
        self.remote["capture_sources"] = []
        snapshot = self.manager.action("diagnose", {"job_id": job["id"]}, background=False)["job"]
        self.assertEqual(snapshot["result"]["capture_sources"], [])

    def test_active_remote_operation_requires_wait_and_diagnose_before_retry(self):
        job = self.trust()
        self.remote = {"status": "diagnostic", "operation_running": True, "checks": {}}
        status = self.manager.action("diagnose", {"job_id": job["id"]}, background=False)["job"]
        self.assertEqual(status["state"], "needs_input")
        self.assertEqual(status["next_actions"], ["diagnose"])
        with self.assertRaisesRegex(ValueError, "still reports an active"):
            self.manager.action("retry", {"job_id": job["id"]}, background=False)
        self.remote["operation_running"] = False
        self.manager.action("diagnose", {"job_id": job["id"]}, background=False)
        self.remote = {"status": "complete", "message": "Finished."}
        self.assertEqual(self.manager.action("retry", {"job_id": job["id"]}, background=False)["job"]["state"], "completed")

    def test_timeout_does_not_remove_files_remote_installer_may_still_use(self):
        original = self.fake_run
        def timed_out(argv, **kwargs):
            if "commission-pi.py" in argv[-1]:
                self.calls.append((argv, kwargs))
                raise SetupError("operation_timeout", "Timed out.")
            return original(argv, **kwargs)
        self.manager._run = timed_out
        job = self.install()
        self.assertEqual(job["state"], "failed")
        self.assertFalse(any(a[-1].startswith("rm -rf") for a, _ in self.calls))
        self.assertTrue(any("completion is unconfirmed" in row["message"] for row in job["logs"]))

    def test_missing_or_invalid_final_result_never_claims_completion(self):
        original = self.fake_run
        def missing(argv, **kwargs):
            if "commission-pi.py" in argv[-1]:
                self.calls.append((argv, kwargs))
                return response("something finished\n")
            return original(argv, **kwargs)
        self.manager._run = missing
        job = self.install()
        self.assertEqual(job["state"], "failed")
        self.assertEqual(job["error"]["code"], "missing_result")
        self.assertIn("diagnostics", job["human_action"])

    def test_restart_marks_pending_job_interrupted_without_remote_calls(self):
        self.trust()
        saved = dict(self.manager.job, state="running", stage="provision")
        private_json(self.manager.state_path, saved)
        before = len(self.calls)
        restarted = CommissioningManager(self.config, self.package_root)
        self.assertEqual(restarted.status()["job"]["state"], "interrupted")
        self.assertEqual(len(self.calls), before)
        self.assertIsNone(restarted.thread)
        self.assertIn("explicitly", restarted.status()["job"]["human_action"])
        restarted.close()

    def test_late_cancel_does_not_reopen_a_completed_job(self):
        job = self.install()
        status = self.manager.action("cancel", {"job_id": job["id"]})["job"]
        self.assertEqual(status["state"], "completed")
        self.assertTrue(status["commissioned"])

    def test_one_active_job_and_cancellation_are_bounded(self):
        entered = threading.Event()
        def blocked(argv, **kwargs):
            entered.set()
            while not self.manager.cancel_event.wait(.01):
                pass
            raise SetupCancelled()
        self.manager._run = blocked
        job = self.manager.action("probe", dict(INPUTS))["job"]
        self.assertTrue(entered.wait(2))
        with self.assertRaisesRegex(ValueError, "already running"):
            self.manager.action("probe", dict(INPUTS))
        self.manager.action("cancel", {"job_id": job["id"]})
        self.manager.thread.join(2)
        self.assertFalse(self.manager.thread.is_alive())
        self.assertEqual(self.manager.status()["job"]["state"], "cancelled")
        self.assertIn("may finish", self.manager.status()["job"]["human_action"])

    def test_package_rejects_missing_files_and_symlinks(self):
        target = self.package_root / PACKAGE_FILES[0]
        target.unlink()
        with self.assertRaisesRegex(SetupError, "missing"):
            self.manager._package()
        target.symlink_to(self.package_root / PACKAGE_FILES[1])
        with self.assertRaisesRegex(SetupError, "missing"):
            self.manager._package()


@unittest.skipUnless(os.name == "posix", "OpenSSH askpass transport requires POSIX")
class LocalTransportTests(unittest.TestCase):
    def test_password_uses_owner_only_fifo_and_helper_has_no_secret(self):
        secret = "local-test-password-do-not-save"
        with password_channel(secret) as env:
            helper = Path(env["SSH_ASKPASS"])
            folder = helper.parent
            fifo = Path(env["SONGSKETCH_ASKPASS_FIFO"])
            self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)
            self.assertTrue(stat.S_ISFIFO(fifo.stat().st_mode))
            self.assertEqual(stat.S_IMODE(fifo.stat().st_mode), 0o600)
            self.assertNotIn(secret, helper.read_text())
            self.assertNotIn(secret, json.dumps(env))
            out = subprocess.run([str(helper), "garden@pi's password:"], env={**os.environ, **env},
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
            self.assertEqual(out.returncode, 0)
            self.assertEqual(out.stdout, (secret + "\n").encode())
        self.assertFalse(folder.exists())

    def test_password_helper_refuses_host_confirmation_or_key_passphrase(self):
        with password_channel("temporary") as env:
            for prompt in ("Are you sure you want to continue connecting?", "Enter passphrase for key:"):
                out = subprocess.run([env["SSH_ASKPASS"], prompt], env={**os.environ, **env},
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
                self.assertNotEqual(out.returncode, 0)
                self.assertEqual(out.stdout, b"")

    def test_runner_streams_progress_and_stdin_without_shell(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = CommissioningManager(Config(folder))
            seen = []
            script = "import sys; x=sys.stdin.buffer.read(); print('SONGSKETCH_PROGRESS {\\\"progress\\\":50}',flush=True); print(len(x))"
            result = manager._run([sys.executable, "-c", script], input_bytes=b"safe input", timeout=3, on_stdout=seen.append)
            self.assertEqual(result["returncode"], 0)
            self.assertTrue(any(line.startswith("SONGSKETCH_PROGRESS") for line in seen))
            self.assertIn("10", result["stdout"])
            self.assertIsNone(manager.process)
            manager.close()

    def test_runner_timeout_reaps_only_its_owned_process(self):
        with tempfile.TemporaryDirectory() as folder:
            manager = CommissioningManager(Config(folder))
            start = time.monotonic()
            with self.assertRaises(SetupError) as caught:
                manager._run([sys.executable, "-c", "import time; time.sleep(10)"], timeout=.15)
            self.assertEqual(caught.exception.code, "operation_timeout")
            self.assertLess(time.monotonic() - start, 4)
            self.assertIsNone(manager.process)
            manager.close()


if __name__ == "__main__":
    unittest.main()
