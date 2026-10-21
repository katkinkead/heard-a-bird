"""Commissioning contract/recovery tests. No real Pi, sudo, Docker or network.

The one HTTP test binds loopback only and verifies real CSRF/cookie transport.
These tests do not establish microphone quality or physical Pi readiness.
"""
import copy
import datetime as dt
import fcntl
import http.server
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location("commission_pi", Path(__file__).resolve().parents[1] / "scripts/commission-pi.py")
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)


def provision(**changes):
    value = {"schema_version": 1, "server_url": "http://192.168.1.20:8765", "station_id": "garden",
             "token": "private-station-token-not-in-output", "latitude": 50.72, "longitude": -2.44,
             "timezone": "Europe/London", "use_existing_birdnet": False}
    return dict(value, **changes)


def initial_settings():
    return {"birdnet": {"latitude": 0, "longitude": 0, "locale": "en-us", "threshold": .7},
            "models": {"enabled": ["birdnet"]},
            "realtime": {"rtsp": {"streams": []}, "daylightFilter": {"enabled": True},
                         "audio": {"sources": [{"name": "Microphone", "device": "sysdefault", "gain": 1.5}],
                                   "quietHours": {"enabled": True}, "export": {"enabled": True}}},
            "output": {"sqlite": {"enabled": True, "path": "precious-existing-history.db"},
                       "mysql": {"enabled": False}}}


def merge(target, patch):
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(target.get(k), dict): merge(target[k], v)
        else: target[k] = copy.deepcopy(v)


def omit_go_empty(value):
    if isinstance(value, list): return [omit_go_empty(v) for v in value]
    if isinstance(value, dict):
        return {k: omit_go_empty(v) for k, v in value.items() if not (k in ("source", "model") and v == "")}
    return value


class FakeBirdNET:
    def __init__(self):
        self.settings = initial_settings()
        self.devices = [{"id": "USB Audio,0", "name": "USB Audio Capture", "stableId": "usb-path:1-1.3", "busPath": "1-1.3"}]
        self.calls = []; self.counter = 0; self.advance = True; self.healthy = True
        self.skip_fields = False; self.restart_required = False; self.base = int(time.time()) - 20
        self.bootstrap_error = None; self.audio_error_once = False

    def bootstrap(self):
        if self.bootstrap_error: raise self.bootstrap_error
        return {"version": "20261014", "csrfToken": "local-csrf", "security": {"enabled": False}}

    def request(self, path, method="GET", body=None):
        self.calls.append((path, method, copy.deepcopy(body)))
        if path == "/api/v2/settings": return copy.deepcopy(self.settings)
        if path.startswith("/api/v2/settings/"):
            section = path.rsplit("/", 1)[-1]
            target = self.settings[section] if section != "audio" else self.settings["realtime"]["audio"]
            if method == "PATCH":
                if not self.skip_fields: merge(target, body)
                return {"skippedFields": ["unexpected"] if self.skip_fields else [], "restart_required": self.restart_required}
            return omit_go_empty(copy.deepcopy(target))
        if path == "/api/v2/system/audio/devices": return copy.deepcopy(self.devices)
        if path == "/api/v2/health/audio":
            if self.audio_error_once:
                self.audio_error_once = False
                raise c.CommissionError("birdnet_unreachable", "Temporary local API outage", status="failed")
            return {"sources": [{"source_id": "capture-one", "state": "HEALTHY" if self.healthy else "FAILED",
                                 "last_dispatch": dt.datetime.now(dt.timezone.utc).isoformat()}]}
        if path == "/api/v2/system/inference":
            if self.advance: self.counter += 1
            return {"models": [{"id": "BirdNET_V2.4", "sources": [{"id": "capture-one"}],
                                "health": {"state": "ok", "lastSuccessAtUnix": self.base + self.counter}}]}
        if path == "/api/v2/detections?numResults=1": return {"data": [], "total": 0}
        if path == "/api/v2/app/wizard/dismiss": return {}
        raise AssertionError("Unexpected test API path: " + path)


class FakeSystem:
    def __init__(self, owned=True):
        self.is_owned = owned; self.installed = 0; self.restarts = 0; self.started = 0; self.backups = 0
        self.on_restart = lambda: None

    def owned(self): return self.is_owned
    def can_restart(self): return self.is_owned
    def timezone(self): return "Europe/London"
    def preflight(self, p): pass
    def install(self, p): self.installed += 1
    def backup_config(self): self.backups += 1
    def restart_birdnet(self):
        self.restarts += 1; self.on_restart(); return True
    def start_relay(self): self.started += 1; return True
    def relay_evidence(self, p): return {"audio_status": "healthy", "inference_status": "healthy", "last_poll": "now"}
    def run(self, args): return subprocess.CompletedProcess(args, 0, "")
    def diagnostics(self): return {"clock_synchronized": True, "capture_device_present": True}


class CommissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.api = FakeBirdNET(); self.system = FakeSystem(); self.emitted = []
        self.send = mock.patch.object(c.relay, "request_json", return_value={"ok": True})
        self.sender = self.send.start()

    def tearDown(self): self.send.stop(); self.temp.cleanup()

    def execute(self, **changes):
        self.helper = c.Commissioner(provision(**changes), system=self.system, api=self.api,
                                     state_path=self.root / "private/status.json", emit=self.emitted.append,
                                     sleep=lambda _: None, attempts=2)
        return self.helper.execute()

    def test_complete_uses_real_health_and_stable_device_not_fake_bird(self):
        result = self.execute()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["checks"]["selected_capture"], "usb-path:1-1.3")
        self.assertTrue(result["checks"]["inference_advancing"])
        self.assertEqual(result["checks"]["stored_detection_count"], 0)
        self.assertFalse(result["real_bird_verified"])
        self.assertFalse(result["physical_audio_quality_verified"])
        self.assertEqual(self.api.settings["output"]["sqlite"]["path"], "precious-existing-history.db")
        self.assertEqual(self.api.settings["realtime"]["audio"]["sources"][0]["gain"], 1.5)
        self.assertFalse(self.api.settings["realtime"]["audio"]["export"]["enabled"])
        self.assertFalse(self.api.settings["realtime"]["daylightFilter"]["enabled"])
        self.assertEqual(self.system.restarts, 0)
        self.assertEqual(self.system.started, 1)
        self.assertEqual(len(self.sender.call_args_list), 1)
        self.assertTrue(self.sender.call_args.args[0].endswith("/api/ingest/heartbeat"))
        self.assertEqual((self.root / "private/status.json").stat().st_mode & 0o777, 0o600)
        output = json.dumps(self.emitted)
        self.assertNotIn(provision()["token"], output)
        self.assertEqual([x["progress"] for x in self.emitted], sorted(x["progress"] for x in self.emitted))

    def test_ambiguous_capture_requests_specific_choice_without_settings_writes(self):
        self.api.devices.append({"id": "Mic2", "name": "USB second mic", "stableId": "usb-path:1-2"})
        result = self.execute()
        self.assertEqual((result["status"], result["code"]), ("needs_input", "capture_choice_required"))
        self.assertEqual(len(result["capture_sources"]), 2)
        self.assertFalse(any(method != "GET" for _, method, _ in self.api.calls))
        self.assertEqual(self.system.started, 0)
        result = self.execute(capture_device="usb-path:1-2")
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["checks"]["selected_capture"], "usb-path:1-2")

    def test_missing_or_ambiguous_default_input_is_not_silently_chosen(self):
        self.api.devices = []
        self.assertEqual(self.execute()["code"], "capture_missing")
        self.api.devices = [{"id": "default", "name": "Default device"}]
        self.assertEqual(self.execute()["code"], "capture_choice_required")

    def test_unmanaged_configuration_never_changed_or_restarted(self):
        self.system.is_owned = False
        result = self.execute(use_existing_birdnet=True)
        self.assertEqual(result["code"], "unmanaged_configuration")
        self.assertFalse(any(method != "GET" for _, method, _ in self.api.calls))
        self.assertEqual(self.system.restarts + self.system.backups + self.system.started, 0)

    def test_fresh_install_with_unverified_api_ownership_never_modifies_that_api(self):
        self.system.is_owned = False
        result = self.execute()
        self.assertEqual(result["code"], "birdnet_ownership_unverified")
        self.assertFalse(any(method != "GET" for _, method, _ in self.api.calls))
        self.assertEqual(self.system.restarts + self.system.started, 0)

    def test_ownership_is_rechecked_before_api_mutation(self):
        self.system.owned = mock.Mock(side_effect=[True, False])
        result = self.execute()
        self.assertEqual(result["code"], "birdnet_ownership_unverified")
        self.assertFalse(any(method != "GET" for _, method, _ in self.api.calls))

    def test_additional_models_sources_or_storage_require_review(self):
        for change in (lambda s: s["models"]["enabled"].append("bat"),
                       lambda s: s["realtime"]["audio"]["sources"].append({"device": "second"}),
                       lambda s: s["realtime"]["rtsp"]["streams"].append({"url": "rtsp://private"}),
                       lambda s: s["output"]["mysql"].update(enabled=True),
                       lambda s: s["realtime"]["audio"]["sources"][0].update(model="bat")):
            self.api = FakeBirdNET(); change(self.api.settings)
            result = self.execute()
            self.assertEqual(result["code"], "existing_configuration_complex")
            self.assertFalse(any(method != "GET" for _, method, _ in self.api.calls))

    def test_loaded_model_without_advancing_windows_never_reports_ready(self):
        self.api.advance = False
        result = self.execute()
        self.assertEqual(result["code"], "audio_pipeline_not_ready")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(self.system.restarts, 1)
        self.assertEqual(self.system.started, 0)
        self.sender.assert_not_called()

    def test_one_bounded_owned_restart_recovers_health_or_transient_api_failure(self):
        for transient in (False, True):
            self.api = FakeBirdNET(); self.system = FakeSystem()
            if transient: self.api.audio_error_once = True
            else: self.api.healthy = False
            self.system.on_restart = lambda: setattr(self.api, "healthy", True)
            result = self.execute()
            self.assertEqual(result["status"], "complete")
            self.assertEqual(self.system.restarts, 1)

    def test_required_configuration_restart_and_later_failure_never_restart_twice(self):
        self.api.restart_required = True; self.api.advance = False
        result = self.execute()
        self.assertEqual(result["code"], "audio_pipeline_not_ready")
        self.assertEqual(self.system.restarts, 1)

    def test_configuration_rejection_stops_before_claiming_health(self):
        self.api.skip_fields = True
        result = self.execute()
        self.assertEqual(result["code"], "settings_rejected")
        self.assertNotIn("audio", result["checks"])
        self.sender.assert_not_called()

    def test_server_outage_keeps_relay_running_and_never_claims_complete(self):
        self.sender.side_effect = OSError("private-token-error should not be shown")
        result = self.execute()
        self.assertEqual((result["status"], result["code"]), ("failed", "server_unreachable"))
        self.assertEqual(self.system.started, 1)
        self.assertNotIn("private-token-error", json.dumps(result))
        self.assertNotIn("server_heartbeat_acknowledged", result["checks"])

    def test_access_denial_is_not_a_service_failure_to_restart(self):
        self.api.bootstrap_error = c.CommissionError("birdnet_access_required", "Protected BirdNET needs approved access")
        result = self.execute()
        self.assertEqual(result["code"], "birdnet_access_required")
        self.assertEqual(self.system.restarts, 0)
        self.assertFalse(self.api.calls)

    def test_diagnostics_is_read_only_and_reports_an_active_lock(self):
        state, lock = self.root / "missing.json", self.root / "operation.lock"
        result = c.diagnose(state, lock, self.system, self.api)
        self.assertEqual(result["status"], "diagnostic")
        self.assertFalse(result["operation_running"])
        self.assertFalse(state.exists() or lock.exists())
        with lock.open("w") as out:
            fcntl.flock(out.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = c.diagnose(state, lock, self.system, self.api)
            self.assertTrue(result["operation_running"])
            self.assertEqual(result["next_actions"], ["wait_for_current_operation"])
        self.assertFalse(any(method != "GET" for _, method, _ in self.api.calls))
        self.assertEqual(self.system.installed + self.system.started + self.system.restarts, 0)

    def test_secret_provision_file_is_private_removed_and_not_in_command_arguments(self):
        system = c.System(); paths = []
        def run(args, timeout, env):
            path = Path(args[args.index("--provision") + 1]); paths.append(path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text())["token"], provision()["token"])
            self.assertNotIn(provision()["token"], " ".join(args))
            self.assertEqual(env["SONGSKETCH_DEFER_RELAY_START"], "1")
            return subprocess.CompletedProcess(args, 1, "secret raw installer error")
        with mock.patch.object(system, "run", side_effect=run):
            with self.assertRaises(c.CommissionError) as error: system.install(provision())
        self.assertEqual(error.exception.code, "installer_failed")
        self.assertNotIn("secret raw", str(error.exception))
        self.assertFalse(paths[0].exists())

    def test_provision_validation_and_go_omitempty_readback(self):
        for changes in ({"latitude": float("nan")}, {"latitude": True}, {"longitude": 181},
                        {"latitude": 0, "longitude": 0}, {"token": "short"},
                        {"server_url": "http://127.0.0.1:8765"}, {"capture_device": "injected\nname"},
                        {"use_existing_birdnet": "yes"}):
            with self.assertRaises((ValueError, TypeError)): c.validate_provision(provision(**changes))
        self.assertTrue(c.matches({"sources": [{}]}, {"source": "", "sources": [{"model": ""}]}))
        self.assertFalse(c.matches({}, {"enabled": False}))
        self.assertFalse(c.matches({}, {"model": "birdnet"}))

    def test_installer_timeout_terminates_child_group_before_releasing_operation(self):
        process = mock.Mock(pid=4321)
        process.communicate.side_effect = [subprocess.TimeoutExpired(["installer"], 1), ("", None)]
        with mock.patch.object(c.subprocess, "Popen", return_value=process) as start, mock.patch.object(c.os, "killpg") as kill:
            result = c.System().run(["installer"], timeout=1)
        self.assertEqual(result.returncode, 124)
        self.assertTrue(start.call_args.kwargs["start_new_session"])
        kill.assert_called_once_with(4321, c.signal.SIGTERM)


class HTTPContractTests(unittest.TestCase):
    def test_real_cookie_csrf_patch_and_http_error_redaction(self):
        received = []
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Set-Cookie", "csrf=csrf-test; Path=/; SameSite=Lax"); self.end_headers()
                self.wfile.write(json.dumps({"version": "20261014", "csrfToken": "csrf-test", "security": {"enabled": False}}).encode())
            def do_PATCH(self):
                received.append((self.headers.get("Cookie"), self.headers.get("X-CSRF-Token"),
                                 self.headers.get("Origin"), json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                self.send_response(403 if self.path.endswith("security") else 200); self.end_headers()
                self.wfile.write(b'{"message":"private debug secret","skippedFields":[]}')
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever); thread.start()
        try:
            base = "http://127.0.0.1:" + str(server.server_port)
            api = c.BirdNET(base); api.bootstrap()
            api.request("/api/v2/settings/birdnet", "PATCH", {"threshold": .7})
            self.assertEqual(received[0], ("csrf=csrf-test", "csrf-test", base, {"threshold": .7}))
            with self.assertRaises(c.CommissionError) as error: api.request("/api/v2/settings/security", "PATCH", {})
            self.assertEqual(error.exception.code, "birdnet_access_required")
            self.assertNotIn("private debug", str(error.exception))
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_bootstrap_rejects_unreviewed_release_and_existing_auth(self):
        api = c.BirdNET()
        for response, code in (({"version": "newer", "security": {}}, "birdnet_version_mismatch"),
                               ({"version": "20261014", "security": {"enabled": True}}, "birdnet_access_required")):
            with mock.patch.object(api, "request", return_value=response):
                with self.assertRaises(c.CommissionError) as error: api.bootstrap()
                self.assertEqual(error.exception.code, code)


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.pinned = "ghcr.io/tphakala/birdnet-go@sha256:" + "a" * 64
        self.image_id = "sha256:" + "b" * 64
        lock = self.root / "image.lock"; lock.write_text(self.pinned)
        self.patch = mock.patch.object(c, "IMAGE_LOCK", lock); self.patch.start()
        self.container = {
            "Config": {"Image": self.pinned, "Labels": {"org.songsketch.managed": "true", "org.songsketch.birdnet-release": "20261014"}},
            "Image": self.image_id, "State": {"Running": True, "Pid": 1234},
            "HostConfig": {"NetworkMode": "bridge", "PortBindings": {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}]}},
            "NetworkSettings": {"Ports": {"8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8080"}]}}}
        self.system = c.System(); self.calls = []
        def run(args, **kwargs):
            self.calls.append(args)
            if args == ["docker", "inspect", "songsketch-birdnet"]:
                return subprocess.CompletedProcess(args, 0, json.dumps([self.container]))
            if args[:3] == ["docker", "image", "inspect"]:
                return subprocess.CompletedProcess(args, 0, self.image_id + "\n")
            if args[:2] == ["docker", "restart"]: return subprocess.CompletedProcess(args, 0, "")
            raise AssertionError("Unexpected ownership command")
        self.runner = mock.patch.object(self.system, "run", side_effect=run); self.runner.start()

    def tearDown(self): self.runner.stop(); self.patch.stop(); self.tmp.cleanup()

    def test_correct_pinned_live_container_is_owned(self):
        self.assertTrue(self.system.owned())
        self.assertTrue(self.system.can_restart())

    def test_label_cannot_authorize_wrong_port_image_or_process(self):
        original = copy.deepcopy(self.container)
        cases = [
            lambda x: x["HostConfig"]["PortBindings"]["8080/tcp"][0].update(HostPort="18080"),
            lambda x: x["HostConfig"]["PortBindings"]["8080/tcp"][0].update(HostIp="0.0.0.0"),
            lambda x: x["NetworkSettings"]["Ports"]["8080/tcp"][0].update(HostPort="18080"),
            lambda x: x["Config"].update(Image="ghcr.io/tphakala/birdnet-go:latest"),
            lambda x: x.update(Image="sha256:" + "c" * 64),
            lambda x: x["Config"]["Labels"].update({"org.songsketch.birdnet-release": "20261013"}),
            lambda x: x["HostConfig"].update(NetworkMode="host"),
            lambda x: x["State"].update(Pid=0),
        ]
        for change in cases:
            self.container = copy.deepcopy(original); change(self.container)
            self.assertFalse(self.system.owned())
            self.assertFalse(self.system.restart_birdnet())
        self.assertFalse(any(args[:2] == ["docker", "restart"] for args in self.calls))

    def test_stopped_labelled_container_cannot_claim_other_service_on_8080(self):
        self.container["State"].update(Running=False, Pid=0)
        self.container["NetworkSettings"]["Ports"] = {}
        with mock.patch.object(c.socket, "create_connection") as probe:
            self.assertFalse(self.system.owned())
            self.assertFalse(self.system.can_restart())
            self.assertFalse(self.system.restart_birdnet())
            probe.assert_called_with(("127.0.0.1", 8080), timeout=2)
        self.assertFalse(any(args[:2] == ["docker", "restart"] for args in self.calls))
        # A verifiably vacant port permits exactly the owned container to start.
        with mock.patch.object(c.socket, "create_connection", side_effect=ConnectionRefusedError):
            self.assertTrue(self.system.restart_birdnet())
        self.assertEqual(sum(args[:2] == ["docker", "restart"] for args in self.calls), 1)


if __name__ == "__main__": unittest.main()
