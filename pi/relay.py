#!/usr/bin/env python3
"""Songsketch Pi relay. Python 3.11+, standard library; no audio leaves this relay.

Contract: BirdNET-Go 20261014 /api/v2/detections (paged stored records),
/health/audio, /system/inference. See docs/pi-setup.md for evidence and limits.
"""
import argparse
import datetime as dt
import hashlib
import hmac
import http.server
import json
import logging
import logging.handlers
import math
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from zoneinfo import ZoneInfo

VERSION = "0.1.0"
BIRDNET_RELEASE = "20261014"
UTC = dt.timezone.utc
LOG = logging.getLogger("songsketch.pi")


def iso_now():
    return dt.datetime.now(UTC).isoformat()


def parse_time(value):
    value = str(value)
    stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timestamp needs an explicit timezone")
    return stamp


def fresh(value, now, seconds=90):
    try:
        age = now - (float(value) if isinstance(value, (int, float)) else parse_time(value).timestamp())
        return -5 <= age <= seconds
    except (ValueError, TypeError, OverflowError):
        return False


def read_secret(path):
    p = Path(path)
    if p.stat().st_mode & 0o077:
        raise ValueError("secret file must be readable only by its owner (chmod 600)")
    secret = p.read_text().strip()
    if len(secret) < 24 or "\n" in secret or "\r" in secret:
        raise ValueError("invalid secret file")
    return secret


def validate_url(value):
    p = urllib.parse.urlsplit(value)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password or p.query or p.fragment:
        raise ValueError("URLs must be HTTP(S) addresses without credentials, query or fragment")
    return value.rstrip("/")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect refused; configure the final service URL")


def request_json(url, token=None, body=None, timeout=8):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    payload = None
    if body is not None:
        payload = json.dumps(body, allow_nan=False).encode()
        headers["Content-Type"] = "application/json"
    # Local service traffic must not accidentally go through an environment proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(urllib.request.Request(url, data=payload, headers=headers), timeout=timeout) as res:
        raw = res.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("response exceeds size limit")
        return json.loads(raw)


def error_code(exc):
    # Never persist arbitrary response bodies, URLs, exceptions or credentials.
    if isinstance(exc, urllib.error.HTTPError):
        return "HTTP " + str(exc.code)
    if isinstance(exc, (TimeoutError, OSError, urllib.error.URLError)):
        return "connection unavailable"
    return type(exc).__name__


class Store:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.directory / "relay.sqlite3"
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        if self.db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise sqlite3.DatabaseError("relay database failed integrity check; preserve it and restore a backup")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS seen(event_id TEXT PRIMARY KEY,observed_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,
            event_key TEXT NOT NULL,payload TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,
            next_attempt REAL NOT NULL DEFAULT 0,last_error TEXT,created_at REAL NOT NULL,
            UNIQUE(kind,event_key));
          CREATE TABLE IF NOT EXISTS reports(report_id TEXT PRIMARY KEY,payload TEXT NOT NULL,created_at REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS faults(component TEXT PRIMARY KEY,active INTEGER NOT NULL,
            first_seen TEXT NOT NULL,last_seen TEXT NOT NULL,last_report REAL NOT NULL,occurrences INTEGER NOT NULL);
        """)
        self.db.commit()
        os.chmod(self.path, 0o600)

    def get(self, key, default=None):
        with self.lock:
            row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return row[0] if row else default

    def set(self, key, value):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, str(value)))

    def detection(self, payload):
        # Recording seen and enqueueing are one durable transaction. Never advance
        # the history checkpoint before all records in the scanned day are stored.
        with self.lock, self.db:
            cur = self.db.execute("INSERT OR IGNORE INTO seen VALUES(?,?)", (payload["event_id"], payload["observed_at"]))
            if cur.rowcount:
                self.db.execute("INSERT INTO outbox(kind,event_key,payload,created_at) VALUES('detections',?,?,?)",
                                (payload["event_id"], json.dumps(payload), time.time()))
            return bool(cur.rowcount)

    def fault(self, station, component, active, message, detail=None, now=None):
        now = time.time() if now is None else now
        stamp = dt.datetime.fromtimestamp(now, UTC).isoformat()
        with self.lock, self.db:
            old = self.db.execute("SELECT * FROM faults WHERE component=?", (component,)).fetchone()
            if not active and (not old or not old["active"]):
                return
            changed = not old or bool(old["active"]) != active
            first = stamp if changed else old["first_seen"]
            count = 1 if changed else old["occurrences"] + 1
            send = changed or now - old["last_report"] >= 3600
            last_report = now if send else old["last_report"]
            self.db.execute("INSERT OR REPLACE INTO faults VALUES(?,?,?,?,?,?)",
                            (component, int(active), first, stamp, last_report, count))
            if not send:
                return
            payload = {"report_id": str(uuid.uuid4()), "station_id": station,
                       "resolved": not active,
                       "severity": "warning" if active else "info", "message": message,
                       "details": {"component": component, "state": "fault" if active else "recovered",
                                   "first_seen": first, "last_seen": stamp, "occurrences": count,
                                   "code": detail or "", "relay_version": VERSION}}
            encoded = json.dumps(payload)
            self.db.execute("INSERT INTO reports VALUES(?,?,?)", (payload["report_id"], encoded, now))
            self.db.execute("INSERT INTO outbox(kind,event_key,payload,created_at) VALUES('reports',?,?,?)",
                            (payload["report_id"], encoded, now))
            # Pending reports are never pruned. Keep the latest 500 delivered reports.
            self.db.execute("""DELETE FROM reports WHERE report_id NOT IN
              (SELECT event_key FROM outbox WHERE kind='reports') AND report_id NOT IN
              (SELECT report_id FROM reports ORDER BY created_at DESC LIMIT 500)""")

    def pending(self, now=None, limit=50):
        with self.lock:
            return list(self.db.execute("SELECT * FROM outbox WHERE next_attempt<=? ORDER BY id LIMIT ?",
                                        (time.time() if now is None else now, limit)))

    def ack(self, ident):
        with self.lock, self.db:
            self.db.execute("DELETE FROM outbox WHERE id=?", (ident,))

    def retry(self, row, code, now=None):
        now = time.time() if now is None else now
        delay = min(300, 2 ** min(row["attempts"] + 1, 9))
        with self.lock, self.db:
            self.db.execute("UPDATE outbox SET attempts=attempts+1,next_attempt=?,last_error=? WHERE id=?",
                            (now + delay, code, row["id"]))

    def snapshot(self):
        with self.lock:
            return {"pending": self.db.execute("SELECT count(*) FROM outbox").fetchone()[0],
                    "pending_detections": self.db.execute("SELECT count(*) FROM outbox WHERE kind='detections'").fetchone()[0],
                    "pending_reports": self.db.execute("SELECT count(*) FROM outbox WHERE kind='reports'").fetchone()[0],
                    "records_seen": self.db.execute("SELECT count(*) FROM seen").fetchone()[0],
                    "faults": [dict(r) for r in self.db.execute("SELECT * FROM faults")],
                    "oldest_pending_at": self.db.execute("SELECT min(created_at) FROM outbox").fetchone()[0]}

    def reports(self):
        with self.lock:
            return [json.loads(r[0]) for r in self.db.execute("SELECT payload FROM reports ORDER BY created_at DESC LIMIT 500")]

    def backup(self):
        today = dt.datetime.now(UTC).date().isoformat()
        target = self.directory / ("relay-backup-" + today + ".sqlite3")
        if not target.exists():
            temporary = target.with_suffix(".tmp")
            with self.lock, sqlite3.connect(temporary) as dest:
                self.db.backup(dest)
            os.chmod(temporary, 0o600)
            temporary.replace(target)
            for old in sorted(self.directory.glob("relay-backup-*.sqlite3"))[:-3]:
                old.unlink()

    def close(self):
        self.db.close()


def normalize_detection(row, config):
    ident = row.get("id")
    if not isinstance(ident, int) or isinstance(ident, bool) or ident <= 0:
        raise ValueError("BirdNET detection requires a positive stored record ID")
    scientific = row.get("scientificName")
    common = row.get("commonName")
    confidence = row.get("confidence")
    if not scientific or not common or not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError("invalid BirdNET species or confidence")
    if row.get("verified") == "false_positive" or row.get("modelType", "bird") != "bird":
        return None
    observed = row.get("timestamp") or row.get("beginTime")
    if observed:
        stamp = parse_time(observed)
    else:
        # This old-record fallback is explicit station-local time, never host local time.
        stamp = dt.datetime.fromisoformat(row["date"] + "T" + row["time"]).replace(tzinfo=ZoneInfo(config["timezone"]))
    if stamp.year < 2000:
        raise ValueError("invalid BirdNET observation time")
    return {"event_id": "birdnet:" + config["source_instance_id"] + ":" + str(ident),
            "station_id": config["station_id"], "scientific_name": scientific,
            "common_name": common, "confidence": confidence,
            "observed_at": stamp.astimezone(UTC).isoformat(), "test": False}


def interpret_health(audio, inference, config, now=None):
    """Fresh dispatch + successful model windows, never bird abundance or HTTP200."""
    now = time.time() if now is None else now
    audio_state, inference_state = "unknown", "unknown"
    sources = audio.get("sources", []) if isinstance(audio, dict) else []
    wanted = config.get("audio_source_id")
    if wanted:
        sources = [s for s in sources if s.get("source_id") == wanted]
    if sources:
        if all(s.get("state") == "HEALTHY" and fresh(s.get("last_dispatch"), now) for s in sources):
            audio_state = "healthy"
        elif any(s.get("state") in ("ALARMED", "RECOVERING", "ESCALATED", "FAILED") for s in sources):
            audio_state = "failed"
    if isinstance(inference, dict):
        models = [m for m in inference.get("models", []) if m.get("id") == config["model_id"]]
        if inference.get("acousticModelsState") in ("none_installed", "load_failed"):
            inference_state = "failed"
        elif models:
            health = models[0].get("health", {}) or {}
            attached = models[0].get("sources", [])
            if wanted:
                attached = [s for s in attached if s.get("id") == wanted]
            if health.get("state") == "failing" or any(s.get("notRunning") for s in attached):
                inference_state = "failed"
            elif attached and not models[0].get("paused") and health.get("state") == "ok" and fresh(health.get("lastSuccessAtUnix"), now):
                inference_state = "healthy"
    return audio_state, inference_state


class Relay:
    def __init__(self, config, transport=request_json):
        self.config = config
        self.transport = transport
        self.store = Store(config["data_dir"])
        self.started = time.monotonic()
        self.stop = threading.Event()
        self.audio_status = self.inference_status = "unknown"
        self.last_poll = self.last_delivery = self.last_health = None
        self.birdnet_version = None
        self.token = read_secret(config["token_file"])
        self.birdnet_token = read_secret(config["birdnet_token_file"]) if config.get("birdnet_token_file") else None

    def birdnet(self, route):
        return self.transport(self.config["birdnet_url"] + route, self.birdnet_token, timeout=8)

    def report_fault(self, component, active, message, detail=""):
        self.store.fault(self.config["station_id"], component, active, message, detail)

    def poll(self, today=None):
        today = today or dt.datetime.now(ZoneInfo(self.config["timezone"])).date()
        checkpoint = self.store.get("history_day")
        start = dt.date.fromisoformat(checkpoint) - dt.timedelta(days=1) if checkpoint else today - dt.timedelta(days=self.config["initial_history_days"])
        day = start
        while day <= today and not self.stop.is_set():
            offset, limit = 0, 200
            while not self.stop.is_set():
                query = urllib.parse.urlencode({"start_date": day.isoformat(), "end_date": day.isoformat(),
                    "sortBy": "date_asc", "numResults": limit, "offset": offset})
                result = self.birdnet("/api/v2/detections?" + query)
                if not isinstance(result, dict) or not isinstance(result.get("data"), list) or not isinstance(result.get("total"), int):
                    raise ValueError("unexpected BirdNET paginated response")
                rows = result["data"]
                if not rows and offset < result["total"]:
                    raise ValueError("incomplete BirdNET history page")
                for row in rows:
                    item = normalize_detection(row, self.config)
                    if item:
                        self.store.detection(item)
                offset += len(rows)
                if offset >= result["total"]:
                    break
                if offset > 1_000_000:
                    raise ValueError("BirdNET pagination safety limit reached")
            if self.stop.is_set():
                return
            self.store.set("history_day", day.isoformat())
            day += dt.timedelta(days=1)
        self.last_poll = iso_now()
        self.report_fault("birdnet_history", False, "BirdNET history connection recovered")

    def deliver(self, now=None):
        for row in self.store.pending(now=now):
            try:
                reply = self.transport(self.config["server_url"] + "/api/ingest/" + row["kind"],
                    self.token, json.loads(row["payload"]), timeout=8)
                if not isinstance(reply, dict) or reply.get("ok") is not True or "id" not in reply:
                    raise ValueError("server did not acknowledge durable storage")
                self.store.ack(row["id"])
                self.last_delivery = iso_now()
            except Exception as exc:
                self.store.retry(row, error_code(exc), now)
                self.report_fault("server_delivery", True, "Server delivery is delayed; records remain queued", error_code(exc))
                # Avoid a slow offline queue blocking health for minutes.
                break
        else:
            if self.last_delivery:
                self.report_fault("server_delivery", False, "Server delivery recovered")

    def heartbeat(self):
        audio = inference = None
        for route, kind in (("/api/v2/health/audio", "audio"), ("/api/v2/system/inference", "inference")):
            try:
                value = self.birdnet(route)
                if kind == "audio": audio = value
                else: inference = value
            except Exception:
                pass  # Permission denied/unavailable health means unknown, never healthy.
        self.audio_status, self.inference_status = interpret_health(audio, inference, self.config)
        self.last_health = iso_now()
        for kind, status in (("audio", self.audio_status), ("inference", self.inference_status)):
            if status == "failed":
                self.report_fault(kind, True, kind.capitalize() + " pipeline reports a fault")
            elif status == "healthy":
                self.report_fault(kind, False, kind.capitalize() + " pipeline recovered")
        body = {"station_id": self.config["station_id"], "audio_status": self.audio_status,
                "inference_status": self.inference_status, "uptime_seconds": round(time.monotonic() - self.started),
                "version": VERSION}
        # Heartbeats are current state; do not queue/replay stale healthy heartbeats.
        self.transport(self.config["server_url"] + "/api/ingest/heartbeat", self.token, body, timeout=8)

    def diagnostics(self):
        return {"relay_version": VERSION, "station_id": self.config["station_id"],
                "birdnet_expected_version": BIRDNET_RELEASE, "birdnet_reported_version": self.birdnet_version,
                "audio_status": self.audio_status, "inference_status": self.inference_status,
                "last_poll": self.last_poll, "last_delivery": self.last_delivery, "last_health": self.last_health,
                "history_day": self.store.get("history_day"), "queue": self.store.snapshot(),
                "disk_free_bytes": shutil.disk_usage(self.config["data_dir"]).free}

    def collector_loop(self):
        delay = self.config["poll_seconds"]
        while not self.stop.is_set():
            try:
                free = shutil.disk_usage(self.config["data_dir"]).free
                if free < 100 * 1024 * 1024:
                    self.report_fault("storage", True, "Pi storage is low; history collection paused", "less than 100 MiB free")
                    self.stop.wait(60)
                    continue
                self.report_fault("storage", False, "Pi storage recovered; history collection resumed")
                self.poll()
                delay = self.config["poll_seconds"]
            except Exception as exc:
                LOG.warning("History poll failed: %s", error_code(exc))
                self.report_fault("birdnet_history", True, "BirdNET history could not be read; catch-up will retry", error_code(exc))
                delay = min(300, max(5, delay * 2))
            self.stop.wait(delay)

    def delivery_loop(self):
        next_heartbeat = next_backup = 0
        while not self.stop.is_set():
            try:
                now = time.monotonic()
                if now >= next_heartbeat:
                    next_heartbeat = now + self.config["heartbeat_seconds"]
                    try:
                        self.heartbeat()
                    except Exception as exc:
                        self.report_fault("server_heartbeat", True, "Server heartbeat delivery failed", error_code(exc))
                    else:
                        self.report_fault("server_heartbeat", False, "Server heartbeat recovered")
                self.deliver()
                if now >= next_backup:
                    self.store.backup()
                    next_backup = now + 3600
                self.report_fault("maintenance", False, "Pi maintenance recovered")
            except Exception as exc:
                LOG.error("Maintenance loop failed: %s", error_code(exc))
                self.report_fault("maintenance", True, "Pi maintenance needs attention", error_code(exc))
            self.stop.wait(1)


def make_handler(relay):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            path = urllib.parse.urlsplit(self.path).path
            if path == "/health":
                payload = {"ok": True, "service": "songsketch-pi", "version": VERSION}
            elif path in ("/diagnostics", "/reports"):
                supplied = self.headers.get("Authorization", "")
                if not hmac.compare_digest(supplied, "Bearer " + relay.token):
                    self.send_error(401, "Authentication required")
                    return
                payload = relay.diagnostics() if path == "/diagnostics" else {"reports": relay.store.reports()}
            else:
                self.send_error(404)
                return
            raw = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
    return Handler


def load_config(path):
    config = json.loads(Path(path).read_text())
    defaults = {"station_id": "garden", "birdnet_url": "http://127.0.0.1:8080",
                "data_dir": "/var/lib/songsketch-pi", "token_file": "/etc/songsketch-pi/station.token",
                "timezone": "Europe/London", "poll_seconds": 5, "heartbeat_seconds": 15,
                "initial_history_days": 30, "model_id": "BirdNET_V2.4", "listen_host": "127.0.0.1", "listen_port": 8081}
    config = {**defaults, **config}
    for key in ("server_url", "birdnet_url"):
        config[key] = validate_url(config[key])
    for key in ("station_id", "source_instance_id"):
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", config.get(key, "")):
            raise ValueError("invalid " + key)
    ZoneInfo(config["timezone"])
    if not 1 <= config["poll_seconds"] <= 300 or not 5 <= config["heartbeat_seconds"] <= 60:
        raise ValueError("invalid polling interval")
    if not 0 <= config["initial_history_days"] <= 3650:
        raise ValueError("invalid initial history window")
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="/etc/songsketch-pi/config.json")
    parser.add_argument("--check", action="store_true", help="Read configuration and check API contracts; do not send detections")
    parser.add_argument("--diagnostics", action="store_true", help="Print redacted diagnostics without network calls")
    parser.add_argument("--rescan-from", metavar="YYYY-MM-DD", help="Rescan stored BirdNET records from this date; deduplication is preserved")
    args = parser.parse_args()
    os.umask(0o077)
    config = load_config(args.config)
    relay = Relay(config)
    if args.rescan_from:
        day = dt.date.fromisoformat(args.rescan_from)
        relay.store.set("history_day", (day + dt.timedelta(days=1)).isoformat())
        print("History rescan checkpoint saved; no recorded detections were removed.")
        relay.store.close(); return
    if args.diagnostics:
        print(json.dumps(relay.diagnostics(), indent=2)); relay.store.close(); return
    if args.check:
        results = {}
        for key, route in (("birdnet", "/api/v2/health"), ("history", "/api/v2/detections?numResults=1"),
                           ("audio", "/api/v2/health/audio"), ("inference", "/api/v2/system/inference")):
            try:
                response = relay.birdnet(route)
                if key == "birdnet": results[key] = {"reachable": True, "version": response.get("version"), "expected": BIRDNET_RELEASE}
                elif key == "history": results[key] = {"contract_ok": isinstance(response.get("data"), list) and isinstance(response.get("total"), int)}
                else: results[key] = {"readable": True}
            except Exception as exc: results[key] = {"error": error_code(exc)}
        print(json.dumps(results, indent=2)); relay.store.close(); return
    handler = logging.handlers.RotatingFileHandler(Path(config["data_dir"]) / "relay.log", maxBytes=2_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    LOG.addHandler(handler); LOG.addHandler(logging.StreamHandler()); LOG.setLevel(logging.INFO)
    try:
        relay.birdnet_version = relay.birdnet("/api/v2/health").get("version")
        if BIRDNET_RELEASE not in str(relay.birdnet_version):
            relay.report_fault("birdnet_version", True, "BirdNET version differs from the tested source contract")
    except Exception:
        pass
    server = http.server.ThreadingHTTPServer((config["listen_host"], config["listen_port"]), make_handler(relay))
    server.daemon_threads = True
    threads = [threading.Thread(target=relay.collector_loop), threading.Thread(target=relay.delivery_loop),
               threading.Thread(target=server.serve_forever)]
    for thread in threads: thread.start()
    for sig in (signal.SIGTERM, signal.SIGINT): signal.signal(sig, lambda *_: relay.stop.set())
    LOG.info("Songsketch Pi relay started")
    failed = False
    while not relay.stop.wait(1):
        if any(not thread.is_alive() for thread in threads):
            LOG.error("A relay worker stopped; supervisor restart required")
            failed = True
            relay.stop.set()
    server.shutdown(); server.server_close()
    for thread in threads: thread.join(timeout=30)
    relay.store.close()
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
