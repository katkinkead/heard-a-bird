"""Delivery-lab safety and honest evidence; upstream is a local fixture here.

These tests do not claim BirdNET recognition. The actual runtime report must be
collected separately against the pinned lab and its documented audio source.
"""
import datetime as dt
import http.server
import importlib.util
import json
from pathlib import Path
import threading
import time
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

SPEC = importlib.util.spec_from_file_location("birdnet_delivery_smoke", Path(__file__).resolve().parents[1] / "scripts/qa-birdnet-delivery.py")
q = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(q)


class BirdNETDeliverySmokeTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.mutate_on_second_poll = False
        self.history_requests = 0
        stamp = dt.datetime.now(dt.timezone.utc)
        self.row = {"id": 1, "scientificName": "Strix aluco", "commonName": "Tawny Owl", "confidence": .95,
                    "timestamp": stamp.isoformat(), "date": stamp.astimezone(ZoneInfo("Europe/London")).date().isoformat(),
                    "verified": "unverified", "modelType": "bird", "unrelated": "secret-response-canary"}
        self.rows = [self.row]
        owner = self
        class Upstream(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                owner.calls.append(self.path)
                parsed = urlsplit(self.path)
                if parsed.path == "/api/v2/app/config":
                    value = {"version": "20261014", "security": {"enabled": False}, "csrfToken": "secret-csrf-canary"}
                elif parsed.path == "/api/v2/detections":
                    owner.history_requests += 1
                    if owner.mutate_on_second_poll and owner.history_requests == 3:
                        owner.rows.append(dict(owner.row, id=2))
                    query = parse_qs(parsed.query)
                    offset, limit = int(query.get("offset", [0])[0]), int(query.get("numResults", [200])[0])
                    value = {"data": owner.rows[offset:offset + limit], "total": len(owner.rows)}
                elif parsed.path == "/api/v2/health/audio":
                    value = {"sources": [{"source_id": "fixture-source", "state": "FAILED"}]}
                elif parsed.path == "/api/v2/system/inference":
                    value = {"models": [{"id": "BirdNET_V2.4", "sources": [{"id": "fixture-source"}],
                                        "health": {"state": "idle", "lastSuccessAtUnix": int(time.time()) - 3600}}]}
                else:
                    self.send_error(404); return
                raw = json.dumps(value).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers(); self.wfile.write(raw)
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def test_real_relay_and_receiver_deliver_and_deduplicate_without_external_workers(self):
        self.rows.append(dict(self.row, id=2, confidence=.6))
        with mock.patch("songsketch.maintenance.Maintenance.run", side_effect=AssertionError("worker must stay off")) as worker:
            result = q.run_check(self.url, "Strix aluco")
        worker.assert_not_called()
        self.assertEqual(result["status"], "passed", result)
        self.assertTrue(all(result["checks"].values()))
        self.assertEqual(result["delivered_records"], 2)
        self.assertEqual(result["qualifying_records"], 1)
        self.assertEqual(result["species"], [{"scientific_name": "Strix aluco", "records": 2,
                         "qualifying_records": 1, "confidence_min": .6, "confidence_max": .95}])
        self.assertEqual(result["missing_art_notifications_queued_locally"], 1)
        self.assertEqual(result["current_pipeline"], {"audio": "failed", "inference": "unknown", "server_listening": "unavailable"})
        self.assertGreater(result["health_reports_delivered"], 0)
        self.assertFalse(any(result["evidence_limits"].values()))
        self.assertNotIn("canary", json.dumps(result))
        self.assertGreaterEqual(self.history_requests, 4)

    def test_expected_species_must_be_real_and_above_application_threshold(self):
        for confidence, wanted in ((.6, "Strix aluco"), (.95, "Tyto alba")):
            self.rows = [dict(self.row, confidence=confidence)]
            with self.subTest(confidence=confidence, wanted=wanted):
                result = q.run_check(self.url, wanted)
                self.assertEqual(result["status"], "failed")
                self.assertFalse(result["checks"]["expected_species_detected"])
                self.assertNotIn("delivered_records", result)

    def test_live_changing_records_are_not_reported_as_stable_idempotence(self):
        self.mutate_on_second_poll = True
        result = q.run_check(self.url, "Strix aluco")
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["checks"]["upstream_snapshot_stable"])
        self.assertFalse(result["checks"]["repeat_poll_idempotent"])
        self.assertIn({"code": "upstream_changed_stop_publisher_and_retry"}, result["errors"])

    def test_target_validation_precedes_network_or_local_application(self):
        for url in ("http://127.0.0.1:8080", "http://example.com:18080", "http://127.0.0.1:18080?token=secret"):
            with self.subTest(url=url), mock.patch.object(q, "App") as app, mock.patch.object(q.api_lab.commission, "BirdNET") as client:
                with self.assertRaises(ValueError): q.run_check(url, "Strix aluco")
                app.assert_not_called(); client.assert_not_called()

    def test_untrusted_exception_text_is_not_saved(self):
        with mock.patch.object(q.api_lab.commission, "BirdNET") as client:
            client.return_value.bootstrap.side_effect = RuntimeError("secret-cookie-canary")
            result = q.run_check(self.url, "Strix aluco")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["errors"], [{"code": "lab_check_failed"}])
        self.assertNotIn("canary", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
