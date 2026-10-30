"""Durable event history, playback queue, diagnostics and notification outbox."""
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
from pathlib import Path
import random
import re
import sqlite3
import threading
import uuid
from zoneinfo import ZoneInfo
from . import __version__

def utcnow():
    return datetime.now(timezone.utc)

def iso(value=None):
    return (value or utcnow()).astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("observed_at must be an ISO timestamp with a timezone")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Timestamps need a timezone")
    return dt.astimezone(timezone.utc)

def short_text(value, name, maximum=200):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise ValueError("Invalid " + name)
    return value.strip()

def redact(value, secret_values=()):
    if isinstance(value, dict):
        return {k: "[redacted]" if re.search(r"password|token|secret|api.?key|authorization|cookie", k, re.I) else redact(v, secret_values) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, secret_values) for v in value[:200]]
    if isinstance(value, str):
        for secret in secret_values:
            if isinstance(secret, str) and len(secret) >= 5:
                value = value.replace(secret, "[redacted]")
        value = re.sub(r"(?i)(bearer\s+)[\w.\-]+", r"\1[redacted]", value)
        value = re.sub(r"\bsk-[A-Za-z0-9_\-]{8,}\b", "[redacted]", value)
        value = re.sub(r"(?i)((?:password|token|secret|api[_-]?key)\s*[:=]\s*)[^\s,;]+", r"\1[redacted]", value)
        return value[:12000]
    return value

SCHEMA = """
CREATE TABLE IF NOT EXISTS detections (
 id INTEGER PRIMARY KEY, event_id TEXT NOT NULL, station_id TEXT NOT NULL,
 scientific_name TEXT NOT NULL, common_name TEXT NOT NULL, confidence REAL NOT NULL,
 observed_at TEXT NOT NULL, received_at TEXT NOT NULL, test INTEGER NOT NULL DEFAULT 0,
 qualifies INTEGER NOT NULL, UNIQUE(station_id,event_id));
CREATE INDEX IF NOT EXISTS detections_species_time ON detections(scientific_name,observed_at);
CREATE INDEX IF NOT EXISTS detections_time ON detections(observed_at);
CREATE TABLE IF NOT EXISTS stations (station_id TEXT PRIMARY KEY, received_at TEXT NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY, event_id TEXT, scientific_name TEXT, data TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reports (report_id TEXT PRIMARY KEY, station_id TEXT, received_at TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS issues (id TEXT PRIMARY KEY,severity TEXT,message TEXT,first_seen TEXT,last_seen TEXT,occurrences INTEGER,resolved INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS missing_art (scientific_name TEXT PRIMARY KEY,common_name TEXT,first_seen TEXT,last_seen TEXT,resolved INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS email_outbox (id TEXT PRIMARY KEY,kind TEXT,species TEXT,status TEXT,attempts INTEGER DEFAULT 0,next_attempt TEXT,last_error TEXT,created_at TEXT,sent_at TEXT);
CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY,kind TEXT,scientific_name TEXT,status TEXT,message TEXT,created_at TEXT,updated_at TEXT,request TEXT,result TEXT);
CREATE TABLE IF NOT EXISTS listening_windows (id INTEGER PRIMARY KEY,start_at TEXT NOT NULL,last_at TEXT NOT NULL,open INTEGER NOT NULL);
PRAGMA user_version=1;
"""

def validate_hardware(value):
    """Accept only bounded measurements with internally consistent status.

    Absence means an older relay/unknown hardware. These observations do not
    prove supply suitability or establish a hardware commissioning pass.
    """
    if value is None:
        return None
    fields = {"observed_at", "power_status", "thermal_status", "temperature_c", "temperature_source",
              "throttled_hex", "current_flags", "historical_flags", "sample_errors", "thermal_warning_c"}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("Invalid hardware measurement fields")
    observed = iso(timestamp(value["observed_at"]))
    allowed_flags = ("under_voltage", "frequency_capped", "throttled", "soft_temperature_limit")
    flags = {}
    for key in ("current_flags", "historical_flags"):
        supplied = value[key]
        if not isinstance(supplied, list) or len(supplied) > 4 or any(not isinstance(flag, str) or flag not in allowed_flags for flag in supplied) or len(set(supplied)) != len(supplied):
            raise ValueError("Invalid hardware flags")
        flags[key] = supplied[:]
    mask = value["throttled_hex"]
    if mask is not None and (not isinstance(mask, str) or not re.fullmatch(r"0x[0-9a-fA-F]{1,8}", mask)):
        raise ValueError("Invalid hardware throttle mask")
    bits = int(mask, 16) if mask is not None else None
    for key, offset in (("current_flags", 0), ("historical_flags", 16)):
        expected = [flag for n, flag in enumerate(allowed_flags) if bits is not None and bits & (1 << (n + offset))]
        if flags[key] != expected:
            raise ValueError("Hardware flags do not match the measurement")
    temperature, source = value["temperature_c"], value["temperature_source"]
    if temperature is not None and (isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not math.isfinite(temperature) or not -40 <= temperature <= 150):
        raise ValueError("Invalid hardware temperature")
    if source not in ("vcgencmd", "sysfs", "unavailable") or (temperature is None) != (source == "unavailable"):
        raise ValueError("Invalid temperature source")
    errors = value["sample_errors"]
    allowed_errors = {kind + "_" + error for kind in ("throttled", "temperature") for error in ("unavailable", "timeout", "invalid")}
    if not isinstance(errors, list) or len(errors) > 2 or any(not isinstance(error, str) or error not in allowed_errors for error in errors) or len(set(errors)) != len(errors):
        raise ValueError("Invalid hardware sampling evidence")
    if isinstance(value["thermal_warning_c"], bool) or value["thermal_warning_c"] != 75:
        raise ValueError("Invalid provisional temperature warning")
    power_status = "unknown" if bits is None else "warning" if bits & 0b111 else "healthy"
    thermal_status = "warning" if (bits is not None and bits & 0b1000) or temperature is not None and temperature >= 75 else "healthy" if temperature is not None and bits is not None else "unknown"
    if value["power_status"] != power_status or value["thermal_status"] != thermal_status:
        raise ValueError("Hardware status does not match the measurements")
    return {"observed_at": observed, "power_status": power_status, "thermal_status": thermal_status,
            "temperature_c": temperature, "temperature_source": source,
            "throttled_hex": hex(bits) if bits is not None else None, **flags,
            "sample_errors": errors[:], "thermal_warning_c": 75}


class Store:
    def __init__(self, config, catalogue_path, reference_registry=None):
        self.config = config
        self.path = config.directory / "songsketch.sqlite3"
        self.lock = threading.RLock()
        self.tx_depth = 0
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("PRAGMA busy_timeout=30000")
        self.conn.executescript(SCHEMA)
        self.catalogue_path = Path(catalogue_path)
        packaged = Path(__file__).resolve().parents[1] / "artwork/catalogue.json"
        self.reference_registry_path = (None if reference_registry is False else
            Path(reference_registry) if reference_registry is not None else
            packaged.with_name("registry.json") if self.catalogue_path.resolve() == packaged.resolve() else None)
        self.birds = []
        self.reload_catalogue()
        with self.tx() as db:
            # A network call may have succeeded just before a crash. Never repeat it automatically.
            db.execute("UPDATE jobs SET status='failed',message='Interrupted by restart. Review the provider account before starting another paid request.' WHERE status IN ('queued','running')")
            db.execute("UPDATE email_outbox SET status='uncertain',last_error='Server restarted during send; check the inbox before retrying.' WHERE status='sending'")

    @contextmanager
    def tx(self):
        with self.lock:
            self.tx_depth += 1
            try:
                yield self.conn
                if self.tx_depth == 1:
                    self.conn.commit()
            except Exception:
                if self.tx_depth == 1:
                    self.conn.rollback()
                raise
            finally:
                self.tx_depth -= 1

    def query(self, sql, params=()):
        with self.lock:
            return [dict(row) for row in self.conn.execute(sql, params).fetchall()]

    def reload_catalogue(self):
        self.birds = json.loads(self.catalogue_path.read_text()).get("birds", []) if self.catalogue_path.exists() else []
        extra = self.config.directory / "approved-artwork.json"
        if extra.exists():
            self.birds += json.loads(extra.read_text()).get("birds", [])
        self.by_name = {}
        for b in self.birds:
            if b.get("approved", b.get("artwork_approved", False)):
                for name in [b.get("scientific_name", ""), b.get("common_name", "")] + b.get("aliases", []):
                    self.by_name[name.casefold()] = b
        # The reference library proves final-art availability, not playback
        # readiness. Never promote its animation flags into the player catalogue.
        self.reference_birds, self.references_by_name = self.load_reference_art()
        with self.tx() as db:
            for b in list(self.by_name.values()) + self.reference_birds:
                for name in {b["scientific_name"], *b.get("aliases", [])}:
                    db.execute("UPDATE missing_art SET resolved=1 WHERE scientific_name=? COLLATE NOCASE", (name,))
                    db.execute("UPDATE email_outbox SET status='resolved' WHERE species=? COLLATE NOCASE AND status IN ('pending','failed')", (name,))

    def load_reference_art(self):
        path = self.reference_registry_path
        if path is None or not path.exists():
            return [], {}
        if path.is_symlink() or path.stat().st_size > 1_000_000:
            raise ValueError("Invalid final-art reference registry")
        registry = json.loads(path.read_text())
        entries = registry.get("birds") if isinstance(registry, dict) else None
        if not isinstance(registry, dict) or registry.get("schema_version") != 1 or not isinstance(entries, list) or len(entries) > 500:
            raise ValueError("Invalid final-art reference registry")
        birds, by_name = [], {}
        root = path.parent.resolve()
        for item in entries:
            if not isinstance(item, dict) or item.get("final_art_accepted") is not True:
                continue
            if item.get("final_art_status") not in ("approved", "accepted_for_animation"):
                raise ValueError("Final-art acceptance status is inconsistent")
            ident = short_text(item.get("id"), "reference id", 80)
            scientific = short_text(item.get("scientific_name"), "reference species", 120)
            common = short_text(item.get("common_name"), "reference name", 120)
            aliases = item.get("aliases", [])
            if not isinstance(aliases, list) or len(aliases) > 30:
                raise ValueError("Invalid final-art aliases")
            aliases = [short_text(name, "reference alias", 120) for name in aliases]
            relative = Path(short_text(item.get("reference_path"), "reference path", 300))
            if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                raise ValueError("Invalid final-art image path")
            image = root / relative
            if not image.is_file() or image.is_symlink() or any(parent.is_symlink() for parent in image.parents if parent != root) or root not in image.resolve().parents or image.stat().st_size > 20_000_000:
                raise ValueError("Final-art reference image is missing or unsafe")
            expected = item.get("reference_sha256")
            if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise ValueError("Final-art reference hash is missing")
            digest = hashlib.sha256()
            with image.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
            if digest.hexdigest() != expected:
                raise ValueError("Final-art reference image does not match its approved snapshot")
            bird = {"id": ident, "scientific_name": scientific, "common_name": common, "aliases": aliases,
                    "approved": True, "artwork_approved": True, "final_art_available": True,
                    "final_art_status": item["final_art_status"], "animation_ready": False,
                    "reference_only": True, "image_url": "/artwork/" + relative.as_posix()}
            birds.append(bird)
            for name in [scientific, common, *aliases]:
                key = name.casefold()
                if key in by_name and by_name[key]["scientific_name"] != scientific:
                    raise ValueError("Final-art reference alias is ambiguous")
                by_name[key] = bird
        return birds, by_name

    def bird(self, name):
        key = str(name).casefold()
        return self.by_name.get(key) or self.references_by_name.get(key)

    def meta(self, key, default=None):
        rows = self.query("SELECT value FROM meta WHERE key=?", (key,))
        return json.loads(rows[0]["value"]) if rows else default

    def set_meta(self, key, value):
        with self.tx() as db:
            db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, json.dumps(value)))

    def month_start(self):
        local = utcnow().astimezone(ZoneInfo(self.config.values["timezone"]))
        return iso(local.replace(day=1,hour=0,minute=0,second=0,microsecond=0))

    def ingest(self, payload, force_test=False):
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object")
        station = short_text(payload.get("station_id", self.config.values["station_id"]), "station_id", 80)
        if station != self.config.values["station_id"] and not force_test:
            raise ValueError("This token belongs to a different station")
        event = short_text(payload.get("event_id"), "event_id", 200)
        scientific = short_text(payload.get("scientific_name"), "scientific_name", 120)
        common = short_text(payload.get("common_name", scientific), "common_name", 120)
        confidence = payload.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (float, int)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        when = timestamp(payload.get("observed_at"))
        if when > utcnow() + timedelta(minutes=5):
            raise ValueError("Detection is in the future; check the Pi clock")
        if not isinstance(payload.get("test", False), bool):
            raise ValueError("test must be true or false")
        test = force_test or payload.get("test", False)
        bird = self.bird(scientific) or self.bird(common)
        if bird:
            scientific, common = bird["scientific_name"], bird["common_name"]
        qualifies = confidence >= self.config.values["confidence_threshold"]
        now = iso()
        data = dict(event_id=event, station_id=station, scientific_name=scientific, common_name=common, confidence=confidence, observed_at=iso(when), test=bool(test))
        with self.tx() as db:
            from .capture_exclusion import contains
            captured_test = contains(self, when)
            test = test or captured_test
            data["test"] = bool(test)
            cur = db.execute("INSERT OR IGNORE INTO detections(event_id,station_id,scientific_name,common_name,confidence,observed_at,received_at,test,qualifies) VALUES (?,?,?,?,?,?,?,?,?)", (event, station, scientific, common, confidence, iso(when), now, int(test), int(qualifies)))
            if not cur.rowcount:
                return {"ok":True,"id":event,"duplicate":True}
            if qualifies and not test and not bird:
                db.execute("INSERT INTO missing_art VALUES (?,?,?,?,0) ON CONFLICT(scientific_name) DO UPDATE SET last_seen=MAX(last_seen,excluded.last_seen)", (scientific, common, iso(when), iso(when)))
                notification_id = hashlib.sha256(("missing-art:" + scientific).encode()).hexdigest()
                db.execute("INSERT OR IGNORE INTO email_outbox(id,kind,species,status,next_attempt,created_at) VALUES (?,'missing-art',?,'pending',?,?)", (notification_id, scientific, now, now))
            recent = (utcnow() - when).total_seconds() <= 120
            if not captured_test and qualifies and bird and bird.get("animation_ready") and (recent or test):
                last = self.meta("displayed:" + scientific)
                cooling = last and (utcnow() - timestamp(last)).total_seconds() < self.config.values["display_cooldown_seconds"]
                queued = db.execute("SELECT 1 FROM queue WHERE scientific_name=?", (scientific,)).fetchone()
                if test or (not cooling and not queued):
                    db.execute("INSERT INTO queue(event_id,scientific_name,data,created_at) VALUES (?,?,?,?)", (event, scientific, json.dumps(data), now))
                    db.execute("DELETE FROM queue WHERE id NOT IN (SELECT id FROM queue ORDER BY id DESC LIMIT 20)")
        if test and not captured_test and bird and bird.get("animation_ready"):
            # The setup button previews immediately; a real song never interrupts a painting.
            self.set_meta("test_override", event)
            self.set_meta("current", None)
        return {"ok":True,"id":event,"duplicate":False,"qualifies":bool(qualifies),"test":bool(test),"commissioning_capture":captured_test}

    def heartbeat(self, data):
        station = short_text(data.get("station_id", "garden"), "station_id", 80)
        if station != self.config.values["station_id"]:
            raise ValueError("Unexpected station_id")
        for key in ("audio_status", "inference_status"):
            if data.get(key, "unknown") not in ("healthy", "failed", "unknown"):
                raise ValueError("Invalid " + key)
        safe = redact(data, self.config.secrets.values())
        safe["hardware"] = validate_hardware(data.get("hardware"))
        from .branch import record_health
        with self.tx() as db:
            record_health(db, safe, utcnow(), self.config.values["heartbeat_timeout_seconds"])
            db.execute("INSERT OR REPLACE INTO stations VALUES (?,?,?)", (station, iso(), json.dumps(safe)))
            db.execute("UPDATE issues SET resolved=1 WHERE id='pi-disconnected'")
        return {"ok":True,"id":station,"duplicate":False}

    def station_status(self):
        rows = self.query("SELECT * FROM stations WHERE station_id=?", (self.config.values["station_id"],))
        if not rows:
            return {"station_id":self.config.values["station_id"],"connected":False,"ever_connected":False,"listening":"unknown","last_heartbeat":None,"audio_status":"unknown","inference_status":"unknown","hardware":None}
        row = rows[0]
        data = json.loads(row["data"])
        connected = (utcnow() - timestamp(row["received_at"])).total_seconds() <= self.config.values["heartbeat_timeout_seconds"]
        audio, inference = data.get("audio_status", "unknown"), data.get("inference_status", "unknown")
        listening = "unknown"
        if connected:
            if audio == inference == "healthy": listening = "available"
            elif "failed" in (audio, inference): listening = "unavailable"
        try:
            hardware = validate_hardware(data.get("hardware"))
        except (TypeError, ValueError, OverflowError):
            hardware = None  # Older/unvalidated stored metadata is not live proof.
        return {"station_id":row["station_id"],"connected":connected,"ever_connected":True,"listening":listening,"last_heartbeat":row["received_at"],"audio_status":audio,"inference_status":inference,"hardware":hardware}

    def report(self, data):
        rid = short_text(data.get("report_id"), "report_id", 200)
        station = short_text(data.get("station_id", "garden"), "station_id", 80)
        message = short_text(data.get("message"), "message", 1000)
        severity = data.get("severity", "warning")
        if severity not in ("info", "warning", "error"):
            raise ValueError("Invalid severity")
        clean = redact(data, self.config.secrets.values())
        if isinstance(data.get("details"), dict) and "hardware" in data["details"]:
            clean["details"]["hardware"] = validate_hardware(data["details"]["hardware"])
        message = redact(message, self.config.secrets.values())
        component = data.get("details", {}).get("component") if isinstance(data.get("details", {}),dict) else None
        fingerprint = hashlib.sha256((station + ":" + str(component or (severity + message))).encode()).hexdigest()[:24]
        with self.tx() as db:
            cur = db.execute("INSERT OR IGNORE INTO reports VALUES (?,?,?,?)", (rid,station,iso(),json.dumps(clean)))
            if not cur.rowcount:
                return {"ok":True,"id":rid,"duplicate":True}
            recovered = data.get("resolved") is True or (isinstance(data.get("details"),dict) and data["details"].get("state") == "recovered")
            self.issue(fingerprint, severity, message, resolved=recovered)
        return {"ok":True,"id":rid,"duplicate":False}

    def issue(self, key, severity, message, resolved=False):
        with self.tx() as db:
            db.execute("INSERT INTO issues VALUES (?,?,?,?,?,1,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,occurrences=occurrences+1,resolved=excluded.resolved,message=excluded.message", (key,severity,redact(message,self.config.secrets.values()),iso(),iso(),int(resolved)))

    def summary(self, period="month", since=None, until=None):
        since = iso(timestamp(since)) if since else (self.month_start() if period == "month" else "1970-01-01T00:00:00Z")
        until = iso(timestamp(until)) if until else iso(utcnow() + timedelta(minutes=5))
        rows = self.query("SELECT scientific_name,MAX(common_name) common_name,COUNT(*) count,MIN(observed_at) first_heard,MAX(observed_at) last_heard,MAX(confidence) confidence FROM detections WHERE test=0 AND qualifies=1 AND observed_at>=? AND observed_at<=? GROUP BY scientific_name ORDER BY count DESC,last_heard DESC", (since,until))
        for row in rows:
            b = self.bird(row["scientific_name"])
            row.update(has_artwork=bool(b), final_art_available=bool(b), has_animation=bool(b and b.get("animation_ready")),
                       animation_ready=bool(b and b.get("animation_ready")))
            mail = self.query("SELECT status FROM email_outbox WHERE species=?", (row["scientific_name"],))
            row["email_status"] = mail[0]["status"] if mail else None
        return rows

    def public_status(self):
        return {"version":__version__,"station":self.station_status(),"current":self.meta("current"),"queue_count":self.query("SELECT COUNT(*) n FROM queue")[0]["n"],"server_time":iso(),"timezone":self.config.values["timezone"]}

    def tick(self):
        with self.lock:
            return self._tick_locked()

    def _tick_locked(self):
        current = self.meta("current")
        elapsed = (utcnow() - timestamp(current["started_at"])).total_seconds() if current else float("inf")
        if current and elapsed < 75 + self.config.values["hold_seconds"]:
            return
        with self.tx() as db:
            db.execute("DELETE FROM queue WHERE created_at<?", (iso(utcnow() - timedelta(minutes=5)),))
            override = self.meta("test_override")
            queued = db.execute("SELECT * FROM queue WHERE event_id=? ORDER BY id DESC LIMIT 1", (override,)).fetchone() if override else None
            if queued:
                self.set_meta("test_override", None)
            else:
                queued = db.execute("SELECT * FROM queue ORDER BY id LIMIT 1").fetchone()
            if queued:
                db.execute("DELETE FROM queue WHERE id=?", (queued["id"],))
                next_item = json.loads(queued["data"])
                b = self.bird(next_item["scientific_name"])
                mode = "live"
                if not next_item.get("test"):
                    self.set_meta("displayed:" + next_item["scientific_name"], iso())
            else:
                ready = [b for b in self.birds if b.get("approved") and b.get("animation_ready")]
                if not ready: return
                counts = {x["scientific_name"]:x for x in self.summary()}
                # Square-root weighting keeps frequent visitors familiar without monopolising the wall.
                candidates = [b for b in ready if not current or b["id"] != current.get("artwork_id")] or ready
                b = random.choices(candidates,weights=[1 + math.sqrt(counts.get(b["scientific_name"],{}).get("count",0)) for b in candidates])[0]
                prior = counts.get(b["scientific_name"])
                if not prior:
                    historic = self.query("SELECT MAX(observed_at) last_heard FROM detections WHERE scientific_name=? AND test=0 AND qualifies=1", (b["scientific_name"],))
                    prior = historic[0] if historic and historic[0]["last_heard"] else None
                mode = "monthly" if b["scientific_name"] in counts else ("last_heard" if prior else "local")
                next_item = {"event_id":str(uuid.uuid4()),"scientific_name":b["scientific_name"],"common_name":b["common_name"],"observed_at":prior["last_heard"] if prior else None,"test":False}
            if not b or not b.get("animation_ready"): return
            month = self.query("SELECT COUNT(*) n FROM detections WHERE scientific_name=? AND observed_at>=? AND test=0 AND qualifies=1", (b["scientific_name"],self.month_start()))[0]["n"]
            next_item.update(artwork_id=b["id"],mode=mode,started_at=iso(),duration_seconds=75,monthly_count=month)
            self.set_meta("current", next_item)

    def diagnostics(self):
        supervisor = None
        state = self.config.directory / "supervisor-status.json"
        if state.exists():
            try: supervisor = json.loads(state.read_text())
            except (OSError,ValueError): supervisor = {"state":"unknown"}
        return redact({"version":__version__,"generated_at":iso(),"station":self.station_status(),"queue_count":self.public_status()["queue_count"],"supervisor":supervisor,"issues":self.query("SELECT * FROM issues ORDER BY last_seen DESC LIMIT 50"),"reports":[json.loads(r["data"]) for r in self.query("SELECT data FROM reports ORDER BY received_at DESC LIMIT 30")],"database_check":self.query("PRAGMA quick_check")[0],"note":"No audio, credentials or full detection history is included."}, self.config.secrets.values())

    def close(self):
        with self.lock:
            self.conn.close()
