"""An explicitly synthetic, loopback-only garden using the real ingestion handlers.

No AI/SSH clients or SMTP transports are constructed. Scenario fixture changes
and clock ageing are confined to a marked, separate database; hardware is never
contacted. Software assertions do not assess animation quality.
"""
import argparse
from datetime import timedelta
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer
import hashlib
import http.client
import json
import os
from pathlib import Path
import random
import secrets
import sys
import threading
import time
from urllib.parse import parse_qs, unquote, urlparse
import uuid
import webbrowser

from . import __version__
from .config import Config, DEFAULTS, ROOT, data_directory, private_json
from .locking import RunLock
from .maintenance import Maintenance
from .server import App, Handler, Server
from .setup_health import build_setup_health
from .store import Store, iso, redact, utcnow

MODE = "songsketch-simulation"
COOKIE = "songsketch_simulation_session"
BLOCKED = "This is the simulated garden. Email, paid AI, SSH, installation and real settings changes are disabled."
LIMITATIONS = [
    "Synthetic events exercise the server; they do not test BirdNET recognition, a microphone, real Pi power or network hardware.",
    "Email is captured locally. No SMTP, paid AI, SSH or installation actions are available.",
    "Each scenario replaces the simulated garden history. Earlier scenario reports remain available.",
    "Painting timing and visual quality need human review; automatic checks never certify the brushwork.",
]


def scenario(key, title, description, *expected):
    return dict(id=key, title=title, description=description, expected=list(expected))


SCENARIOS = [
    scenario("known-bird", "A familiar bird sings", "A synthetic Robin reaches the real detection endpoint and starts its painting.", "One qualifying detection", "Robin painting selected"),
    scenario("duplicate-retry", "The same message arrives twice", "Resend one event, then send another genuine event during display cooldown.", "Retry counted once", "Distinct observations retained", "No repeated queue entry"),
    scenario("missing-art", "A visitor needs a portrait", "A deliberately fictional QA species has no artwork. Its first notification stays in the local inbox.", "One locally captured notification", "Two observations recorded", "Working painting retained"),
    scenario("pi-disconnect", "The garden Pi goes quiet", "Age the last synthetic heartbeat beyond the real timeout; keep the disconnected state visible.", "Connection unavailable", "Listening unknown", "Painting continues"),
    scenario("pi-reconnect", "The garden Pi returns", "First age a heartbeat, then deliver a fresh one through the real endpoint.", "Disconnect recognised", "Fresh heartbeat restores listening"),
    scenario("disconnect-reconnect", "A connection survives a retry", "Exercise heartbeat loss and restoration, then retry the same bird event.", "Listening restored", "Delivery retry counted once"),
    scenario("capture-failure", "The microphone stops capturing", "Send fresh Pi health with failed capture, plus a deduplicated diagnostic report.", "Pi remains connected", "Listening unavailable", "Capture issue recorded"),
    scenario("inference-failure", "Bird recognition stops", "Capture remains healthy but synthetic inference fails.", "Pi remains connected", "Listening unavailable", "Recognition issue recorded"),
    scenario("power-warning", "The Pi reports low voltage", "Supply a synthetic current under-voltage bit. This is not a physical voltage test.", "Power warning shown", "Historical flags kept distinct"),
    scenario("thermal-warning", "The Pi reports heat", "Supply a synthetic 78°C reading above the provisional 75°C warning threshold.", "Thermal warning shown", "No shutdown action"),
    scenario("recovery", "The garden recovers", "Create capture, inference, power and heat faults, then send healthy readings and recovery reports.", "Listening available", "Faults resolved", "Historical power evidence retained"),
    scenario("burst-idle", "A busy chorus, then a pause", "A seeded burst includes a retry and a low-confidence record; advance the fixture clock to inspect idle selection.", "Only qualifying unique events counted", "Idle mode selected", "Familiarity weights use recorded counts"),
]


def simulation_directory():
    base = Path.home() / ("Library/Application Support" if sys.platform == "darwin" else ".local/share")
    return base / "Songsketch Simulation"


def prepare_directory(value):
    """Never adopt a normal installation or follow runtime-file symlinks."""
    path = Path(value).expanduser().absolute()
    real = data_directory().resolve()
    resolved = path.resolve()
    if path.is_symlink() or resolved == real or real in resolved.parents or resolved in real.parents:
        raise ValueError("Choose a separate simulation folder, outside the real Songsketch data folder.")
    if path.exists() and not path.is_dir():
        raise ValueError("The simulation data path must be a directory.")
    marker = path / "simulation.json"
    if path.exists() and any(path.iterdir()):
        if not marker.is_file() or marker.is_symlink() or marker.stat().st_size > 1024:
            raise ValueError("Refusing an existing unmarked folder. Choose a new empty simulation folder.")
        for entry in path.rglob("*"):
            if entry.is_symlink():
                raise ValueError("Simulation runtime files must not be symlinks.")
        info = json.loads(marker.read_text())
        if not isinstance(info,dict) or info.get("mode") != MODE or info.get("version") != 1 or not isinstance(info.get("id"), str) or len(info["id"]) != 32:
            raise ValueError("The simulation folder marker is invalid.")
    else:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        info = {"mode":MODE, "version":1, "id":uuid.uuid4().hex}
        private_json(marker, info)
    os.chmod(path, 0o700)
    return path, info


def disabled(*args, **kwargs):
    raise ValueError(BLOCKED)


class SimulationConfig(Config):
    def __init__(self, directory):
        super().__init__(directory)
        # Persisted provider configuration is never used, even if hand-edited.
        self.values = dict(DEFAULTS, site_name="Simulated garden · no live audio")
        self.secrets = {k:self.secrets[k] for k in ("admin_token", "station_token")}

    update = disabled


class DisabledJobs:
    requester = staticmethod(disabled)
    start = run = approve = staticmethod(disabled)
    def list(self): return []


class DisabledCommissioning:
    action = staticmethod(disabled)
    def status(self): return {"available":False,"simulation":True,"job":None,"message":BLOCKED}
    def close(self): pass


class SimulationStore(Store):
    def __init__(self, config, catalogue, preview_candidates=False):
        self.preview_candidates = preview_candidates
        super().__init__(config, catalogue)

    def reload_catalogue(self):
        super().reload_catalogue()
        if not self.preview_candidates: return
        # Runtime preview eligibility is not an artwork/animation approval.
        # The candidate file and the production catalogue are never changed.
        for bird in self.birds:
            if bird.get("approved") is True: continue
            if not (bird.get("approved") is False and bird.get("animation_ready") is True and
                    bird.get("artwork_approved") is True and bird.get("production_eligible") is False and
                    bird.get("review_status") == "completed_awaiting_review"):
                raise ValueError("Candidate catalogue contains an entry without explicit review-only eligibility.")
            for field in ("image_url", "animation_url"):
                url = bird.get(field, "")
                if not isinstance(url,str) or not url.startswith("/artwork/") or "?" in url or "#" in url or ".." in Path(url).parts:
                    raise ValueError("Candidate artwork must use bundled local artwork URLs.")
                asset=(ROOT/url.lstrip("/")).resolve()
                if ROOT.resolve() not in asset.parents or not asset.is_file():
                    raise ValueError("Candidate artwork asset is missing or outside the project.")
            bird.update(source_approved=False, candidate=True, approved=True)
            for name in [bird["scientific_name"],bird["common_name"],*bird.get("aliases",[])]:
                self.by_name[name.casefold()]=bird

    def public_status(self):
        return {**super().public_status(), "simulation":True, "live_audio":False}


class LocalMaintenance(Maintenance):
    """The mail boundary is a local capture, never an SMTP transport."""
    def send_mail(self):
        captured = []
        with self.store.tx() as db:
            rows = db.execute("SELECT * FROM email_outbox WHERE status IN ('pending','failed') ORDER BY created_at LIMIT 20").fetchall()
            for row in rows:
                if self.store.bird(row["species"]):
                    db.execute("UPDATE email_outbox SET status='resolved' WHERE id=?", (row["id"],))
                    continue
                detail = db.execute("SELECT * FROM missing_art WHERE scientific_name=? AND resolved=0", (row["species"],)).fetchone()
                if detail is None: continue
                captured.append({"id":row["id"],"species":row["species"],"common_name":detail["common_name"],
                                 "subject":"A new visitor needs a portrait: " + detail["common_name"],
                                 "recipient":"Local simulation inbox only", "captured_at":iso(), "external_delivery":False})
                db.execute("UPDATE email_outbox SET status='captured',attempts=attempts+1,last_error='Captured locally by simulator; not sent' WHERE id=?", (row["id"],))
            prior = self.store.meta("simulation_mail", [])
            self.store.set_meta("simulation_mail", (prior + captured)[-100:])
        return len(captured)

    def run(self):
        # Deliberately excludes normal backup/mail/provider/commissioning loops.
        while not self.stop.wait(.5):
            try:
                with self.app.scenario_lock:
                    if self.app.synthetic_health and time.monotonic() - self.app.last_heartbeat > 10:
                        self.app.send_heartbeat(self.app.synthetic_health)
                    self.store.tick()
            except (OSError,ValueError,http.client.HTTPException):
                if not self.stop.is_set():
                    self.store.issue("simulation-tick", "warning", "The simulated heartbeat could not refresh. Reopen the simulator and inspect its local report.")


class SimulationApp(App):
    def __init__(self, directory, candidate_catalogue=None):
        directory, self.marker = prepare_directory(directory)
        self.run_lock = RunLock(directory)
        try:
            self.config = SimulationConfig(directory)
            self.candidate_catalogue = Path(candidate_catalogue).expanduser().resolve() if candidate_catalogue else None
            catalogue = self.candidate_catalogue or ROOT / "artwork/catalogue.json"
            if self.candidate_catalogue and not catalogue.is_file():
                raise ValueError("The explicitly selected candidate catalogue does not exist.")
            self.store = SimulationStore(self.config, catalogue, preview_candidates=bool(self.candidate_catalogue))
            self.catalogue_sha256=hashlib.sha256(catalogue.read_bytes()).hexdigest()
            self.maintenance = LocalMaintenance(self.store)
            self.maintenance.app = self
            self.jobs = DisabledJobs()
            self.commissioning = DisabledCommissioning()
            self.sessions, self.setup_tickets, self.auth_attempts = {}, {}, {}
            self.auth_lock = threading.Lock()
            self.streams = threading.BoundedSemaphore(12)
            self.scenario_lock = threading.RLock()
            self.started = time.monotonic()
            self.port = None
            self.synthetic_health = None
            self.last_heartbeat = 0
            self.runs_folder = directory / "simulation-runs"
            self.runs_folder.mkdir(exist_ok=True, mode=0o700)
            self.store.set_meta("simulation", True)
            self.store.tick()
            self.thread = threading.Thread(target=self.maintenance.run, daemon=True)
        except Exception:
            self.run_lock.close()
            raise

    def start_ticks(self):
        if not self.thread.is_alive(): self.thread.start()

    def admin_status(self):
        result = super().admin_status()
        result["verification"] = {"real_pi":False,"hardware_checked":False,"simulation":True}
        result["count_definition"] = "Synthetic qualifying records in the isolated simulation database; not real birds or individual animals."
        result["simulation"] = True
        return result

    def setup_context(self):
        diagnostics = self.store.diagnostics()
        return {"simulation":True, "setup":self.commissioning.status(), "diagnostics":diagnostics,
                "health":build_setup_health(self.commissioning.status(), diagnostics), "limits":LIMITATIONS}

    def local_ingest(self, kind, value):
        """Exercise the production HTTP handler with private station credentials."""
        if self.port is None: raise RuntimeError("Start the simulation HTTP server first.")
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request("POST", "/api/ingest/" + kind, body=json.dumps(value), headers={"Content-Type":"application/json", "Authorization":"Bearer " + self.config.secrets["station_token"]})
            response = conn.getresponse()
            result = json.loads(response.read())
            if response.status != 200: raise ValueError("Synthetic ingestion failed: " + result.get("error", str(response.status)))
            return result
        finally: conn.close()

    @staticmethod
    def hardware(power=False, hot=False, history=False):
        return {"observed_at":iso(),"power_status":"warning" if power else "healthy", "thermal_status":"warning" if hot else "healthy",
                "temperature_c":78.0 if hot else 47.0,"temperature_source":"vcgencmd", "throttled_hex":hex((1 if power else 0) | (65536 if history else 0)),
                "current_flags":["under_voltage"] if power else [], "historical_flags":["under_voltage"] if history else [], "sample_errors":[],"thermal_warning_c":75}

    def send_heartbeat(self, health=None):
        health = dict(health or {"audio_status":"healthy", "inference_status":"healthy", "hardware":self.hardware()})
        if health.get("hardware"): health["hardware"] = dict(health["hardware"], observed_at=iso())
        result = self.local_ingest("heartbeat", {"station_id":"garden", **health})
        self.synthetic_health, self.last_heartbeat = health, time.monotonic()
        return result

    def age_heartbeat(self):
        self.synthetic_health = None
        # A fixture clock jump, not a claim of having waited 151 seconds.
        with self.store.tx() as db:
            db.execute("UPDATE stations SET received_at=?", (iso(utcnow()-timedelta(seconds=151)),))
        self.maintenance.check()

    def saved_runs(self):
        runs = []
        for path in sorted(self.runs_folder.glob("*.json"), reverse=True)[:100]:
            if path.stat().st_size <= 512000:
                try: runs.append(json.loads(path.read_text()))
                except (ValueError,OSError): pass
        return runs

    def state(self):
        runs = self.saved_runs()
        return {"simulation":True,"version":__version__,"mode":MODE,"limitations":LIMITATIONS,"scenarios":SCENARIOS,
                "runs":[{k:v for k,v in r.items() if k not in ("diagnostics","snapshot","steps")} for r in runs[:20]],
                "current_run":runs[0] if runs else None,"local_inbox":self.store.meta("simulation_mail",[]),
                "candidate_artwork":bool(self.candidate_catalogue),"catalogue_count":len(self.store.birds),
                "candidate_timing_note":"Cold preparation can consume part of a live event's 75-second window. Use the review gallery for a full candidate sequence after preparation." if self.candidate_catalogue else None,
                "links":{"painting":"/", "dashboard":"/dashboard", "report":"/api/simulation/report", "candidate_gallery":"/artwork/review.html"}}

    def reset_fixture(self):
        self.synthetic_health = None
        with self.store.tx() as db:
            for table in ("detections","stations","queue","reports","issues","missing_art","email_outbox","jobs","meta"):
                db.execute("DELETE FROM " + table)
        self.store.set_meta("simulation", True)

    def run_scenario(self, name, seed=20261022):
        if name not in {s["id"] for s in SCENARIOS}: raise ValueError("Choose a listed simulation scenario.")
        if isinstance(seed,bool) or not isinstance(seed,int) or not 0 <= seed <= 2147483647:
            raise ValueError("Seed must be an integer from 0 to 2147483647.")
        if not self.scenario_lock.acquire(blocking=False): raise ValueError("A scenario is already running.")
        run = {"id":uuid.uuid4().hex,"scenario":name,"seed":seed,"started_at":iso(),"checks":[],"steps":[],
               "manual_checks":[{"name":"Watch the complete 75-second painting and assess stroke flow, detail, status marks and final composition.","status":"not_checked"}],
               "simulation":True,"hardware_verified":False,"candidate_artwork":bool(self.candidate_catalogue)}
        def check(label, expected, actual):
            run["checks"].append(dict(name=label, expected=expected, actual=actual, passed=expected == actual))
        events = {}
        def event(index, species="Erithacus rubecula", confidence=.96):
            value = {"station_id":"garden","event_id":"qa-%s-%s-%s" % (run["id"],seed,index),"scientific_name":species,
                     "common_name":"Simulation-only visitor" if species == "Songsketch qa_species" else species,
                     "confidence":confidence,"observed_at":iso(),"test":False}
            value = events.setdefault(str(index),value)
            result = self.local_ingest("detections",value)
            run["steps"].append({"action":"POST /api/ingest/detections", "event":value,"result":result})
            return result
        def count(): return sum(b["count"] for b in self.store.summary("all"))
        def report(component, resolved=False, hardware=None):
            details = {"component":component,"state":"recovered" if resolved else "failed"}
            if hardware: details["hardware"] = hardware
            value = {"station_id":"garden","report_id":run["id"]+"-"+component+str(resolved),"message":"Simulated " + component + (" recovered" if resolved else " fault"),"severity":"info" if resolved else "warning","resolved":resolved,"details":details}
            result = self.local_ingest("reports",value)
            run["steps"].append({"action":"POST /api/ingest/reports","report":value,"result":result})
            return result
        try:
            self.reset_fixture()
            self.send_heartbeat()
            run["steps"].append({"action":"fixture_reset","note":"Only the marked simulation database is reset; previous run reports remain."})
            if name in ("known-bird", "duplicate-retry", "missing-art", "burst-idle"):
                if name == "known-bird":
                    event(1); self.store.tick()
                    check("Qualifying observations",1,count())
                    check("Selected artwork","robin",self.store.public_status()["current"]["artwork_id"])
                    check("Live display mode","live",self.store.public_status()["current"]["mode"])
                elif name == "duplicate-retry":
                    event(1); retry = event(1); self.store.tick(); event(2)
                    check("Retry recognised",True,retry["duplicate"])
                    check("Distinct observations",2,count())
                    check("Cooldown queue",0,self.store.public_status()["queue_count"])
                elif name == "missing-art":
                    event(1); self.store.tick(); before=self.store.meta("current")["event_id"]
                    event(2,"Songsketch qa_species"); event(3,"Songsketch qa_species")
                    self.maintenance.send_mail(); self.maintenance.send_mail(); self.store.tick()
                    check("Unknown-species observations",2,next(b["count"] for b in self.store.summary("all") if b["scientific_name"]=="Songsketch qa_species"))
                    check("Local notifications",1,len(self.store.meta("simulation_mail",[])))
                    check("External email sent",False,any(m["external_delivery"] for m in self.store.meta("simulation_mail",[])))
                    check("Existing painting retained",before,self.store.meta("current")["event_id"])
                else:
                    choices=[b["scientific_name"] for b in self.store.birds if b.get("animation_ready")]
                    rng=random.Random(seed)
                    for n in range(12): event(n,rng.choice(choices))
                    retry=event(0,choices[0]); event("quiet",choices[0],.1)
                    check("Qualifying unique observations",12,count())
                    check("Retry recognised",True,retry["duplicate"])
                    # Advance past buffered replay; use the real idle selector.
                    with self.store.tx() as db: db.execute("UPDATE queue SET created_at=?",(iso(utcnow()-timedelta(minutes=6)),))
                    self.store.set_meta("current",None); self.store.tick()
                    check("Expired replay queue",0,self.store.public_status()["queue_count"])
                    check("Idle repertoire mode",True,self.store.meta("current")["mode"] in ("monthly","last_heard","local"))
                    run["steps"].append({"action":"fixture_clock_advance","seconds":360,"note":"Aged replay queue only; no timer or visual completion is asserted."})
            elif name in ("pi-disconnect", "pi-reconnect", "disconnect-reconnect"):
                event(1); self.store.tick(); self.age_heartbeat()
                check("Stale heartbeat connected",False,self.store.station_status()["connected"])
                check("Listening after stale heartbeat","unknown",self.store.station_status()["listening"])
                run["steps"].append({"action":"fixture_clock_advance","seconds":151,"note":"Age received heartbeat beyond the production timeout."})
                if name != "pi-disconnect":
                    self.send_heartbeat()
                    check("Listening after reconnection","available",self.store.station_status()["listening"])
                if name == "disconnect-reconnect":
                    event(1); check("Retried observation count",1,count())
                check("Painting remains available",True,bool(self.store.meta("current")))
            elif name in ("capture-failure", "inference-failure"):
                capture = name == "capture-failure"
                self.send_heartbeat({"audio_status":"failed" if capture else "healthy","inference_status":"healthy" if capture else "failed","hardware":self.hardware()})
                report("capture" if capture else "inference"); duplicate=report("capture" if capture else "inference")
                self.store.tick()
                check("Pi remains connected",True,self.store.station_status()["connected"])
                check("Listening availability","unavailable",self.store.station_status()["listening"])
                check("Duplicate diagnostic recognised",True,duplicate["duplicate"])
                check("Unresolved fault",1,len(self.store.query("SELECT id FROM issues WHERE resolved=0")))
            elif name in ("power-warning", "thermal-warning"):
                power=name == "power-warning"; hardware=self.hardware(power=power,hot=not power,history=power)
                self.send_heartbeat({"audio_status":"healthy","inference_status":"healthy","hardware":hardware})
                report("power" if power else "thermal",hardware=hardware); self.store.tick()
                check("Reported warning","warning",self.store.station_status()["hardware"]["power_status" if power else "thermal_status"])
                check("Listening continues","available",self.store.station_status()["listening"])
                check("Historical flags",["under_voltage"] if power else [],self.store.station_status()["hardware"]["historical_flags"])
            elif name == "recovery":
                bad=self.hardware(power=True,hot=True)
                self.send_heartbeat({"audio_status":"failed","inference_status":"failed","hardware":bad})
                for component in ("capture","inference","power","thermal"): report(component)
                self.send_heartbeat({"audio_status":"healthy","inference_status":"healthy","hardware":self.hardware(history=True)})
                for component in ("capture","inference","power","thermal"): report(component,True)
                self.store.tick()
                check("Listening restored","available",self.store.station_status()["listening"])
                check("Unresolved simulated faults",0,len(self.store.query("SELECT id FROM issues WHERE resolved=0")))
                check("Current power health","healthy",self.store.station_status()["hardware"]["power_status"])
                check("Historical evidence retained",["under_voltage"],self.store.station_status()["hardware"]["historical_flags"])
        except Exception as exc:
            run["checks"].append({"name":"Scenario execution","expected":"completed","actual":redact(str(exc),self.config.secrets.values()),"passed":False})
        finally:
            run["finished_at"]=iso()
            run["status"]="passed" if run["checks"] and all(c["passed"] for c in run["checks"]) else "failed"
            run["snapshot"]={"status":self.store.public_status(),"birds":self.store.summary("all"),"local_inbox":self.store.meta("simulation_mail",[])}
            run["diagnostics"]=self.store.diagnostics()
            run=redact(run,self.config.secrets.values())
            try:
                private_json(self.runs_folder/(str(time.time_ns())+"-"+run["id"]+".json"),run)
                for old in sorted(self.runs_folder.glob("*.json"))[:-100]: old.unlink()
            finally:
                self.scenario_lock.release()
        return run

    def report_bundle(self, run_id=None, notes=""):
        if not isinstance(notes,str) or len(notes)>6000: raise ValueError("Keep visual notes under 6000 characters.")
        if run_id is not None and (not isinstance(run_id,str) or len(run_id)!=32 or any(c not in "0123456789abcdef" for c in run_id)):
            raise ValueError("Invalid simulation run identifier.")
        runs=self.saved_runs()
        if run_id:
            runs=[r for r in runs if r["id"]==run_id]
            if not runs: raise ValueError("That run is no longer retained.")
        return redact({"application":"Songsketch", "version":__version__,"simulation":True,"generated_at":iso(),
                       "limitations":LIMITATIONS,"manual_visual_notes":notes,"manual_visual_review":"User notes only; not an automatic pass.",
                       "runs":runs,"diagnostics":self.store.diagnostics(),"external_messages_sent":False}, self.config.secrets.values())


class SimulationHandler(Handler):
    def authorized(self, station=False):
        if station: return super().authorized(station=True)
        if not self.local_admin(): return False
        auth=self.headers.get("Authorization", "")
        if auth.startswith("Bearer ") and secrets.compare_digest(auth[7:],self.app.config.secrets["admin_token"]): return True
        cookies=SimpleCookie()
        try: cookies.load(self.headers.get("Cookie",""))
        except Exception: return False
        sid=cookies.get(COOKIE)
        if not sid: return False
        with self.app.auth_lock: return self.app.sessions.get(sid.value,0)>time.time()

    def start_session(self):
        sid=secrets.token_urlsafe(32)
        with self.app.auth_lock:
            self.app.sessions={k:v for k,v in self.app.sessions.items() if v>time.time()}
            self.app.sessions[sid]=time.time()+43200
        self.send({"ok":True,"simulation":True},extra={"Set-Cookie":COOKIE+"="+sid+"; HttpOnly; SameSite=Strict; Path=/api/; Max-Age=43200"})

    def do_GET(self):
        try:
            parsed=urlparse(self.path); path=unquote(parsed.path); query=parse_qs(parsed.query)
            if path=="/health":
                return self.send({"ok":True,"application":"songsketch","mode":MODE,"simulation":True,"data_id":self.app.marker["id"],"version":__version__,"candidate_artwork":bool(self.app.candidate_catalogue),"catalogue_sha256":self.app.catalogue_sha256})
            if path in ("/simulation","/simulation/"): return self.file(ROOT/"static/qa.html")
            if path.startswith("/api/simulation/"):
                self.require_admin()
                if path=="/api/simulation/status": return self.send(self.app.state())
                if path=="/api/simulation/report":
                    return self.send(self.app.report_bundle(query.get("run_id",[None])[0]),extra={"Content-Disposition":"attachment; filename=songsketch-simulation-report.json"})
                return self.send({"error":"Not found"},404)
            if path=="/api/admin/export":
                self.require_admin()
                return self.send({"error":"Simulation data is not a garden migration. Download the simulation report instead."},403)
            return super().do_GET()
        except PermissionError as exc: self.send({"error":str(exc)},401)
        except (ValueError,TypeError) as exc: self.send({"error":str(exc)},400)

    def do_POST(self):
        path=urlparse(self.path).path
        allowed={"/api/session","/api/setup/session","/api/admin/setup-ticket","/api/admin/test-detection","/api/admin/diagnostics",
                 "/api/ingest/detections","/api/ingest/heartbeat","/api/ingest/reports","/detections","/heartbeat","/debug-reports"}
        try:
            self.check_origin()
            if path in ("/api/simulation/run","/api/simulation/report","/api/admin/logout"):
                self.require_admin(); data=self.body()
                if path=="/api/simulation/run":
                    if set(data)-{"scenario","seed"}: raise ValueError("Supply a scenario and optional seed only.")
                    return self.send({"run":self.app.run_scenario(data.get("scenario"),data.get("seed",20261022)),"simulation":True})
                if path=="/api/simulation/report":
                    if set(data)-{"run_id","notes"}: raise ValueError("Supply run_id and notes only.")
                    report=self.app.report_bundle(data.get("run_id"),data.get("notes",""))
                    private_json(self.app.config.directory/"latest-simulation-report.json",report)
                    return self.send(report,extra={"Content-Disposition":"attachment; filename=songsketch-simulation-report.json"})
                cookies=SimpleCookie(); cookies.load(self.headers.get("Cookie","")); sid=cookies.get(COOKIE)
                if sid:
                    with self.app.auth_lock: self.app.sessions.pop(sid.value,None)
                return self.send({"ok":True},extra={"Set-Cookie":COOKIE+"=; HttpOnly; SameSite=Strict; Path=/api/; Max-Age=0"})
            if path not in allowed:
                self.require_admin()
                self.close_connection=True
                return self.send({"error":BLOCKED,"simulation":True},403)
            return super().do_POST()
        except PermissionError as exc: self.send({"error":str(exc)},401)
        except (ValueError,TypeError) as exc: self.send({"error":str(exc)},400)

    def file(self, file):
        # Even a painting/dashboard opened in a separate tab remains visibly synthetic.
        if file in (ROOT/"static/display.html",ROOT/"static/dashboard.html"):
            label="SIMULATED GARDEN · review candidates · no live audio" if self.app.candidate_catalogue else "SIMULATED GARDEN · no live audio"
            badge='<div style="position:fixed;right:10px;top:10px;z-index:99999;background:#203e42;color:white;padding:5px 9px;border-radius:4px;font:12px system-ui;pointer-events:none">'+label+'</div>'
            content=file.read_text().replace("</body>",badge+"</body>").encode()
            self.headers_out(200,"text/html; charset=utf-8",len(content))
            if self.command!="HEAD": self.wfile.write(content)
            return
        return super().file(file)


class SimulationServer(Server):
    def __init__(self,address,app):
        if address[0]!="127.0.0.1": raise ValueError("The simulated garden binds to 127.0.0.1 only.")
        self.app=app
        ThreadingHTTPServer.__init__(self,address,SimulationHandler)
        app.port=self.server_address[1]


def launch_url(app,port):
    ticket=secrets.token_urlsafe(32)
    with app.auth_lock: app.setup_tickets[ticket]=time.time()+120
    return "http://127.0.0.1:%s/simulation#ticket=%s" % (port,ticket)


def main(argv=None):
    parser=argparse.ArgumentParser(description="Open an isolated synthetic Songsketch garden. No Pi, email, paid AI or SSH.")
    parser.add_argument("--data-dir",type=Path,default=simulation_directory())
    parser.add_argument("--port",type=int,default=8766)
    parser.add_argument("--no-open",action="store_true")
    parser.add_argument("--candidate-catalogue",type=Path,help="Explicitly opt into a local candidate animation catalogue; does not change live playback.")
    parser.add_argument("--review-animations",action="store_true",help="Explicitly preview the bundled 45-bird review catalogue; live playback is unchanged.")
    args=parser.parse_args(argv)
    if not 1024<=args.port<=65535: parser.error("Choose a port from 1024 to 65535.")
    if args.review_animations:
        if args.candidate_catalogue: parser.error("Use --review-animations or --candidate-catalogue, not both.")
        args.candidate_catalogue=ROOT/"artwork/review-catalogue.json"
    app=None; server=None
    try:
        directory,marker=prepare_directory(args.data_dir)
        # Reopening the launcher reuses only this marked simulator, never a real server.
        conn=http.client.HTTPConnection("127.0.0.1",args.port,timeout=1)
        try:
            conn.request("GET","/health"); response=conn.getresponse(); existing=json.loads(response.read())
        except (OSError,ValueError,http.client.HTTPException): existing=None
        finally: conn.close()
        if existing:
            if not isinstance(existing,dict) or existing.get("mode")!=MODE or existing.get("data_id")!=marker["id"]:
                raise ValueError("That port belongs to another server. Choose a different simulation port.")
            expected_catalogue=args.candidate_catalogue or ROOT/"artwork/catalogue.json"
            expected_hash=hashlib.sha256(expected_catalogue.read_bytes()).hexdigest()
            if existing.get("candidate_artwork")!=bool(args.candidate_catalogue) or existing.get("catalogue_sha256")!=expected_hash:
                raise ValueError("This simulator is using a different catalogue. Stop its Terminal process or choose a separate simulation folder and port for this review.")
            config=SimulationConfig(directory)
            conn=http.client.HTTPConnection("127.0.0.1",args.port,timeout=5)
            try:
                conn.request("POST","/api/admin/setup-ticket",body="{}",headers={"Content-Type":"application/json","Authorization":"Bearer "+config.secrets["admin_token"]})
                response=conn.getresponse(); result=json.loads(response.read())
                if response.status!=200: raise ValueError("Could not reopen the existing simulator session.")
            finally: conn.close()
            url="http://127.0.0.1:%s/simulation#ticket=%s"%(args.port,result["ticket"])
            if not args.no_open: webbrowser.open(url)
            print("The existing simulated garden is running at http://127.0.0.1:%s/simulation"%args.port)
            return 0
        app=SimulationApp(directory,args.candidate_catalogue)
        server=SimulationServer(("127.0.0.1",args.port),app)
        app.start_ticks()
        if not args.no_open: webbrowser.open(launch_url(app,args.port))
        print("Simulated garden: http://127.0.0.1:%s/simulation"%args.port)
        print("Synthetic data only. No Pi, external email, paid AI or SSH. Keep this window open; Control-C stops the simulator.")
        server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt: pass
    except (OSError,ValueError,RuntimeError) as exc:
        print("The simulated garden could not start: "+str(exc),file=sys.stderr)
        return 1
    finally:
        if server: server.server_close()
        if app: app.close()
    return 0


if __name__=="__main__": raise SystemExit(main())
