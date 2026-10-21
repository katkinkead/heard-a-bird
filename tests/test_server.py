"""Real loopback HTTP and durable-state tests. No external requests or email."""
from datetime import datetime, timedelta, timezone
import http.client
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from songsketch.config import Config
from songsketch.server import App, Server
from songsketch.store import iso, redact


def detection(event="bird-1", species="Erithacus rubecula", **overrides):
    value = {"event_id":event, "station_id":"garden", "scientific_name":species,
             "common_name":species, "confidence":0.95, "observed_at":iso()}
    value.update(overrides)
    return value


class AppTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = App(self.temp.name, background=False)
        self.app.jobs.requester = Mock(side_effect=AssertionError("External AI calls are forbidden in this test"))

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()


class DurableStoreTests(AppTest):
    def test_retry_low_confidence_and_tests_do_not_inflate_real_counts(self):
        store = self.app.store
        first = store.ingest(detection())
        duplicate = store.ingest(detection())
        store.ingest(detection("below-threshold", confidence=0.2))
        store.ingest(detection("simulation", test=True))
        self.assertFalse(first["duplicate"])
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(store.query("SELECT COUNT(*) n FROM detections")[0]["n"], 3)
        self.assertEqual(store.summary("all")[0]["count"], 1)
        self.assertEqual(self.app.admin_status()["counts"]["detections"], 1)

    def test_display_cooldown_preserves_new_history_and_deduplicates_queue(self):
        store = self.app.store
        store.set_meta("displayed:Erithacus rubecula", iso())
        store.ingest(detection("cooldown-1"))
        store.ingest(detection("cooldown-2"))
        self.assertEqual(store.public_status()["queue_count"], 0)
        self.assertEqual(store.summary()[0]["count"], 2)
        store.set_meta("displayed:Erithacus rubecula", iso(datetime.now(timezone.utc)-timedelta(hours=1)))
        store.ingest(detection("queued-1"))
        store.ingest(detection("queued-2"))
        self.assertEqual(store.public_status()["queue_count"], 1)
        self.assertEqual(store.summary()[0]["count"], 4)

    def test_old_buffered_detections_are_recorded_without_live_replay(self):
        old = iso(datetime.now(timezone.utc)-timedelta(hours=3))
        self.app.store.ingest(detection("buffered", observed_at=old))
        self.assertEqual(self.app.store.public_status()["queue_count"], 0)
        self.assertEqual(self.app.store.summary("all")[0]["count"], 1)

    def test_aliases_resolve_to_the_prepared_species(self):
        self.app.store.ingest(detection("alias", species="Parus caeruleus", common_name="Eurasian Blue Tit"))
        row = self.app.store.summary()[0]
        self.assertEqual(row["scientific_name"], "Cyanistes caeruleus")
        self.assertTrue(row["has_artwork"])
        self.assertTrue(row["has_animation"])

    def test_history_queue_and_current_survive_restart(self):
        store = self.app.store
        store.ingest(detection("durable"))
        before = store.public_status()
        self.app.close()
        self.app = App(self.temp.name, background=False)
        after = self.app.store.public_status()
        self.assertEqual(after["current"]["event_id"], before["current"]["event_id"])
        self.assertEqual(after["queue_count"], 1)
        self.assertTrue(self.app.store.ingest(detection("durable"))["duplicate"])
        self.assertEqual(self.app.store.summary()[0]["count"], 1)

    def test_sqlite_backup_is_consistent_and_contains_pending_work(self):
        self.app.store.ingest(detection("backup-queue"))
        self.app.store.report({"report_id":"report-backup", "station_id":"garden", "message":"Microphone disconnected"})
        result = self.app.maintenance.backup()
        path = Path(self.temp.name) / "backups" / result["filename"]
        with sqlite3.connect(path) as copy:
            self.assertEqual(copy.execute("PRAGMA quick_check").fetchone()[0], "ok")
            self.assertEqual(copy.execute("SELECT COUNT(*) FROM detections").fetchone()[0], 1)
            self.assertEqual(copy.execute("SELECT COUNT(*) FROM queue").fetchone()[0], 1)
            self.assertEqual(copy.execute("SELECT COUNT(*) FROM reports").fetchone()[0], 1)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_month_boundary_is_garden_timezone_not_utc(self):
        # BST October starts at 23:00 UTC on September 30.
        now = datetime(2026,10,1,12,tzinfo=timezone.utc)
        with patch("songsketch.store.utcnow", return_value=now):
            self.assertEqual(self.app.store.month_start(), "2026-09-30T23:00:00.000Z")
            self.app.store.ingest(detection("september", observed_at="2026-09-30T22:59:59Z"))
            self.app.store.ingest(detection("october", observed_at="2026-09-30T23:00:01Z"))
            self.assertEqual(self.app.store.summary()[0]["count"], 1)
            self.assertEqual(self.app.store.summary("all")[0]["count"], 2)

    def test_quiet_garden_health_uses_heartbeat_and_audio_evidence(self):
        store = self.app.store
        now = datetime(2026,10,21,12,tzinfo=timezone.utc)
        with patch("songsketch.store.utcnow", return_value=now):
            store.heartbeat({"station_id":"garden", "audio_status":"healthy", "inference_status":"healthy"})
            self.assertEqual(store.station_status()["listening"], "available")
            self.app.maintenance.check()
            self.assertFalse(store.query("SELECT * FROM issues WHERE id IN ('audio-unavailable','pi-disconnected') AND resolved=0"))
        with patch("songsketch.store.utcnow", return_value=now+timedelta(minutes=5)):
            self.assertFalse(store.station_status()["connected"])
            self.assertEqual(store.station_status()["listening"], "unknown")

    def test_reports_are_deduplicated_redacted_and_recovery_resolves_issue(self):
        secret = self.app.config.secrets["station_token"]
        event = {"report_id":"report-a", "station_id":"garden", "message":"Capture failed token="+secret,
                 "details":{"component":"capture", "password":"hidden", "log":"Bearer "+secret}}
        self.assertFalse(self.app.store.report(event)["duplicate"])
        self.assertTrue(self.app.store.report(event)["duplicate"])
        self.app.store.report({**event,"report_id":"report-b","message":"Capture recovered", "resolved":True})
        self.assertEqual(self.app.store.query("SELECT COUNT(*) n FROM reports")[0]["n"], 2)
        issue = self.app.store.query("SELECT * FROM issues")[0]
        self.assertEqual(issue["occurrences"], 2)
        self.assertEqual(issue["resolved"], 1)
        bundle = json.dumps(self.app.store.diagnostics())
        self.assertNotIn(secret, bundle)
        self.assertNotIn('"hidden"', bundle)
        self.assertIn("[redacted]", bundle)

    def test_invalid_detection_is_atomic(self):
        for changes in ({"confidence":float("nan")},{"confidence":True},{"station_id":"different"},{"observed_at":"2026-10-21T12:00:00"},{"test":"true"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.app.store.ingest(detection(**changes))
        self.assertEqual(self.app.store.query("SELECT COUNT(*) n FROM detections")[0]["n"], 0)


class HTTPServerTests(AppTest):
    def setUp(self):
        super().setUp()
        self.server = Server(("127.0.0.1",0),self.app)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,kwargs={"poll_interval":0.05},daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        super().tearDown()

    def request(self, method, path, data=None, token=None, headers=None, raw=False):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        request_headers = dict(headers or {})
        if token:
            request_headers["Authorization"] = "Bearer "+token
        body = json.dumps(data).encode() if data is not None else None
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        try:
            conn.request(method,path,body=body,headers=request_headers)
            response = conn.getresponse()
            payload = response.read()
            return response.status, dict(response.getheaders()), payload if raw else json.loads(payload)
        finally:
            conn.close()

    @property
    def admin(self): return self.app.config.secrets["admin_token"]

    @property
    def station(self): return self.app.config.secrets["station_token"]

    def test_public_endpoints_and_station_admin_token_separation(self):
        self.assertEqual(self.request("GET","/health")[0], 200)
        self.assertEqual(self.request("GET","/api/public/status")[0], 200)
        self.assertEqual(self.request("GET","/api/admin/status")[0], 401)
        self.assertEqual(self.request("GET","/api/admin/status",token=self.station)[0], 401)
        self.assertEqual(self.request("POST","/api/ingest/detections",detection(),token=self.admin)[0], 401)
        self.assertEqual(self.request("POST","/api/ingest/detections",detection(),token=self.station)[0], 200)
        status,_,payload = self.request("GET","/api/admin/status",token=self.admin)
        self.assertEqual(status, 200)
        self.assertEqual(payload["counts"]["detections"], 1)
        self.assertNotIn(self.admin, json.dumps(payload))

    def test_admin_requires_local_host_and_matching_origin(self):
        self.assertEqual(self.request("GET","/api/admin/status",token=self.admin,headers={"Host":"garden.example"})[0], 401)
        self.assertEqual(self.request("POST","/api/admin/settings",{"site_name":"Unwanted"},token=self.admin,headers={"Origin":"https://evil.example"})[0], 401)
        status,_,_ = self.request("POST","/api/admin/settings",{"site_name":"Test garden"},token=self.admin,headers={"Origin":f"http://127.0.0.1:{self.port}"})
        self.assertEqual(status, 200)
        self.assertEqual(self.app.config.values["site_name"], "Test garden")

    def test_cookie_unlock_and_logout_invalidates_server_session(self):
        status,headers,_ = self.request("POST","/api/session",{"token":self.admin})
        self.assertEqual(status, 200)
        cookie = headers["Set-Cookie"].split(";",1)[0]
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", headers["Set-Cookie"])
        self.assertEqual(self.request("GET","/api/admin/status",headers={"Cookie":cookie})[0], 200)
        self.assertEqual(self.request("POST","/api/admin/logout",{},headers={"Cookie":cookie})[0], 200)
        self.assertEqual(self.request("GET","/api/admin/status",headers={"Cookie":cookie})[0], 401)

    def test_setup_simulation_is_marked_and_excluded_from_history_counts(self):
        status,_,_ = self.request("POST","/api/admin/test-detection",{"scientific_name":"Troglodytes troglodytes"},token=self.admin)
        self.assertEqual(status, 200)
        _,_,view = self.request("GET","/api/public/status")
        self.assertTrue(view["current"]["test"])
        self.assertEqual(view["current"]["artwork_id"], "wren")
        self.assertEqual(self.app.store.summary("all"), [])

    def test_setup_test_previews_requested_bird_without_losing_real_queue(self):
        self.app.store.ingest(detection("queued-real-robin"))
        status,_,_ = self.request("POST","/api/admin/test-detection",{"scientific_name":"Troglodytes troglodytes"},token=self.admin)
        self.assertEqual(status,200)
        current = self.app.store.public_status()["current"]
        self.assertTrue(current["test"])
        self.assertEqual(current["artwork_id"],"wren")
        self.assertEqual(self.app.store.query("SELECT event_id FROM queue")[0]["event_id"],"queued-real-robin")
        self.assertEqual(self.app.store.summary("all")[0]["count"],1)

    def test_migration_export_excludes_credentials_but_preserves_queue(self):
        self.app.config.update({"openai_api_key":"unit-test-key-never-send", "smtp_password":"unit-test-mail-secret"})
        self.app.store.ingest(detection("export"))
        status,headers,body = self.request("GET","/api/admin/export",token=self.admin,raw=True)
        self.assertEqual(status,200)
        self.assertEqual(headers["Content-Type"],"application/zip")
        with zipfile.ZipFile(io.BytesIO(body)) as archive:
            self.assertIn("songsketch.sqlite3",archive.namelist())
            self.assertNotIn("secrets.json",archive.namelist())
            all_data = b"".join(archive.read(n) for n in archive.namelist())
            for secret in self.app.config.secrets.values(): self.assertNotIn(secret.encode(),all_data)

    def test_static_traversal_is_denied_and_painting_is_served(self):
        self.assertEqual(self.request("GET","/artwork/%2e%2e/%2e%2e/config.json")[0],404)
        status,_,body = self.request("GET","/artwork/animations/robin.html",raw=True)
        self.assertEqual(status,200)
        self.assertIn(b"SongsketchPainting",body)

    def test_sse_stream_contains_real_public_state(self):
        conn = http.client.HTTPConnection("127.0.0.1",self.port,timeout=3)
        try:
            conn.request("GET","/events")
            response = conn.getresponse()
            self.assertEqual(response.status,200)
            self.assertEqual(response.readline().strip(),b"event: state")
            data = response.readline().decode()
            self.assertTrue(data.startswith("data: "))
            state = json.loads(data[6:])
            self.assertEqual(state["station"]["listening"],"unknown")
            self.assertIn("artwork_id",state["current"])
            self.assertNotIn(self.admin,data)
        finally:
            conn.close()


if __name__ == "__main__": unittest.main()
