"""Composed Pi relay -> actual Songsketch HTTP server -> SQLite integration.

BirdNET upstream is a localhost fixture with the pinned API shapes. No email, AI,
private service, physical microphone or non-local network is contacted.
"""
import datetime as dt
import http.server
import importlib.util
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from songsketch.server import App, Server
from songsketch.store import iso, utcnow
from songsketch.config import Config
from songsketch.locking import RunLock

SPEC = importlib.util.spec_from_file_location("integration_pi_relay", ROOT / "pi/relay.py")
pi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pi)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        self.catalogue = self.path / "catalogue.json"
        self.catalogue.write_text(json.dumps({"version": 1, "birds": [
            {"id": "robin", "common_name": "Robin", "scientific_name": "Erithacus rubecula",
             "aliases": ["European Robin"], "approved": True, "animation_ready": True,
             "image_url": "/artwork/robin.png", "animation_url": "/artwork/robin.html"}]}))
        self.app = App(self.path / "server-state", self.catalogue, background=False)
        self.app.config.update({"timezone": "UTC"})
        self.start_server()
        self.rows = []
        self.audio_state = "HEALTHY"
        self.inference_state = "ok"
        self.birdnet_requests = []
        owner = self

        class BirdNET(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                parsed = urlsplit(self.path)
                owner.birdnet_requests.append(self.path)
                if parsed.path == "/api/v2/detections":
                    q = parse_qs(parsed.query)
                    rows = [r for r in owner.rows if q.get("start_date", [""])[0] <= r["date"] <= q.get("end_date", ["9999"])[0]]
                    rows.sort(key=lambda r: r["timestamp"])
                    offset, limit = int(q.get("offset", [0])[0]), int(q.get("numResults", [200])[0])
                    value = {"data": rows[offset:offset + limit], "total": len(rows), "limit": limit, "offset": offset}
                elif parsed.path == "/api/v2/health/audio":
                    value = {"sources": [{"source_id": "usb-microphone", "state": owner.audio_state, "last_dispatch": iso()}]}
                elif parsed.path == "/api/v2/system/inference":
                    value = {"acousticModelsState": "ok", "models": [{"id": "BirdNET_V2.4", "sources": [{"id": "usb-microphone"}],
                             "health": {"state": owner.inference_state, "lastSuccessAtUnix": int(time.time()), "inferenceCount": 100}}]}
                else:
                    value = {"status": "healthy", "version": "20261014"}
                raw = json.dumps(value).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers(); self.wfile.write(raw)

        self.upstream = http.server.ThreadingHTTPServer(("127.0.0.1", 0), BirdNET)
        self.upstream_thread = threading.Thread(target=self.upstream.serve_forever)
        self.upstream_thread.start()
        self.token_file = self.path / "station.token"
        self.token_file.write_text(self.app.config.secrets["station_token"])
        self.token_file.chmod(0o600)
        self.pi_config = {"station_id": "garden", "source_instance_id": "integration-source",
            "server_url": self.server_url, "birdnet_url": "http://127.0.0.1:" + str(self.upstream.server_port),
            "token_file": str(self.token_file), "data_dir": str(self.path / "pi-state"), "timezone": "UTC",
            "initial_history_days": 0, "poll_seconds": 5, "heartbeat_seconds": 15, "model_id": "BirdNET_V2.4"}
        self.relay = pi.Relay(self.pi_config)

    def start_server(self, port=0):
        self.server = Server(("127.0.0.1", port), self.app)
        self.server_url = "http://127.0.0.1:" + str(self.server.server_port)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.start()

    def stop_server(self):
        self.server.shutdown(); self.server.server_close(); self.server_thread.join()

    def tearDown(self):
        self.stop_server()
        self.upstream.shutdown(); self.upstream.server_close(); self.upstream_thread.join()
        self.relay.store.close(); self.app.close(); self.tmp.cleanup()

    def detection(self, ident, scientific="Erithacus rubecula", common="European Robin", confidence=.93, days_ago=0):
        stamp = utcnow() - dt.timedelta(days=days_ago)
        return {"id": ident, "date": stamp.date().isoformat(), "time": stamp.strftime("%H:%M:%S"),
                "timestamp": iso(stamp), "scientificName": scientific, "commonName": common,
                "confidence": confidence, "verified": "unverified", "modelType": "bird"}

    def drain(self):
        # Delivery may append its recovery report after the initial batch.
        for _ in range(4):
            self.relay.deliver(now=time.time() + 1000)
            if not self.relay.store.snapshot()["pending"]:
                break

    def test_real_receiver_normalization_counts_and_missing_art(self):
        self.rows = [self.detection(11), self.detection(12, "Passer domesticus", "House Sparrow"),
                     self.detection(13, "Regulus regulus", "Goldcrest", confidence=.1)]
        self.relay.poll(utcnow().date())
        self.assertEqual(len(self.app.store.query("SELECT * FROM detections")), 0)
        self.drain()
        records = self.app.store.query("SELECT * FROM detections ORDER BY id")
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["common_name"], "Robin")
        self.assertEqual(records[0]["event_id"], "birdnet:integration-source:11")
        counts = {row["scientific_name"]: row["count"] for row in self.app.store.summary()}
        self.assertEqual(counts, {"Erithacus rubecula": 1, "Passer domesticus": 1})
        outbox = self.app.store.query("SELECT species,status FROM email_outbox")
        self.assertEqual(outbox, [{"species": "Passer domesticus", "status": "pending"}])
        self.relay.poll(utcnow().date()); self.drain()
        self.assertEqual(len(self.app.store.query("SELECT * FROM detections")), 3)
        self.app.store.set_meta("current", None); self.app.store.tick()
        current = self.app.store.public_status()["current"]
        self.assertEqual(current["artwork_id"], "robin")
        self.assertEqual(current["mode"], "live")
        self.assertTrue(all("/api/v2/" in p for p in self.birdnet_requests))

    def test_health_and_recovery_reports_with_no_bird_activity(self):
        self.relay.heartbeat()
        self.assertEqual(self.app.store.station_status()["listening"], "available")
        self.assertEqual(self.app.store.query("SELECT COUNT(*) n FROM detections")[0]["n"], 0)
        self.audio_state = "FAILED"
        self.relay.heartbeat(); self.drain()
        self.assertEqual(self.app.store.station_status()["listening"], "unavailable")
        active = self.app.store.query("SELECT * FROM issues WHERE resolved=0")
        self.assertTrue(any("Audio" in i["message"] for i in active))
        self.audio_state = "HEALTHY"
        self.relay.heartbeat(); self.drain()
        self.assertEqual(self.app.store.station_status()["listening"], "available")
        self.assertFalse(self.app.store.query("SELECT * FROM issues WHERE resolved=0"))
        self.assertEqual(self.app.store.query("SELECT COUNT(*) n FROM reports")[0]["n"], 2)

    def test_server_outage_and_both_restarts_replay_without_duplicate(self):
        self.rows = [self.detection(21)]
        self.relay.poll(utcnow().date())
        self.drain()
        port = self.server.server_port
        self.stop_server(); self.app.close()
        self.rows.append(self.detection(22, "Passer domesticus", "House Sparrow"))
        self.relay.poll(utcnow().date())
        self.relay.deliver()
        self.assertEqual(self.relay.store.snapshot()["pending_detections"], 1)
        self.relay.store.close()
        self.relay = pi.Relay(self.pi_config)
        self.app = App(self.path / "server-state", self.catalogue, background=False)
        self.start_server(port)
        self.drain()
        self.relay.poll(utcnow().date()); self.drain()
        self.assertEqual(self.app.store.query("SELECT COUNT(*) n FROM detections")[0]["n"], 2)
        self.assertEqual(self.relay.store.snapshot()["pending"], 0)
        issues = self.app.store.query("SELECT * FROM issues WHERE resolved=0")
        self.assertFalse(any("delivery" in i["message"].lower() for i in issues))

    def test_receiver_commit_with_lost_ack_replays_existing_row(self):
        self.rows = [self.detection(31)]
        self.relay.poll(utcnow().date())
        failed = [False]
        def lose_response(url, token=None, body=None, timeout=8):
            result = pi.request_json(url, token, body, timeout)
            if url.endswith("/detections") and not failed[0]:
                failed[0] = True
                raise ConnectionResetError("simulated acknowledgement loss after real database commit")
            return result
        self.relay.transport = lose_response
        self.relay.deliver()
        self.assertEqual(self.app.store.query("SELECT COUNT(*) n FROM detections")[0]["n"], 1)
        self.assertEqual(self.relay.store.snapshot()["pending_detections"], 1)
        self.relay.store.close(); self.relay = pi.Relay(self.pi_config)
        self.drain()
        self.assertEqual(self.app.store.query("SELECT COUNT(*) n FROM detections")[0]["n"], 1)
        self.assertEqual(self.relay.store.snapshot()["pending_detections"], 0)


class RobustnessTests(unittest.TestCase):
    """Regression checks for shared-state races and retry boundaries."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        catalogue = self.path / "catalogue.json"
        catalogue.write_text(json.dumps({"birds": [
            {"id": "robin", "common_name": "Robin", "scientific_name": "Erithacus rubecula",
             "approved": True, "animation_ready": True}]}))
        self.catalogue = catalogue
        self.app = App(self.path / "state", catalogue, background=False)

    def tearDown(self):
        self.app.close()
        self.tmp.cleanup()

    def prepare_mail(self):
        self.app.config.update({"smtp_host": "mail.invalid", "smtp_from": "sender@example.invalid",
                                "notification_email": "friend@example.invalid", "smtp_tls": False})
        self.app.store.ingest({"event_id": "new-sparrow", "station_id": "garden",
            "scientific_name": "Passer domesticus", "common_name": "House Sparrow",
            "confidence": .94, "observed_at": iso()})

    def test_second_app_cannot_mutate_running_jobs_or_state(self):
        with self.app.store.tx() as db:
            db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)", (
                "in-progress", "artwork", "Passer domesticus", "running", "In progress", iso(), iso(), "{}", None))
        before = (self.app.config.directory / "secrets.json").read_bytes()
        with self.assertRaisesRegex(RuntimeError, "already using this data folder"):
            App(self.app.config.directory, self.catalogue, background=False)
        self.assertEqual(self.app.store.query("SELECT status FROM jobs WHERE id='in-progress'")[0]["status"], "running")
        self.assertEqual((self.app.config.directory / "secrets.json").read_bytes(), before)
        # The same exclusion is available to restore, independent of listening port.
        with self.assertRaises(RuntimeError):
            RunLock(self.app.config.directory)

    def test_run_lock_can_be_acquired_after_owner_releases(self):
        folder = self.path / "separate-lock"
        first = RunLock(folder)
        with self.assertRaises(RuntimeError):
            RunLock(folder)
        first.close()
        replacement = RunLock(folder)
        replacement.close()

    def test_pre_submission_network_failure_retries_with_backoff(self):
        self.prepare_mail()
        with mock.patch("songsketch.maintenance.smtplib.SMTP", side_effect=socket.gaierror("mock DNS failure")) as smtp:
            self.assertEqual(self.app.maintenance.send_mail(), 0)
            self.assertEqual(self.app.maintenance.send_mail(), 0)
            smtp.assert_called_once()
        row = self.app.store.query("SELECT * FROM email_outbox")[0]
        self.assertEqual(row["status"], "failed")
        self.assertEqual(row["attempts"], 1)
        self.assertGreater(row["next_attempt"], iso())

    def test_failure_during_submission_remains_uncertain(self):
        self.prepare_mail()
        with mock.patch("songsketch.maintenance.smtplib.SMTP") as smtp:
            smtp.return_value.__enter__.return_value.send_message.side_effect = ConnectionResetError("mock lost acknowledgement")
            self.assertEqual(self.app.maintenance.send_mail(), 0)
            self.assertEqual(self.app.maintenance.send_mail(), 0)
            smtp.assert_called_once()
        row = self.app.store.query("SELECT * FROM email_outbox")[0]
        self.assertEqual(row["status"], "uncertain")
        self.assertEqual(row["attempts"], 1)

    def test_invalid_common_name_rejected_before_job_or_provider(self):
        self.app.config.secrets["openai_api_key"] = "test-only-never-sent"
        self.app.jobs.requester = mock.Mock(side_effect=AssertionError("must not contact provider"))
        for common in ({"invalid": True}, ["House Sparrow"], 3, "invalid\nname"):
            with self.subTest(common=common), self.assertRaises(ValueError):
                self.app.jobs.start({"kind": "artwork", "scientific_name": "Passer domesticus",
                                     "common_name": common, "confirm_paid": True}, background=False)
        self.app.jobs.requester.assert_not_called()
        self.assertFalse(self.app.store.query("SELECT * FROM jobs"))
        self.assertFalse((self.app.config.directory / "approved-artwork.json").exists())

    def test_concurrent_ticks_start_one_painting_without_losing_queue_item(self):
        store = self.app.store
        store.set_meta("current", None)
        with store.tx() as db:
            for event in ("first", "second"):
                data = {"event_id": event, "scientific_name": "Erithacus rubecula", "common_name": "Robin",
                        "observed_at": iso(), "test": False}
                db.execute("INSERT INTO queue(event_id,scientific_name,data,created_at) VALUES (?,?,?,?)",
                           (event, data["scientific_name"], json.dumps(data), iso()))
        original_meta = store.meta
        def widened_read(key, default=None):
            value = original_meta(key, default)
            if key == "current":
                # Widen the former read/check/consume race while allowing the
                # fixed outer lock to serialize both readers without deadlock.
                time.sleep(.05)
            return value
        barrier = threading.Barrier(3)
        errors = []
        def tick():
            try:
                barrier.wait(timeout=5)
                store.tick()
            except Exception as exc:
                errors.append(exc)
        with mock.patch.object(store, "meta", side_effect=widened_read):
            workers = [threading.Thread(target=tick) for _ in range(2)]
            for worker in workers: worker.start()
            barrier.wait(timeout=5)
            for worker in workers: worker.join(timeout=5)
        self.assertFalse(errors)
        self.assertFalse(any(w.is_alive() for w in workers))
        self.assertEqual(store.meta("current")["event_id"], "first")
        self.assertEqual(store.query("SELECT event_id FROM queue"), [{"event_id": "second"}])

    def test_concurrent_settings_updates_keep_both_changes_and_credentials(self):
        config = self.app.config
        credentials = dict(config.secrets)
        barrier = threading.Barrier(3)
        errors = []
        def change(patch):
            try:
                barrier.wait(timeout=5)
                config.update(patch)
            except Exception as exc:
                errors.append(exc)
        workers = [threading.Thread(target=change, args=(patch,)) for patch in
                   ({"site_name": "Garden Test"}, {"hold_seconds": 33})]
        for worker in workers: worker.start()
        barrier.wait(timeout=5)
        for worker in workers: worker.join(timeout=5)
        self.assertFalse(errors)
        self.assertFalse(any(w.is_alive() for w in workers))
        restored = Config(config.directory)
        self.assertEqual(restored.values["site_name"], "Garden Test")
        self.assertEqual(restored.values["hold_seconds"], 33)
        self.assertEqual(restored.secrets, credentials)
        self.assertFalse(list(config.directory.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
