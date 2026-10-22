#!/usr/bin/env python3
"""Headless, bounded commissioning for the pinned Songsketch garden Pi.

Input: --provision - (JSON stdin), or a private JSON file. No secrets in argv.
Output: SONGSKETCH_PROGRESS JSON lines, then one final JSON result.
--diagnose is read-only and never restarts services or changes configuration.

Pinned source contracts (20261014): internal/api/v2/settings.go,
audio/audio_devices.go, app/app.go, internal/api/middleware/csrf.go,
internal/conf/config.go and frontend/src/lib/utils/audioDevices.ts.
This is source-verified software, not evidence of a physical Pi test.
"""
import argparse
import copy
import datetime as dt
import fcntl
import http.cookiejar
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("commission_relay", ROOT / "pi/relay.py")
relay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(relay)
STATE = Path("/var/lib/songsketch-pi/commission-status.json")
LOCK = Path("/run/songsketch-commission.lock")
CONFIG = Path("/etc/songsketch-pi/config.json")
IMAGE_LOCK = Path("/etc/songsketch-pi/birdnet-image.lock")
BASE = "http://127.0.0.1:8080"
RELEASE = "20261014"


class CommissionError(Exception):
    def __init__(self, code, message, actions=None, human=None, status="needs_input"):
        super().__init__(message)
        self.code, self.actions, self.human, self.status = code, actions or [], human, status


def clean(value, limit=200):
    if not isinstance(value, str): return ""
    return "".join(c for c in value if c.isprintable())[:limit]


def private_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=".commission-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as out:
            json.dump(data, out, allow_nan=False)
            out.write("\n"); out.flush(); os.fsync(out.fileno())
        os.replace(name, path)
        path.chmod(0o600)
    finally:
        if os.path.exists(name): os.unlink(name)


def validate_provision(data):
    if not isinstance(data, dict): raise ValueError("Expected a JSON object")
    allowed = {"schema_version", "server_url", "station_id", "token", "latitude", "longitude",
               "timezone", "capture_device", "use_existing_birdnet"}
    if set(data) - allowed: raise ValueError("Unexpected provisioning fields")
    if type(data.get("schema_version", 1)) is not int or data.get("schema_version", 1) != 1:
        raise ValueError("Unsupported provisioning schema")
    out = dict(data)
    out["server_url"] = relay.validate_url(data.get("server_url", ""))
    if urllib.parse.urlsplit(out["server_url"]).hostname in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Use the server LAN address, not Pi loopback")
    out["station_id"] = data.get("station_id", "garden")
    if not isinstance(out["station_id"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", out["station_id"]):
        raise ValueError("Invalid station identity")
    token = data.get("token")
    if not isinstance(token, str) or not 24 <= len(token) <= 512 or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise ValueError("Invalid station credential")
    for key, bound in (("latitude", 90), ("longitude", 180)):
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not -bound <= value <= bound:
            raise ValueError("Provide valid property coordinates")
    if data["latitude"] == 0 and data["longitude"] == 0:
        raise ValueError("Provide the actual garden location, not the default 0,0")
    zone = data.get("timezone", "Europe/London")
    if not isinstance(zone, str) or not re.fullmatch(r"[A-Za-z0-9_+/-]{1,80}", zone):
        raise ValueError("Invalid timezone")
    ZoneInfo(zone)
    out["timezone"] = zone
    existing = data.get("use_existing_birdnet", False)
    if not isinstance(existing, bool): raise ValueError("use_existing_birdnet must be boolean")
    out["use_existing_birdnet"] = existing
    selected = data.get("capture_device", "")
    if not isinstance(selected, str) or len(selected) > 240 or any(ord(c) < 32 for c in selected):
        raise ValueError("Invalid capture device choice")
    out["capture_device"] = selected
    return out


def capture_choices(devices):
    if not isinstance(devices, list):
        raise CommissionError("device_contract_changed", "BirdNET returned an unfamiliar capture-device list.", ["check_pinned_release"], status="failed")
    result, seen = [], set()
    for item in devices:
        if not isinstance(item, dict): continue
        ident = item.get("stableId") or item.get("id")
        name = item.get("name")
        if not isinstance(ident, str) or not ident or len(ident) > 240 or any(ord(c) < 32 for c in ident): continue
        if not isinstance(name, str) or not name: continue
        if ident in seen: continue
        seen.add(ident)
        # Enumeration is capture-only, but virtual/default/loopback inputs may
        # still be present. They are never silently selected for a garden mic.
        sensible = not re.search(r"\b(hdmi|monitor|loopback|default|null|pulse|pipewire)\b", name + " " + ident, re.I)
        result.append({"id": ident, "name": clean(name), "legacy_id": clean(item.get("id"), 240),
                       "bus_path": clean(item.get("busPath")), "recommended": sensible})
    return result


def select_capture(choices, requested=""):
    if requested:
        matches = [c for c in choices if requested in (c["id"], c["legacy_id"])]
        if len(matches) == 1: return matches[0]
        raise CommissionError("capture_choice_changed", "The selected capture input is no longer uniquely available.", ["refresh_capture_sources", "choose_capture_device"], "Choose a currently connected microphone input.")
    candidates = [c for c in choices if c["recommended"]]
    if len(candidates) == 1: return candidates[0]
    if not choices:
        raise CommissionError("capture_missing", "BirdNET cannot see a capture input.", ["check_usb_microphone", "check_microphone_power", "retry_commissioning"], "Connect the microphone and compatible USB audio input.")
    raise CommissionError("capture_choice_required", "Several or ambiguous capture inputs need a choice.", ["choose_capture_device"], "Choose the USB input connected to the garden microphone.")


def matches(actual, expected):
    if isinstance(expected, dict):
        # Go omits cleared deprecated fields from its JSON response. Absence
        # is equivalent to empty only for these documented string fields.
        return isinstance(actual, dict) and all(
            (k not in actual and k in ("source", "model") and v == "") or
            (k in actual and matches(actual[k], v)) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(matches(a, e) for a, e in zip(actual, expected))
    return actual == expected


def settings_plan(settings, provision, selected):
    if not isinstance(settings, dict) or not all(isinstance(settings.get(k), dict) for k in ("birdnet", "models", "realtime", "output")):
        raise CommissionError("settings_contract_changed", "BirdNET settings do not match the pinned release.", ["check_pinned_release"], status="failed")
    realtime, bird = settings["realtime"], settings["birdnet"]
    audio = realtime.get("audio", {})
    sources = audio.get("sources", [])
    streams = realtime.get("rtsp", {}).get("streams", [])
    models = settings["models"].get("enabled", [])
    if (not isinstance(sources, list) or len(sources) > 1 or any(s.get("enabled", True) for s in streams)
            or any(m != "birdnet" for m in models) or bird.get("modelPath") or bird.get("labelPath")
            or settings["output"].get("mysql", {}).get("enabled")):
        raise CommissionError("existing_configuration_complex", "This installation has extra sources, models or storage that the MVP will preserve.",
                              ["review_existing_birdnet_configuration"], "Review this existing BirdNET setup before changing it.")
    source = copy.deepcopy(sources[0]) if sources else {"name": "Garden microphone", "gain": 0}
    if source.get("model") not in (None, "", "birdnet") or (source.get("models") and any(m != "birdnet" for m in source["models"])):
        raise CommissionError("existing_configuration_complex", "The capture input already uses additional models.", ["review_existing_birdnet_configuration"])
    source.update(device=selected["id"], models=["birdnet"], model="", sampleRate=48000)
    source["quietHours"] = {**source.get("quietHours", {}), "enabled": False, "mode": "fixed",
                            "startTime": "22:00", "endTime": "06:00"}
    return [
        ("birdnet", {"latitude": provision["latitude"], "longitude": provision["longitude"],
                     "locationConfigured": True, "locale": "en-uk", "threshold": .7}),
        ("models", {"enabled": ["birdnet"]}),
        ("realtime", {"daylightFilter": {"enabled": False}}),
        ("output", {"sqlite": {"enabled": True}}),
        ("audio", {"sources": [source], "source": "", "quietHours": {"enabled": False},
                   "export": {"enabled": False, "retention": {"policy": "usage", "maxUsage": "75%", "maxAge": "14d",
                                                             "minClips": 1, "checkInterval": 15}}}),
    ]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None


class BirdNET:
    def __init__(self, base=BASE):
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = ""

    def request(self, path, method="GET", body=None):
        headers = {"Accept": "application/json"}
        if body is not None: headers["Content-Type"] = "application/json"
        if method != "GET":
            if not self.csrf: raise CommissionError("csrf_missing", "BirdNET did not provide a safe configuration session.", ["check_pinned_release"], status="failed")
            headers["X-CSRF-Token"] = self.csrf
            headers["Origin"] = self.base
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=8) as response:
                raw = response.read(2_000_001)
            if len(raw) > 2_000_000: raise ValueError("oversize response")
            return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            status_code = exc.code
            exc.close()
            if status_code in (401, 403):
                raise CommissionError("birdnet_access_required", "BirdNET did not authorize this local request. Existing authentication was preserved.",
                                      ["review_birdnet_access"], "Provide an approved unattended access arrangement for this BirdNET installation.") from None
            raise CommissionError("birdnet_http_error", "BirdNET rejected a commissioning request.", ["run_diagnostics", "check_pinned_release"], status="failed") from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise CommissionError("birdnet_unreachable", "BirdNET is not answering with its expected local API.", ["run_diagnostics", "check_birdnet_service"], status="failed") from None

    def bootstrap(self):
        result = self.request("/api/v2/app/config")
        if not isinstance(result, dict): raise CommissionError("app_contract_changed", "BirdNET startup response is unfamiliar.", ["check_pinned_release"], status="failed")
        self.csrf = result.get("csrfToken", "")
        if result.get("version") != RELEASE:
            raise CommissionError("birdnet_version_mismatch", "This BirdNET version differs from tested release 20261014.", ["review_birdnet_version"], "Use the tested release or have its API compatibility reviewed.")
        if result.get("security", {}).get("enabled"):
            raise CommissionError("birdnet_access_required", "Existing BirdNET authentication is enabled and will remain unchanged.", ["review_birdnet_access"], "Provide an approved unattended access arrangement for BirdNET.")
        return result


class System:
    def run(self, args, timeout=30, env=None):
        try:
            # Isolate the installer and its children so a timeout cannot leave
            # apt/docker subprocesses behind while the commissioning lock ends.
            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                       env=env, start_new_session=True)
            try:
                output, _ = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                try: process.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    process.communicate()
                return subprocess.CompletedProcess(args, 124, "")
            return subprocess.CompletedProcess(args, process.returncode, output)
        except OSError:
            return subprocess.CompletedProcess(args, 124, "")

    def _owned_container(self):
        """Verify the installation, image and configured publish target together.

        A label alone never authorizes modifying the process answering the API.
        Docker's saved image digest and resolved image ID must both match, and
        the sole 8080 publication must be the helper's fixed loopback target.
        """
        r = self.run(["docker", "inspect", "songsketch-birdnet"])
        if r.returncode: return None
        try:
            values = json.loads(r.stdout)
            if not isinstance(values, list) or len(values) != 1: return None
            container = values[0]
            labels = container["Config"].get("Labels") or {}
            if labels.get("org.songsketch.managed") != "true" or labels.get("org.songsketch.birdnet-release") != RELEASE:
                return None
            pinned = IMAGE_LOCK.read_text().strip()
            if not re.fullmatch(r"ghcr\.io/tphakala/birdnet-go@sha256:[a-f0-9]{64}", pinned): return None
            if container["Config"]["Image"] != pinned: return None
            image = self.run(["docker", "image", "inspect", "--format", "{{.Id}}", pinned])
            if image.returncode or not re.fullmatch(r"sha256:[a-f0-9]{64}", image.stdout.strip()): return None
            if container["Image"] != image.stdout.strip(): return None
            target = [{"HostIp": "127.0.0.1", "HostPort": "8080"}]
            host = container["HostConfig"]
            if host.get("NetworkMode") not in ("default", "bridge"): return None
            if host.get("PortBindings", {}).get("8080/tcp") != target: return None
            return container
        except (OSError, ValueError, KeyError, TypeError): return None

    def owned(self):
        container = self._owned_container()
        if not container: return False
        state = container.get("State", {})
        # Check actual live publication as well as saved HostConfig. A stopped
        # labelled container cannot lend ownership to a different API on 8080.
        return (state.get("Running") is True and type(state.get("Pid")) is int and state["Pid"] > 0
                and container.get("NetworkSettings", {}).get("Ports", {}).get("8080/tcp") ==
                [{"HostIp": "127.0.0.1", "HostPort": "8080"}])

    def can_restart(self):
        container = self._owned_container()
        if not container: return False
        if container.get("State", {}).get("Running") is True: return self.owned()
        # A stopped owned container may recover only while the intended API
        # port is vacant. Starting it must not displace another local service.
        try:
            with socket.create_connection(("127.0.0.1", 8080), timeout=2): return False
        except ConnectionRefusedError: return True
        except OSError: return False

    def timezone(self):
        r = self.run(["docker", "inspect", "--format", "{{json .Config.Env}}", "songsketch-birdnet"])
        try:
            return next((s[3:] for s in json.loads(r.stdout) if s.startswith("TZ=")), "")
        except (ValueError, TypeError): return ""

    def preflight(self, provision):
        args = ["bash", str(ROOT / "scripts/install-pi.sh"), "--check"]
        if provision["use_existing_birdnet"]: args.append("--skip-birdnet")
        if self.run(args).returncode:
            raise CommissionError("unsupported_platform", "The Pi does not pass the supported 64-bit platform checks.", ["verify_pi_os"], "Use supported 64-bit Raspberry Pi OS on the Pi kit.")
        if not provision["use_existing_birdnet"] and not any(p.is_char_device() for p in Path("/dev/snd").glob("pcm*C*c")):
            raise CommissionError("capture_missing", "No physical ALSA capture device is present.", ["connect_usb_audio", "retry_commissioning"], "Connect the microphone and its USB audio interface.")
        if shutil.disk_usage("/var/lib").free < 2 * 1024**3:
            raise CommissionError("low_disk", "Less than 2 GB is free for installation and BirdNET startup.", ["review_disk_space"], "Free space or use suitable storage; existing data has not been erased.")
        if self.run(["timedatectl", "set-timezone", provision["timezone"]]).returncode:
            raise CommissionError("timezone_failed", "The Pi timezone could not be set.", ["check_time_service"], status="failed")
        if self.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"]).stdout.strip() != "yes":
            self.run(["timedatectl", "set-ntp", "true"])
            for _ in range(6):
                time.sleep(2)
                if self.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"]).stdout.strip() == "yes": break
            else:
                raise CommissionError("clock_unsynchronized", "The Pi clock has not synchronized; detection timestamps would be unreliable.", ["check_internet_time", "retry_commissioning"], "Check the Pi's internet connection and time service.")

    def install(self, provision):
        fd, name = tempfile.mkstemp(prefix="songsketch-provision-", suffix=".json")
        try:
            with os.fdopen(fd, "w") as out: json.dump(provision, out)
            args = ["bash", str(ROOT / "scripts/install-pi.sh"), "--provision", name]
            if provision["use_existing_birdnet"]: args.append("--skip-birdnet")
            env = dict(os.environ, SONGSKETCH_DEFER_RELAY_START="1")
            result = self.run(args, timeout=1200, env=env)
            if result.returncode:
                raise CommissionError("installer_failed", "Installation did not complete. Existing history has not been erased.", ["run_diagnostics", "check_package_network", "check_disk_space"], status="failed")
        finally:
            os.unlink(name)

    def backup_config(self):
        source = Path("/var/lib/songsketch-birdnet/config/config.yaml")
        if source.is_file():
            folder = STATE.parent / "commission-backups"
            folder.mkdir(exist_ok=True, mode=0o700)
            target = folder / (str(time.time_ns()) + ".yaml")
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as out: out.write(source.read_bytes())
            for old in sorted(folder.glob("*.yaml"))[:-3]: old.unlink()

    def restart_birdnet(self):
        if not self.can_restart(): return False
        return self.run(["docker", "restart", "songsketch-birdnet"], timeout=45).returncode == 0

    def start_relay(self):
        return self.run(["systemctl", "restart", "songsketch-pi.service"], timeout=45).returncode == 0

    def relay_evidence(self, provision):
        try:
            info = relay.request_json("http://127.0.0.1:8081/diagnostics", provision["token"])
            return {"audio_status": info.get("audio_status"), "inference_status": info.get("inference_status"),
                    "last_poll": info.get("last_poll"), "last_health": info.get("last_health"),
                    "pending": info.get("queue", {}).get("pending")}
        except Exception: return {}

    def diagnostics(self):
        """Fixed read-only checks: no shell, logs, environment or credentials."""
        info = {"capture_device_present": any(p.is_char_device() for p in Path("/dev/snd").glob("pcm*C*c"))}
        try: info["free_bytes"] = shutil.disk_usage("/var/lib").free
        except OSError: pass
        info["clock_synchronized"] = self.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"]).stdout.strip() == "yes"
        info["timezone"] = clean(self.run(["timedatectl", "show", "-p", "Timezone", "--value"]).stdout.strip(), 80)
        container = self.run(["docker", "inspect", "--format", "{{json .State}}", "songsketch-birdnet"])
        try:
            state = json.loads(container.stdout)
            info["container"] = {k: state[k] for k in ("Status", "Running", "Restarting", "OOMKilled", "ExitCode") if k in state}
        except (ValueError, TypeError): info["container"] = {"Status": "unavailable"}
        return info


class Commissioner:
    def __init__(self, provision, system=None, api=None, state_path=STATE, emit=None, sleep=time.sleep, attempts=12):
        self.provision = validate_provision(provision)
        self.system, self.api = system or System(), api or BirdNET()
        self.state_path, self.emit, self.sleep, self.attempts = Path(state_path), emit, sleep, attempts
        self.restarted = False
        self.result = {"schema_version": 1, "operation_id": uuid.uuid4().hex, "status": "running", "stage": "starting",
                       "message": "Starting Pi commissioning", "progress": 0, "checks": {}, "next_actions": [], "human_action": None,
                       "capture_sources": [], "physical_audio_quality_verified": False, "real_bird_verified": False}

    def progress(self, stage, message, **extra):
        # Milestone completion, not a claim about download byte progress.
        milestones = {"preflight": 5, "installing": 20, "connecting": 45,
                      "configuring": 60, "verifying": 75, "starting_relay": 90, "complete": 100}
        self.result["progress"] = max(self.result["progress"], milestones.get(stage, 0))
        self.result.update(stage=stage, message=message, updated_at=relay.iso_now(), **extra)
        private_json(self.state_path, self.result)
        if self.emit:
            try: self.emit(copy.deepcopy(self.result))
            except BrokenPipeError: self.emit = None  # Finish safely if the SSH observer disappears.

    def wait_api(self):
        last = None
        for _ in range(self.attempts):
            try: return self.api.bootstrap()
            except CommissionError as exc:
                last = exc
                if exc.code != "birdnet_unreachable": raise
                self.sleep(5)
        raise last

    def restart_once(self):
        if self.restarted or not self.system.can_restart(): return False
        self.restarted = True
        self.progress("recovering", "Restarting the owned BirdNET service once, then checking again.")
        return self.system.restart_birdnet()

    def health(self):
        for _ in range(self.attempts):
            audio = self.api.request("/api/v2/health/audio")
            inference = self.api.request("/api/v2/system/inference")
            statuses = relay.interpret_health(audio, inference, {"model_id": "BirdNET_V2.4"})
            self.result["checks"].update(audio=statuses[0], inference=statuses[1])
            if statuses == ("healthy", "healthy"):
                # Require subsequent evidence of progressing analysis, not just
                # a loaded model or a single recent bird detection.
                first = next((m for m in inference.get("models", []) if m.get("id") == "BirdNET_V2.4"), {})
                before = first.get("health", {}).get("lastSuccessAtUnix", 0)
                self.sleep(5)
                second = self.api.request("/api/v2/system/inference")
                after = next((m for m in second.get("models", []) if m.get("id") == "BirdNET_V2.4"), {}).get("health", {}).get("lastSuccessAtUnix", 0)
                if after > before and relay.interpret_health(audio, second, {"model_id": "BirdNET_V2.4"}) == ("healthy", "healthy"):
                    self.result["checks"]["inference_advancing"] = True
                    return True
            self.sleep(5)
        return False

    def verify_settings(self, plan, after_restart=False):
        # An in-memory PATCH readback does not prove that the saved settings
        # survive a restart. Invalidate earlier evidence before each check,
        # and report section names only, never locations or device values.
        self.result["checks"]["settings_verified"] = False
        if after_restart:
            self.result["checks"]["settings_verified_after_restart"] = False
        mismatches = [section for section, patch in plan
                      if not matches(self.api.request("/api/v2/settings/" + section), patch)]
        if mismatches:
            self.result["checks"]["settings_requiring_review"] = mismatches
            if after_restart:
                raise CommissionError("settings_not_persistent", "BirdNET settings changed after restart; commissioning stopped before starting the relay.",
                                      ["run_diagnostics", "review_birdnet_settings_persistence"], status="failed")
            raise CommissionError("settings_not_verified", "Saved BirdNET settings differ from the commissioning plan.",
                                  ["run_diagnostics", "review_birdnet_settings"], status="failed")
        self.result["checks"]["settings_verified"] = True
        if after_restart:
            self.result["checks"]["settings_verified_after_restart"] = True

    def verify_health(self, plan):
        try:
            healthy = self.health()
        except CommissionError as exc:
            if exc.code != "birdnet_unreachable": raise
            healthy = False
        if not healthy and self.restart_once():
            self.wait_api()
            self.verify_settings(plan, after_restart=True)
            healthy = self.health()
        return healthy

    def owned_api_write(self, path, method, body):
        # Recheck immediately before each mutation; the container may have
        # stopped or its publish target may have changed since discovery.
        if not self.system.owned():
            raise CommissionError("birdnet_ownership_unverified", "BirdNET's verified container ownership changed. The requested API change was not sent.",
                                  ["run_diagnostics", "review_birdnet_installation"], "Review the container image and port binding before continuing.")
        return self.api.request(path, method, body)

    def execute(self):
        try:
            self.progress("preflight", "Checking platform, capture hardware, space and clock.")
            self.system.preflight(self.provision)
            self.result["checks"]["platform_clock_storage"] = True
            self.progress("installing", "Installing the pinned software and preserving existing data. Downloads can take several minutes.")
            self.system.install(self.provision)
            self.result["checks"]["software_installed"] = True
            self.result["checks"]["relay_paused_until_ready"] = True
            self.progress("connecting", "Waiting for BirdNET's local configuration API.")
            try: self.wait_api()
            except CommissionError as exc:
                if exc.code != "birdnet_unreachable" or not self.restart_once(): raise
                self.wait_api()
            self.result["checks"]["birdnet_release"] = RELEASE
            owned = self.system.owned()
            if not owned and not self.provision["use_existing_birdnet"]:
                raise CommissionError("birdnet_ownership_unverified", "The API cannot be tied to the pinned Songsketch container and its loopback port. No settings were changed.",
                                      ["run_diagnostics", "review_birdnet_installation"], "Review the container image and port binding before commissioning continues.")
            if owned and self.system.timezone() != self.provision["timezone"]:
                raise CommissionError("container_timezone_mismatch", "The existing container uses a different timezone; it was not replaced.", ["review_container_timezone"], "Have the existing container timezone reconciled without deleting its data.")
            settings = self.api.request("/api/v2/settings")
            choices = capture_choices(self.api.request("/api/v2/system/audio/devices"))
            self.result["capture_sources"] = choices
            selected = select_capture(choices, self.provision["capture_device"])
            self.result["checks"]["selected_capture"] = selected["id"]
            plan = settings_plan(settings, self.provision, selected)
            if not owned:
                # Existing installation can be connected only when it already
                # satisfies the contract; no unowned settings writes/restarts.
                mismatches = [section for section, patch in plan if not matches(self.api.request("/api/v2/settings/" + section), patch)]
                if mismatches:
                    self.result["checks"]["settings_requiring_review"] = mismatches
                    raise CommissionError("unmanaged_configuration", "Existing BirdNET settings need review; the helper has not changed them.", ["review_existing_birdnet_configuration"], "Approve and configure the existing installation's required settings separately.")
            else:
                self.system.backup_config()
                self.progress("configuring", "Applying garden location, one capture input, BirdNET v2.4, owl coverage and durable history.")
                restart = False
                for section, patch in plan:
                    if matches(self.api.request("/api/v2/settings/" + section), patch): continue
                    response = self.owned_api_write("/api/v2/settings/" + section, "PATCH", patch)
                    if not isinstance(response, dict) or response.get("skippedFields"):
                        raise CommissionError("settings_rejected", "BirdNET did not accept every requested setting.", ["run_diagnostics", "review_birdnet_settings"], status="failed")
                    restart = restart or response.get("restart_required", False)
                self.verify_settings(plan)
                if restart:
                    if not self.restart_once(): raise CommissionError("restart_required", "BirdNET requires a restart that could not be completed safely.", ["run_diagnostics"], status="failed")
                    self.wait_api()
                    self.verify_settings(plan, after_restart=True)
            self.result["checks"]["settings_verified"] = True
            self.progress("verifying", "Checking live capture, advancing inference and stored-history access.")
            healthy = self.verify_health(plan)
            if not healthy:
                raise CommissionError("audio_pipeline_not_ready", "Capture or inference is not producing fresh successful windows.", ["run_diagnostics", "check_selected_capture", "check_microphone_power"],
                                      "Check the connected input and microphone power if audio health is failing; a quiet garden alone is not a fault.", status="failed")
            history = self.api.request("/api/v2/detections?numResults=1")
            if not isinstance(history, dict) or not isinstance(history.get("data"), list) or type(history.get("total")) is not int:
                raise CommissionError("history_contract_changed", "Stored-detection access does not match the tested contract.", ["check_database_output", "check_pinned_release"], status="failed")
            self.result["checks"].update(history_readable=True, stored_detection_count=history["total"])
            self.progress("starting_relay", "Starting buffered delivery and verifying the server accepts a current heartbeat.")
            if not self.system.start_relay(): raise CommissionError("relay_start_failed", "The relay service did not start.", ["run_diagnostics"], status="failed")
            self.result["checks"]["relay_paused_until_ready"] = False
            body = {"station_id": self.provision["station_id"], "audio_status": "healthy", "inference_status": "healthy",
                    "uptime_seconds": 0, "version": relay.VERSION}
            try:
                ack = relay.request_json(self.provision["server_url"] + "/api/ingest/heartbeat", self.provision["token"], body)
                if not isinstance(ack, dict) or ack.get("ok") is not True: raise ValueError("ack")
            except Exception:
                raise CommissionError("server_unreachable", "Recognition is ready, but the Songsketch server did not acknowledge the connection. The relay retains queued records.", ["check_server_running", "check_lan_address", "check_firewall", "run_diagnostics"], "Keep the server awake and reachable from the Pi.", status="failed") from None
            self.result["checks"]["server_heartbeat_acknowledged"] = True
            for _ in range(self.attempts):
                evidence = self.system.relay_evidence(self.provision)
                if evidence.get("last_poll") and evidence.get("audio_status") == "healthy" and evidence.get("inference_status") == "healthy": break
                self.sleep(5)
            else:
                raise CommissionError("relay_verification_pending", "BirdNET is ready, but the relay has not yet completed a healthy history scan.", ["run_diagnostics", "wait_for_history_scan"], status="failed")
            self.result["checks"].update(relay_scan_verified=True, relay_healthy=True)
            if owned:
                self.owned_api_write("/api/v2/app/wizard/dismiss", "POST", {})
            self.progress("complete", "Software commissioning passed: audio is flowing, inference is advancing, history is readable and the server is connected.",
                          status="complete", code="commissioned", next_actions=["confirm_microphone_placement", "observe_first_real_bird", "verify_reboot_recovery"],
                          human_action="Listen once to confirm microphone quality and placement; observe a real bird and verify reboot recovery.")
        except CommissionError as exc:
            self.progress(self.result["stage"], str(exc), status=exc.status, code=exc.code,
                          next_actions=exc.actions, human_action=exc.human)
        except Exception:
            self.progress(self.result["stage"], "Commissioning stopped after an unexpected local error; credentials and raw logs were withheld.",
                          status="failed", code="unexpected_error", next_actions=["run_diagnostics"], human_action=None)
        return self.result


def lock_active(path=LOCK):
    # Open existing only: diagnostics must not create a file.
    try: fd = os.open(path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError: return False
    try:
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: return True
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally: os.close(fd)


def diagnose(state_path=STATE, lock_path=LOCK, system=None, api=None):
    system, api = system or System(), api or BirdNET()
    out = {"schema_version": 1, "status": "diagnostic", "stage": "diagnostics", "operation_running": lock_active(lock_path),
           "checks": {}, "next_actions": [], "human_action": None, "capture_sources": []}
    try:
        previous = json.loads(Path(state_path).read_text())
        # Only fields generated by this helper, never raw config/error logs.
        out["commissioning"] = {k: previous[k] for k in ("operation_id", "status", "stage", "code", "message", "updated_at", "next_actions", "human_action") if k in previous}
    except (OSError, ValueError, TypeError): pass
    out["checks"]["birdnet_owned"] = system.owned()
    out["checks"]["relay_service_active"] = system.run(["systemctl", "is-active", "--quiet", "songsketch-pi.service"]).returncode == 0
    out["checks"]["local_state"] = system.diagnostics()
    try:
        api.bootstrap()
        out["capture_sources"] = capture_choices(api.request("/api/v2/system/audio/devices"))
        audio = api.request("/api/v2/health/audio")
        inference = api.request("/api/v2/system/inference")
        a, i = relay.interpret_health(audio, inference, {"model_id": "BirdNET_V2.4"})
        history = api.request("/api/v2/detections?numResults=1")
        out["checks"].update(birdnet_release=RELEASE, audio=a, inference=i,
                             history_readable=isinstance(history, dict) and isinstance(history.get("data"), list) and type(history.get("total")) is int)
    except CommissionError as exc:
        out.update(code=exc.code, message=str(exc), next_actions=exc.actions, human_action=exc.human)
    if out["operation_running"]: out["next_actions"] = ["wait_for_current_operation"]
    return out


def main():
    parser = argparse.ArgumentParser()
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--provision", metavar="PRIVATE_JSON_OR_DASH")
    choice.add_argument("--diagnose", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    if os.geteuid() != 0:
        print(json.dumps({"status": "needs_input", "code": "sudo_required", "stage": "preflight", "message": "Run the helper through the approved sudo setup connection.", "next_actions": ["enable_approved_sudo_access"]}))
        return 2
    if args.diagnose:
        print(json.dumps(diagnose(), allow_nan=False)); return 0
    # Retain the lock and finish an in-flight installer when an SSH observer
    # disconnects. The caller must diagnose an uncertain operation before retry.
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    lock = None
    try:
        fd = os.open(LOCK, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        lock = os.fdopen(fd, "r+")
        try: fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise CommissionError("commissioning_in_progress", "Another Pi commissioning operation is still running.", ["wait_for_current_operation", "run_diagnostics"])
        if args.provision == "-": raw = sys.stdin.buffer.read(16385)
        else:
            fd = os.open(args.provision, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            with os.fdopen(fd, "rb") as source:
                info = os.fstat(source.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                    raise ValueError("Provisioning input must be an owner-only regular file")
                raw = source.read(16385)
        if len(raw) > 16384: raise ValueError("Provisioning input is too large")
        provision = validate_provision(json.loads(raw))
        commissioner = Commissioner(provision, emit=lambda value: print("SONGSKETCH_PROGRESS " + json.dumps(value), flush=True))
        result = commissioner.execute()
    except CommissionError as exc:
        result = {"status": exc.status, "stage": "preflight", "code": exc.code, "message": str(exc), "next_actions": exc.actions, "human_action": exc.human}
    except (ValueError, KeyError, OSError):
        result = {"status": "needs_input", "stage": "preflight", "code": "invalid_provision", "message": "Provisioning input or private local state could not be validated.", "next_actions": ["review_setup_inputs"]}
    finally:
        if lock: lock.close()
    print(json.dumps(result, allow_nan=False), flush=True)
    return 0 if result["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
