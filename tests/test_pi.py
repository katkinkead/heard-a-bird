"""Pi-side recovery/contract tests; no Raspberry Pi or private service required."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
import urllib.error
import http.server
import threading

SPEC = importlib.util.spec_from_file_location("pi_relay", Path(__file__).resolve().parents[1] / "pi/relay.py")
relay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(relay)


def bird(ident, day="2026-10-21"):
    return {"id": ident, "date": day, "time": "09:00:00", "timestamp": day + "T09:00:00+01:00",
            "scientificName": "Erithacus rubecula", "commonName": "European Robin", "confidence": .91}


class PiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        token = self.root / "station.token"
        token.write_text("station-secret-that-must-never-appear")
        token.chmod(0o600)
        self.config = {"station_id": "garden", "source_instance_id": "birdnet-db-one",
                       "server_url": "http://server.invalid", "birdnet_url": "http://birdnet.invalid",
                       "token_file": str(token), "data_dir": str(self.root / "state"), "timezone": "Europe/London",
                       "initial_history_days": 0, "poll_seconds": 5, "heartbeat_seconds": 15,
                       "model_id": "BirdNET_V2.4"}

    def tearDown(self):
        self.tmp.cleanup()

    def test_pagination_catchup_and_restart_do_not_duplicate(self):
        records = [bird(n) for n in range(1, 406)]
        calls = []
        def transport(url, token=None, body=None, timeout=8):
            from urllib.parse import parse_qs, urlsplit
            q = parse_qs(urlsplit(url).query); calls.append(q)
            offset = int(q["offset"][0]); limit = int(q["numResults"][0])
            rows = records if q["start_date"] == ["2026-10-21"] else []
            return {"data": rows[offset:offset + limit], "total": len(rows)}
        r = relay.Relay(self.config, transport)
        r.poll(dt.date(2026, 10, 21))
        self.assertEqual(r.store.snapshot()["pending_detections"], 405)
        self.assertEqual([q["offset"][0] for q in calls], ["0", "200", "400"])
        self.assertTrue(all(q["sortBy"] == ["date_asc"] for q in calls))
        r.store.close()
        r = relay.Relay(self.config, transport)
        r.poll(dt.date(2026, 10, 21))
        self.assertEqual(r.store.snapshot()["pending_detections"], 405)
        self.assertEqual(r.store.get("history_day"), "2026-10-21")
        r.store.close()

    def test_interrupted_page_never_advances_checkpoint(self):
        records = [bird(n) for n in range(1, 202)]
        def broken(url, *args, **kwargs):
            if "offset=200" in url: raise OSError("offline")
            return {"data": records[:200], "total": 201}
        r = relay.Relay(self.config, broken)
        with self.assertRaises(OSError): r.poll(dt.date(2026, 10, 21))
        self.assertIsNone(r.store.get("history_day"))
        self.assertEqual(r.store.snapshot()["pending_detections"], 200)
        r.store.close()

    def test_committed_but_ack_lost_retries_same_event_id(self):
        server_ids = set()
        calls = []
        lose_ack = [True]
        def receiver(url, token, body, timeout=8):
            if url.endswith("/reports"): return {"ok": True, "id": body["report_id"], "duplicate": False}
            calls.append(body["event_id"])
            duplicate = body["event_id"] in server_ids
            server_ids.add(body["event_id"])
            if lose_ack[0]:
                lose_ack[0] = False
                raise OSError("response lost after commit")
            return {"ok": True, "id": body["event_id"], "duplicate": duplicate}
        r = relay.Relay(self.config, receiver)
        r.store.detection(relay.normalize_detection(bird(42), self.config))
        r.deliver(now=time.time())
        self.assertEqual(r.store.snapshot()["pending_detections"], 1)
        r.store.close()
        r = relay.Relay(self.config, receiver)
        r.deliver(now=time.time() + 999)
        self.assertEqual(len(server_ids), 1)
        self.assertEqual(calls, ["birdnet:birdnet-db-one:42"] * 2)
        self.assertEqual(r.store.snapshot()["pending_detections"], 0)
        r.store.close()

    def test_nondurable_reply_keeps_record(self):
        r = relay.Relay(self.config, lambda *args, **kwargs: {"ok": True})
        r.store.detection(relay.normalize_detection(bird(2), self.config))
        r.deliver(now=time.time())
        self.assertEqual(r.store.snapshot()["pending_detections"], 1)
        r.store.close()

    def test_reports_survive_outage_and_are_grouped(self):
        s = relay.Store(self.root / "reports")
        s.fault("garden", "audio", True, "Audio failed", "HTTP 500", now=100)
        for i in range(20): s.fault("garden", "audio", True, "Audio failed", now=101 + i)
        self.assertEqual(s.snapshot()["pending_reports"], 1)
        self.assertEqual(s.snapshot()["faults"][0]["occurrences"], 21)
        s.close(); s = relay.Store(self.root / "reports")
        s.fault("garden", "audio", False, "Audio recovered", now=130)
        self.assertEqual(s.snapshot()["pending_reports"], 2)
        self.assertEqual(len(s.reports()), 2)
        s.close()

    def test_quiet_garden_health_uses_frames_and_inference(self):
        now = time.time()
        audio = {"sources": [{"source_id": "usb-mic", "state": "HEALTHY",
                  "last_dispatch": dt.datetime.fromtimestamp(now - 2, relay.UTC).isoformat()}]}
        inference = {"models": [{"id": "BirdNET_V2.4", "sources": [{"id": "usb-mic"}],
                     "health": {"state": "ok", "lastSuccessAtUnix": int(now - 1)}}]}
        self.assertEqual(relay.interpret_health(audio, inference, self.config, now), ("healthy", "healthy"))
        self.assertEqual(relay.interpret_health({"status": "healthy"}, {"status": "healthy"}, self.config, now), ("unknown", "unknown"))
        inference["models"][0]["health"]["lastSuccessAtUnix"] = now - 300
        self.assertEqual(relay.interpret_health(audio, inference, self.config, now)[1], "unknown")
        audio["sources"][0]["state"] = "FAILED"
        inference["models"][0]["health"]["state"] = "failing"
        self.assertEqual(relay.interpret_health(audio, inference, self.config, now), ("failed", "failed"))

    def test_diagnostics_and_faults_never_echo_credentials(self):
        r = relay.Relay(self.config)
        failure = urllib.error.HTTPError("http://secret@example.invalid", 401, "secret-password", {}, None)
        r.report_fault("test", True, "Request failed", relay.error_code(failure))
        text = json.dumps({"status": r.diagnostics(), "reports": r.store.reports()})
        self.assertNotIn("station-secret", text)
        self.assertNotIn("secret-password", text)
        self.assertNotIn("example.invalid", text)
        self.assertIn("HTTP 401", text)
        r.store.close()

    def test_species_filter_and_time_and_identity(self):
        row = bird(3)
        payload = relay.normalize_detection(row, self.config)
        self.assertEqual(payload["observed_at"], "2026-10-21T08:00:00+00:00")
        row["verified"] = "false_positive"
        self.assertIsNone(relay.normalize_detection(row, self.config))
        row = bird(3); row["modelType"] = "bat"
        self.assertIsNone(relay.normalize_detection(row, self.config))
        row = bird(3); row["confidence"] = float("nan")
        with self.assertRaises(ValueError): relay.normalize_detection(row, self.config)
        row = bird(3); del row["id"]
        with self.assertRaises(ValueError): relay.normalize_detection(row, self.config)

    def test_backup_is_consistent_and_preserves_pending(self):
        s = relay.Store(self.root / "backup")
        s.detection(relay.normalize_detection(bird(7), self.config)); s.backup()
        import sqlite3
        with sqlite3.connect(next((self.root / "backup").glob("relay-backup-*.sqlite3"))) as db:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(db.execute("SELECT count(*) FROM outbox").fetchone()[0], 1)
        s.close()

    def test_http_receiver_observes_bearer_and_ack_removes_queue(self):
        received = []
        class Receiver(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                received.append((self.path, self.headers.get('Authorization'), body))
                self.send_response(200); self.send_header('Content-Type', 'application/json'); self.end_headers()
                self.wfile.write(json.dumps({'ok': True, 'id': body.get('event_id', body.get('report_id')), 'duplicate': False}).encode())
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Receiver)
        thread = threading.Thread(target=server.serve_forever); thread.start()
        try:
            self.config['server_url'] = 'http://127.0.0.1:' + str(server.server_port)
            r = relay.Relay(self.config)
            r.store.detection(relay.normalize_detection(bird(9), self.config))
            r.deliver()
            self.assertEqual(r.store.snapshot()['pending_detections'], 0)
            self.assertEqual(received[0][0], '/api/ingest/detections')
            self.assertEqual(received[0][1], 'Bearer station-secret-that-must-never-appear')
            self.assertEqual(received[0][2]['event_id'], 'birdnet:birdnet-db-one:9')
            r.store.close()
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_local_diagnostics_auth_and_redirect_refusal(self):
        r = relay.Relay(self.config)
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), relay.make_handler(r))
        thread = threading.Thread(target=server.serve_forever); thread.start()
        try:
            url = 'http://127.0.0.1:' + str(server.server_port)
            self.assertTrue(relay.request_json(url + '/health')['ok'])
            with self.assertRaises(urllib.error.HTTPError) as err:
                relay.request_json(url + '/diagnostics')
            self.assertEqual(err.exception.code, 401)
            self.assertIn('queue', relay.request_json(url + '/diagnostics', r.token))
            self.assertNotIn(r.token, json.dumps(relay.request_json(url + '/reports', r.token)))
            req = relay.urllib.request.Request(url, headers={'Authorization':'Bearer private'})
            with self.assertRaises(ValueError):
                relay.NoRedirect().redirect_request(req, None, 302, 'moved', {}, 'http://other.invalid')
        finally:
            server.shutdown(); server.server_close(); thread.join(); r.store.close()


if __name__ == "__main__":
    unittest.main()
