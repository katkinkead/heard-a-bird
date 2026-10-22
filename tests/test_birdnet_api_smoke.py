"""Developer API lab boundaries. No Docker, external network or real BirdNET.

These verify the harness, not the upstream API; a separate saved runtime report
must show actual pinned-container results before claiming real compatibility.
"""
import copy
import datetime as dt
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.parse
from unittest import mock


SPEC = importlib.util.spec_from_file_location("birdnet_api_smoke", Path(__file__).resolve().parents[1] / "scripts/qa-birdnet-api.py")
q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(q)


def merge(target, patch):
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict): merge(target[key], value)
        else: target[key] = copy.deepcopy(value)


class LabAPI:
    def __init__(self, configured=True):
        self.app = {"version": "20261014", "csrfToken": "secret-csrf-canary", "security": {"enabled": False}}
        self.settings = {
            "birdnet": {"latitude": 0, "longitude": 0, "locale": "en-us", "threshold": .8},
            "models": {"enabled": ["birdnet"]},
            "realtime": {"daylightFilter": {"enabled": True},
                         "dynamicThreshold": {"enabled": True, "trigger": .9, "min": .2, "validHours": 24},
                         "rtsp": {"streams": [{"enabled": True, "url": "rtsp://secret:canary@fixture:8554/test"}]},
                         "audio": {"sources": [{"name": "saved input", "device": "precious-device", "gain": 2.3}],
                                   "quietHours": {"enabled": True}, "export": {"enabled": True}}},
            "output": {"sqlite": {"enabled": False, "path": "private-existing-history.db"}, "mysql": {"enabled": False}},
            "secretUnrelated": "secret-response-canary",
        }
        self.calls = []
        self.skip_section = None
        self.ignore_section = None
        self.failures = {}
        self.responses = {
            "/api/v2/system/audio/devices": [],
            "/api/v2/health/audio": {"sources": []},
            "/api/v2/system/inference": {"models": [{"id": "BirdNET_V2.4", "sources": [], "health": {"state": "idle"}}]},
            "/api/v2/detections": {"data": [{"commonName": "secret-record-canary"}], "total": 1},
        }
        if configured:
            for section, patch in q.source_independent_plan(self.settings):
                target = self.settings[section] if section != "audio" else self.settings["realtime"]["audio"]
                merge(target, patch)

    def bootstrap(self):
        self.calls.append(("bootstrap", "GET", None))
        return copy.deepcopy(self.app)

    def request(self, path, method="GET", body=None):
        self.calls.append((path, method, copy.deepcopy(body)))
        if path in self.failures: raise self.failures[path]
        if path == "/api/v2/settings": return copy.deepcopy(self.settings)
        if path.startswith("/api/v2/settings/"):
            section = path.rsplit("/", 1)[-1]
            target = self.settings[section] if section != "audio" else self.settings["realtime"]["audio"]
            if method == "PATCH":
                if section == self.skip_section: return {"skippedFields": ["private-field-canary"]}
                if section != self.ignore_section: merge(target, body)
                return {"restart_required": section == "models", "skippedFields": [], "secret": "response-token-canary"}
            return copy.deepcopy(target)
        return copy.deepcopy(self.responses[path.split("?", 1)[0]])


class BirdNETAPISmokeTests(unittest.TestCase):
    def run_lab(self, api=None, mutate=False):
        self.api = api or LabAPI()
        return q.run_check("http://127.0.0.1:18080", mutate, api=self.api)

    def test_default_snapshot_does_not_write_or_claim_recognition(self):
        result = self.run_lab()
        self.assertEqual(result["status"], "passed")
        self.assertFalse(result["settings_mutated"])
        self.assertFalse(result["settings_write_attempted"])
        self.assertEqual(result["settings_write_outcome"], "not_attempted")
        self.assertTrue(all(method == "GET" for _, method, _ in self.api.calls))
        self.assertEqual(result["stored_detection_count"], 1)
        self.assertEqual(result["observed_pipeline"], {"audio": "unknown", "inference": "unknown"})
        self.assertFalse(any(result["evidence_limits"].values()))
        self.assertTrue(all(result["checks"][section + "_readback"] for section in q.SECTIONS))

    def test_readonly_detects_saved_setting_drift_without_repair(self):
        api = LabAPI()
        api.settings["realtime"]["audio"]["export"]["enabled"] = True
        result = self.run_lab(api)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["checks"]["audio_readback"])
        self.assertTrue(api.settings["realtime"]["audio"]["export"]["enabled"])
        self.assertTrue(all(method == "GET" for _, method, _ in api.calls))

    def test_history_query_uses_lab_timezone_day_and_stored_date_filters(self):
        class Midnight(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 10, 22, 0, 30, tzinfo=dt.timezone.utc).astimezone(tz)
        api = LabAPI()
        with mock.patch.object(q.dt, "datetime", Midnight):
            result = q.run_check("http://127.0.0.1:18080", api=api, timezone="America/Los_Angeles")
        query = next(urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
                     for path, _, _ in api.calls if path.startswith("/api/v2/detections?"))
        self.assertEqual(query, {"start_date": ["2026-10-21"], "end_date": ["2026-10-21"],
                                 "numResults": ["1"], "sortBy": ["date_asc"]})
        self.assertEqual(result["query_day"], "2026-10-21")
        self.assertEqual(result["query_timezone"], "America/Los_Angeles")
        self.assertEqual(result["status"], "passed")

    def test_invalid_timezone_does_not_contact_api(self):
        api = LabAPI()
        with self.assertRaises(ValueError):
            q.run_check("http://127.0.0.1:18080", api=api, timezone="invalid/place")
        self.assertEqual(api.calls, [])

    def test_real_commissioner_client_is_used_by_default(self):
        api = LabAPI()
        with mock.patch.object(q.commission, "BirdNET", return_value=api) as client:
            result = q.run_check("http://127.0.0.1:18080/")
        client.assert_called_once_with("http://127.0.0.1:18080")
        self.assertEqual(api.calls[0][0], "bootstrap")
        self.assertEqual(result["status"], "passed")

    def test_source_independent_patch_preserves_lab_inputs_and_history(self):
        api = LabAPI(configured=False)
        original = copy.deepcopy(api.settings)
        result = self.run_lab(api, mutate=True)
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["settings_mutated"])
        self.assertTrue(result["restart_required"])
        writes = [(path.rsplit("/", 1)[-1], body) for path, method, body in api.calls if method == "PATCH"]
        self.assertEqual([section for section, _ in writes], list(q.SECTIONS))
        audio = dict(writes)["audio"]
        self.assertEqual(set(audio), {"quietHours", "export"})
        self.assertNotIn("planning-only", json.dumps(writes))
        self.assertEqual(api.settings["realtime"]["audio"]["sources"], original["realtime"]["audio"]["sources"])
        self.assertEqual(api.settings["realtime"]["rtsp"], original["realtime"]["rtsp"])
        self.assertEqual(api.settings["output"]["sqlite"]["path"], original["output"]["sqlite"]["path"])
        self.assertEqual(api.settings["birdnet"]["threshold"], .7)
        self.assertEqual(result["threshold_policy"], {"baseline": .7, "dynamic_enabled": True,
                         "dynamic_trigger": .9, "dynamic_minimum": .2, "dynamic_valid_hours": 24})
        self.assertFalse(api.settings["realtime"]["audio"]["export"]["enabled"])

    def test_target_must_be_explicit_literal_loopback_lab_port(self):
        invalid = ["http://127.0.0.1:8080", "http://127.0.0.1", "https://127.0.0.1:18080",
                   "http://localhost:18080", "http://192.168.1.10:18080", "http://example.com:18080",
                   "http://127.0.0.1:18080/anything", "http://127.0.0.1:18080?token=secret",
                   "http://127.0.0.1:18080#fragment", "http://u:p@127.0.0.1:18080", "http://[::1]:8080",
                   "http://127.0.0.1:22", "http://127.0.0.1:99999"]
        for url in invalid:
            api = LabAPI()
            with self.subTest(url=url), self.assertRaises(ValueError): q.run_check(url, True, api=api)
            self.assertEqual(api.calls, [])
        self.assertEqual(q.lab_url("http://[::1]:18080/"), "http://[::1]:18080")

    def test_non_boolean_mutation_permission_rejected(self):
        with self.assertRaises(ValueError): self.run_lab(mutate="yes")

    def test_bootstrap_auth_version_or_csrf_failure_blocks_writes(self):
        for change in ({"security": {"enabled": True}}, {"version": "another-release"},
                       {"version": "20261014-custom"}, {"version": "not20261014"}, {"csrfToken": ""}):
            api = LabAPI(); api.app.update(change)
            with self.subTest(change=list(change)):
                result = self.run_lab(api, mutate=True)
                self.assertEqual(result["status"], "failed")
                self.assertEqual(len(api.calls), 1)
                self.assertFalse(result["settings_mutated"])

    def test_skipped_fields_stops_after_first_rejection_and_keeps_snapshot(self):
        api = LabAPI(); api.skip_section = "models"
        result = self.run_lab(api, mutate=True)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["checks"]["models_patch_accepted"])
        self.assertEqual(sum(method == "PATCH" for _, method, _ in api.calls), 2)
        self.assertTrue(result["checks"]["stored_detections_shape"])
        self.assertNotIn("private-field-canary", json.dumps(result))

    def test_saved_setting_mismatch_fails_without_retry_or_restart(self):
        api = LabAPI(configured=False); api.ignore_section = "birdnet"
        result = self.run_lab(api, mutate=True)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["checks"]["birdnet_readback"])
        self.assertEqual(sum(method == "PATCH" for _, method, _ in api.calls), 1)

    def test_committed_patch_with_lost_ack_reports_uncertain_write(self):
        class CommitThenDisconnect(LabAPI):
            def request(self, path, method="GET", body=None):
                response = super().request(path, method, body)
                if method == "PATCH":
                    raise q.commission.CommissionError("birdnet_unreachable", "Response lost after commit")
                return response
        api = CommitThenDisconnect(configured=False)
        result = self.run_lab(api, mutate=True)
        self.assertEqual(api.settings["birdnet"]["threshold"], .7)
        self.assertEqual(api.settings["birdnet"]["locale"], "en-uk")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["settings_write_attempted"])
        self.assertEqual(result["settings_write_outcome"], "uncertain")
        self.assertIsNone(result["settings_mutated"])
        self.assertEqual(result["errors"], [{"check": "settings", "code": "birdnet_unreachable"}])
        self.assertEqual(sum(method == "PATCH" for _, method, _ in api.calls), 1)

    def test_other_models_and_storage_are_not_reconfigured(self):
        for section, key, value in (("models", "enabled", ["birdnet", "other"]), ("output", "mysql", {"enabled": True})):
            api = LabAPI(); api.settings[section][key] = value
            result = self.run_lab(api, mutate=True)
            self.assertEqual(result["status"], "failed")
            self.assertFalse(result["settings_mutated"])
            self.assertTrue(all(method == "GET" for _, method, _ in api.calls))

    def test_reports_exclude_raw_responses_cookie_and_exception_text(self):
        result = self.run_lab(mutate=True)
        rendered = json.dumps(result)
        self.assertNotIn("canary", rendered)
        self.assertNotIn("private-existing", rendered)
        api = LabAPI()
        api.failures["/api/v2/health/audio"] = q.commission.CommissionError("birdnet_unreachable", "secret-error-canary")
        result = self.run_lab(api)
        self.assertEqual(result["errors"], [{"check": "audio_health", "code": "birdnet_unreachable"}])
        self.assertNotIn("canary", json.dumps(result))
        self.assertEqual(result["status"], "failed")
        api.failures["/api/v2/health/audio"] = q.commission.CommissionError("secretcodecanary", "hidden")
        result = self.run_lab(api)
        self.assertEqual(result["errors"], [{"check": "audio_health", "code": "unexpected_response"}])

    def test_unfamiliar_health_and_invalid_history_are_not_contract_passes(self):
        api = LabAPI()
        api.responses["/api/v2/health/audio"] = {"secret": "unexpected-shape"}
        api.responses["/api/v2/detections"] = {"data": [], "total": True}
        result = self.run_lab(api)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["checks"]["audio_health_shape"])
        self.assertFalse(result["checks"]["stored_detections_shape"])

    def test_cli_saves_private_json_and_returns_failure_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "report.json"
            api = LabAPI(); api.app["version"] = "different"
            with mock.patch.object(q.commission, "BirdNET", return_value=api), mock.patch("sys.stdout", new=io.StringIO()):
                code = q.main(["--url", "http://127.0.0.1:18080", "--report", str(target)])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(target.read_text())["status"], "failed")
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
