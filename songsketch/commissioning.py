"""Bounded SSH commissioning, with explicit trust and no command execution API.

The administrator HTTP boundary belongs to server.py. This module only accepts
the named actions below. No password is placed in arguments, saved state, logs,
or a regular file. Physical microphone/recognition checks remain Pi evidence.
"""
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from urllib.parse import urlsplit, urlunsplit
import uuid

from .config import ROOT, private_json


ACTIONS = ("probe", "trust", "install", "retry", "diagnose", "cancel")
ACTIVE = {"probing", "running", "cancelling"}
TERMINAL = {"completed", "failed", "cancelled", "interrupted", "needs_input"}
PACKAGE_FILES = (
    "scripts/commission-pi.py", "scripts/install-pi.sh",
    "scripts/install-linux-service.sh", "pi/relay.py", "pi/birdnet-contract.json",
)
HOST_RE = re.compile(r"(?=.{1,253}\Z)[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\Z")
USER_RE = re.compile(r"[a-z_][a-z0-9_-]{0,31}\Z")
KEY_TYPES = ("ssh-ed25519", "ecdsa-sha2-nistp256", "ssh-rsa")


def protocol_json(value):
    """Reject JavaScript-only NaN/Infinity before they reach saved/API state."""
    def reject_constant(_value):
        raise ValueError("Non-finite JSON number")
    def finite_float(number):
        parsed = float(number)
        if not math.isfinite(parsed):
            raise ValueError("JSON number overflows a finite float")
        return parsed
    return json.loads(value, parse_constant=reject_constant, parse_float=finite_float)


def utc_string(value=None):
    return datetime.fromtimestamp(time.time() if value is None else value,
                                  timezone.utc).isoformat().replace("+00:00", "Z")


def validate_hostname(value):
    if not isinstance(value, str) or not HOST_RE.fullmatch(value):
        raise ValueError("Enter a hostname or IPv4 address, without spaces or SSH options.")
    if any(not label or len(label) > 63 or label.startswith("-") or label.endswith("-")
           for label in value.split(".")):
        raise ValueError("Invalid hostname.")
    if re.fullmatch(r"[0-9.]+", value):
        try:
            ipaddress.IPv4Address(value)
        except ValueError:
            raise ValueError("Invalid IPv4 address.")
    return value.lower()


def validate_inputs(data):
    allowed = {"hostname", "username", "server_url", "latitude", "longitude", "use_existing_birdnet"}
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError("Unknown setup field. Passwords are accepted only when connecting after trust.")
    hostname = validate_hostname(data.get("hostname"))
    username = data.get("username")
    if not isinstance(username, str) or not USER_RE.fullmatch(username):
        raise ValueError("Enter the Pi's actual Linux account name.")
    raw_url = data.get("server_url")
    if not isinstance(raw_url, str) or len(raw_url) > 300 or any(c.isspace() for c in raw_url):
        raise ValueError("Enter the indoor server's LAN URL.")
    try:
        parsed = urlsplit(raw_url)
        host = validate_hostname(parsed.hostname)
        port = parsed.port
    except (ValueError, TypeError):
        raise ValueError("Enter a valid indoor server LAN URL.")
    if (parsed.scheme not in ("http", "https") or parsed.username is not None or
            parsed.password is not None or parsed.path not in ("", "/") or
            parsed.query or parsed.fragment or port == 0):
        raise ValueError("Use an http(s) server address without credentials, a path or a query.")
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("The Pi needs the server's LAN address, not localhost.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address and (address.is_loopback or address.is_unspecified or address.is_multicast):
        raise ValueError("The Pi needs a reachable server LAN address.")
    coordinates = {}
    for key, limit in (("latitude", 90), ("longitude", 180)):
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > limit:
            raise ValueError("Enter a valid garden " + key + ".")
        coordinates[key] = float(value)
    existing = data.get("use_existing_birdnet", False)
    if not isinstance(existing, bool):
        raise ValueError("use_existing_birdnet must be true or false.")
    authority = host + ((":" + str(port)) if port is not None else "")
    return {"hostname": hostname, "username": username,
            "server_url": urlunsplit((parsed.scheme, authority, "", "", "")),
            **coordinates, "use_existing_birdnet": existing}


def scan_key(output, hostname):
    """Choose one unambiguous strong advertised key; scanning is NOT trust."""
    keys = {kind: set() for kind in KEY_TYPES}
    for line in output.splitlines():
        if line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 3 or parts[0] not in (hostname, "[" + hostname + "]:22") or parts[1] not in keys:
            continue
        try:
            blob = base64.b64decode(parts[2], validate=True)
            length = int.from_bytes(blob[:4], "big")
            if not (16 <= len(blob) <= 16384) or blob[4:4 + length].decode("ascii") != parts[1]:
                continue
        except (ValueError, UnicodeError):
            continue
        keys[parts[1]].add(parts[2])
    for kind in KEY_TYPES:
        if len(keys[kind]) > 1:
            raise SetupError("ambiguous_host_key", "The address returned conflicting SSH identities.",
                             "Check the Pi address and network before trying again.", ["probe"])
        if keys[kind]:
            key = next(iter(keys[kind]))
            fingerprint = "SHA256:" + base64.b64encode(hashlib.sha256(base64.b64decode(key)).digest()).decode().rstrip("=")
            return {"hostname": hostname, "key_type": kind, "key": key, "fingerprint": fingerprint}
    raise SetupError("host_unreachable", "No usable SSH host key was received.",
                     "Check that the Pi is powered on, SSH is enabled and its address is correct.", ["probe"])


class SetupError(Exception):
    def __init__(self, code, message, human_action=None, next_actions=None):
        super().__init__(message)
        self.code, self.message = code, message
        self.human_action = human_action
        self.next_actions = next_actions or ["diagnose", "retry"]


class SetupCancelled(Exception):
    pass


@contextmanager
def password_channel(password):
    """A secret-free executable plus owner-only FIFO; password bytes stay in RAM.

    A FIFO is used because OpenSSH may close inherited descriptors. It has no
    regular-file content. The helper answers only a password prompt, never an
    identity confirmation or a private-key passphrase challenge.
    """
    if not password:
        yield {}
        return
    with tempfile.TemporaryDirectory(prefix="songsketch-askpass-") as name:
        folder = Path(name)
        os.chmod(folder, 0o700)
        fifo = folder / "answer"
        os.mkfifo(fifo, 0o600)
        helper = folder / "askpass"
        code = ("import os,sys\n"
                "if len(sys.argv)<2 or not sys.argv[1].strip().lower().endswith('password:'): sys.exit(1)\n"
                "with open(os.environ['SONGSKETCH_ASKPASS_FIFO'],'rb',buffering=0) as f: answer=f.read(4096)\n"
                "os.write(1,answer)\n")
        helper.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " -c " + shlex.quote(code) + ' "$@"\n')
        helper.chmod(0o700)
        done = threading.Event()

        def deliver():
            answer = (password + "\n").encode("utf-8")
            while not done.is_set():
                try:
                    fd = os.open(str(fifo), os.O_WRONLY | os.O_NONBLOCK)
                except OSError:
                    done.wait(.05)
                    continue
                try:
                    os.write(fd, answer)
                except OSError:
                    pass
                finally:
                    os.close(fd)
                # Each ssh process is allowed one password prompt. Stop after
                # its reader receives the answer rather than replaying it.
                return

        writer = threading.Thread(target=deliver, name="songsketch-password-pipe", daemon=True)
        writer.start()
        try:
            yield {"SSH_ASKPASS": str(helper), "SSH_ASKPASS_REQUIRE": "force",
                   "DISPLAY": "songsketch-local", "SONGSKETCH_ASKPASS_FIFO": str(fifo)}
        finally:
            done.set()
            writer.join(1)


class CommissioningManager:
    def __init__(self, config, root=ROOT):
        self.config = config
        self.root = Path(root)
        self.directory = config.directory / "commissioning"
        self.directory.mkdir(mode=0o700, exist_ok=True)
        os.chmod(self.directory, 0o700)
        self.state_path = self.directory / "state.json"
        self.known_hosts = self.directory / "known_hosts"
        self.lock = threading.RLock()
        self.cancel_event = threading.Event()
        self.thread = None
        self.process = None
        self.pending_key = None
        self.job = None
        if self.state_path.exists():
            try:
                self.job = json.loads(self.state_path.read_text())
                if not isinstance(self.job, dict) or not re.fullmatch(r"[a-f0-9]{32}", self.job.get("id", "")):
                    self.job = None
            except (ValueError, OSError):
                self.job = None
        if self.job and self.job.get("state") not in TERMINAL:
            self.job.update(state="interrupted", stage="interrupted", challenge=None,
                            human_action="The local helper restarted. Diagnose the Pi before explicitly retrying setup.",
                            next_actions=["probe", "diagnose", "retry"], updated_at=utc_string())
            self._save()

    def capabilities(self):
        return {"ssh_available": bool(shutil.which("ssh")),
                "keyscan_available": bool(shutil.which("ssh-keyscan")),
                "password_available": os.name == "posix" and hasattr(os, "mkfifo"),
                "auth_methods": ["ssh_key_or_agent", "password"],
                "actions": list(ACTIONS), "ssh_port": 22,
                "host_key_policy": "Exact pinned key; new or changed keys require explicit confirmation.",
                "remote_install_timeout_seconds": 1800}

    def status(self):
        with self.lock:
            return {"capabilities": self.capabilities(),
                    "job": json.loads(json.dumps(self.job)) if self.job else None}

    def _save(self):
        private_json(self.state_path, self.job)

    def _update(self, message=None, **patch):
        with self.lock:
            self.job.update(patch, updated_at=utc_string())
            if message:
                self.job["logs"] = (self.job.get("logs", []) + [{"at": utc_string(), "message": message[:600]}])[-60:]
            self._save()

    def _check_id(self, data):
        if not self.job or data.get("job_id") != self.job["id"]:
            raise ValueError("This setup job is no longer current. Refresh setup status.")

    def _busy(self):
        return bool(self.thread and self.thread.is_alive()) or bool(self.job and self.job.get("state") in ACTIVE)

    def action(self, action, data=None, background=True):
        data = {} if data is None else data
        if action not in ACTIONS or not isinstance(data, dict):
            raise ValueError("Unknown setup action.")
        with self.lock:
            if action == "cancel":
                if set(data) - {"job_id"}:
                    raise ValueError("Unknown cancellation field.")
                self._check_id(data)
                if self.job["state"] in TERMINAL:
                    return self.status()
                self.cancel_event.set()
                self.pending_key = None
                self._update(state="cancelling" if self._busy() else "cancelled", challenge=None,
                             human_action="The connection will stop. Any remote installation already started may still finish; diagnose before retrying.",
                             next_actions=[] if self._busy() else ["diagnose", "probe"])
                return self.status()
            if self._busy():
                raise ValueError("A setup operation is already running. Wait or cancel it first.")
            if action == "probe":
                inputs = validate_inputs(data)
                self.job = {"id": uuid.uuid4().hex, "state": "probing", "stage": "host_key",
                            "progress": 0, "inputs": inputs, "challenge": None, "trusted": False,
                            "commissioned": False, "last_successful_install": None,
                            "logs": [], "result": None, "error": None, "human_action": None,
                            "next_actions": ["cancel"], "created_at": utc_string(), "updated_at": utc_string()}
                self.pending_key = None
                self.cancel_event.clear()
                self._save()
                work = self._probe
                args = ()
            elif action == "trust":
                if set(data) - {"job_id", "challenge_id", "fingerprint", "confirmed"}:
                    raise ValueError("Unknown trust field.")
                self._check_id(data)
                challenge = self.job.get("challenge") or {}
                if (self.job["state"] != "awaiting_trust" or not self.pending_key or
                        data.get("confirmed") is not True or data.get("challenge_id") != challenge.get("challenge_id") or
                        data.get("fingerprint") != challenge.get("fingerprint")):
                    raise ValueError("Confirm the exact current fingerprint after comparing it with the Pi.")
                if time.time() > challenge["expires_epoch"]:
                    self.pending_key = None
                    raise ValueError("The trust challenge expired. Probe the Pi again.")
                self._pin(self.pending_key)
                self.pending_key = None
                self._update("Pi identity explicitly trusted.", state="ready", stage="ready", trusted=True,
                             challenge=None, human_action=None, next_actions=["install", "diagnose", "cancel"])
                return self.status()
            else:
                allowed = {"job_id", "password", "capture_device"} if action != "diagnose" else {"job_id", "password"}
                if set(data) - allowed:
                    raise ValueError("Unknown connection field. Arbitrary commands are not accepted.")
                self._check_id(data)
                if not self.job.get("trusted") or not self._has_pin(self.job["inputs"]["hostname"]):
                    raise ValueError("Probe and explicitly trust the Pi's SSH identity first.")
                permitted = {"ready"} if action == "install" else TERMINAL | {"ready"}
                if self.job["state"] not in permitted:
                    raise ValueError("This job is not ready for that action.")
                if action != "diagnose" and (self.job.get("result") or {}).get("operation_running") is True:
                    raise ValueError("The Pi still reports an active operation. Wait and run diagnostics again before retrying.")
                password = data.get("password", "")
                if (not isinstance(password, str) or len(password.encode("utf-8")) > 1024 or
                        any(c in password for c in "\r\n\x00")):
                    raise ValueError("Enter a valid short-lived SSH password.")
                if password and not self.capabilities()["password_available"]:
                    raise ValueError("Password entry is unavailable on this host. Use an SSH key or agent.")
                capture = data.get("capture_device")
                if capture is not None:
                    choices = (self.job.get("result") or {}).get("capture_sources", [])
                    valid = {row.get("id") for row in choices if isinstance(row, dict)}
                    if not isinstance(capture, str) or capture not in valid or len(capture) > 300 or any(ord(c) < 32 for c in capture):
                        raise ValueError("Choose an exact capture device returned by the Pi.")
                    self.job["inputs"]["capture_device"] = capture
                self.cancel_event.clear()
                self._update("Starting read-only diagnostics." if action == "diagnose" else "Starting the approved Pi setup operation.",
                             state="running", stage="connect", progress=12, error=None,
                             human_action=None, next_actions=["cancel"], operation=action,
                             **({"commissioned": False} if action != "diagnose" else {}))
                work, args = self._remote, (action, password)
            if background:
                self.thread = threading.Thread(target=self._guarded, args=(work, args), name="songsketch-commissioning", daemon=True)
                self.thread.start()
            else:
                self._guarded(work, args)
        return self.status()

    def _guarded(self, work, args):
        try:
            work(*args)
            if self.cancel_event.is_set() and self.job.get("state") not in TERMINAL:
                raise SetupCancelled()
        except SetupCancelled:
            self._update("Local setup connection stopped.", state="cancelled", stage="cancelled", error=None,
                         human_action="The Pi may finish an operation already started. Diagnose it before retrying.",
                         next_actions=["diagnose", "probe"])
        except SetupError as error:
            self._update(error.message, state="failed", error={"code": error.code, "message": error.message},
                         human_action=error.human_action, next_actions=error.next_actions)
        except Exception:
            # Remote output, exception arguments and credentials never enter a
            # generic traceback/status field. Specific failures are mapped below.
            self._update("The setup helper could not finish this operation.", state="failed",
                         error={"code": "helper_error", "message": "The setup helper could not finish this operation."},
                         human_action="Check local disk permissions and installed SSH tools, then diagnose before retrying.",
                         next_actions=["diagnose", "probe"])

    def _probe(self):
        if not shutil.which("ssh") or not shutil.which("ssh-keyscan"):
            raise SetupError("ssh_missing", "OpenSSH tools are not installed on this computer.",
                             "Install the operating system's OpenSSH client, then try again.", ["probe"])
        host = self.job["inputs"]["hostname"]
        result = self._run(["ssh-keyscan", "-T", "5", "-p", "22", "-t", "ed25519,ecdsa,rsa", host], timeout=15)
        key = scan_key(result["stdout"], host)
        if self._has_pin(host, key):
            self._update("The Pi's SSH key exactly matches its saved, explicitly trusted identity.", state="ready",
                         progress=10, stage="ready", trusted=True, fingerprint=key["fingerprint"],
                         human_action=None, next_actions=["install", "diagnose", "cancel"])
            return
        self.pending_key = key
        expires = time.time() + 600
        challenge = {"challenge_id": uuid.uuid4().hex, "fingerprint": key["fingerprint"],
                     "hostname": host, "key_type": key["key_type"], "expires_at": utc_string(expires),
                     "expires_epoch": expires, "changed": self._has_pin(host)}
        message = "This Pi address has a different SSH key. Verify the change directly on the Pi before trusting it." if challenge["changed"] else "Compare this fingerprint with the Pi, then explicitly confirm it. A network scan alone does not verify identity."
        self._update("SSH identity received; awaiting your comparison and confirmation.", state="awaiting_trust",
                     progress=10, challenge=challenge, fingerprint=key["fingerprint"],
                     human_action=message, next_actions=["trust", "probe", "cancel"])

    def _has_pin(self, host, key=None):
        try:
            lines = self.known_hosts.read_text().splitlines()
        except OSError:
            return False
        for line in lines:
            parts = line.split()
            if len(parts) == 3 and parts[0] == host:
                if key is None or parts[1:] == [key["key_type"], key["key"]]:
                    return True
        return False

    def _pin(self, key):
        lines = self.known_hosts.read_text().splitlines() if self.known_hosts.exists() else []
        lines = [line for line in lines if line.split() and line.split()[0] != key["hostname"]]
        lines.append("{hostname} {key_type} {key}".format(**key))
        fd, path = tempfile.mkstemp(prefix="known-hosts-", dir=str(self.directory))
        try:
            with os.fdopen(fd, "w") as stream:
                stream.write("\n".join(lines[-50:]) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(path, self.known_hosts)
            self.known_hosts.chmod(0o600)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def _ssh(self, command, password):
        inputs = self.job["inputs"]
        # Ignore arbitrary user-configured ProxyCommand/LocalCommand/forwarding.
        # Default local keys and the existing agent remain available.
        return ["ssh", "-F", "/dev/null", "-T", "-p", "22",
                "-o", "StrictHostKeyChecking=yes", "-o", "UserKnownHostsFile=" + json.dumps(str(self.known_hosts)),
                "-o", "GlobalKnownHostsFile=/dev/null", "-o", "CheckHostIP=no",
                "-o", "UpdateHostKeys=no", "-o", "VerifyHostKeyDNS=no",
                "-o", "PermitLocalCommand=no", "-o", "ClearAllForwardings=yes",
                "-o", "ForwardAgent=no", "-o", "ControlMaster=no", "-o", "ControlPath=none",
                "-o", "ConnectTimeout=10", "-o", "ConnectionAttempts=1",
                "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=2",
                "-o", "NumberOfPasswordPrompts=1", "-o", "KbdInteractiveAuthentication=no",
                "-o", "PreferredAuthentications=publickey,password",
                "-o", "BatchMode=" + ("no" if password else "yes"),
                "-l", inputs["username"], inputs["hostname"], command]

    def _package(self):
        content = io.BytesIO()
        with tarfile.open(fileobj=content, mode="w:gz") as archive:
            for name in PACKAGE_FILES:
                path = self.root / name
                if not path.is_file() or path.is_symlink() or path.resolve().parent not in {self.root.resolve() / "scripts", self.root.resolve() / "pi"}:
                    raise SetupError("package_incomplete", "This release is missing a required Pi setup file.",
                                     "Download a complete Songsketch release before trying again.", ["probe"])
                data = path.read_bytes()
                if len(data) > 2 * 1024 * 1024:
                    raise SetupError("package_invalid", "A bundled setup file is unexpectedly large.")
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(data), 0o600
                archive.addfile(info, io.BytesIO(data))
        return content.getvalue()

    def _clean(self, value, password="", depth=0):
        if depth > 8:
            return "[truncated]"
        if isinstance(value, dict):
            return {str(k)[:100]: self._clean(v, password, depth + 1) for k, v in list(value.items())[:80]
                    if not re.search(r"password|token|secret|authorization|cookie|api_key", str(k), re.I)}
        if isinstance(value, list):
            return [self._clean(v, password, depth + 1) for v in value[:80]]
        if isinstance(value, str):
            for secret in [password] + list(self.config.secrets.values()):
                if isinstance(secret, str) and secret:
                    value = value.replace(secret, "[redacted]")
            value = re.sub(r"(?i)(bearer\s+)[^\s,;]+", r"\1[redacted]", value)
            value = re.sub(r"(?i)((?:password|token|secret|api.key)\s*[:=]\s*)[^\s,;]+", r"\1[redacted]", value)
            return "".join(c for c in value if ord(c) >= 32 or c == "\n")[:2000]
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return "[omitted]"

    def _remote(self, operation, password):
        inputs = dict(self.job["inputs"])
        stage = "/tmp/songsketch-commission-" + self.job["id"] + "-" + uuid.uuid4().hex[:12]
        # No secret is included in the transferred archive or any process argv.
        package = self._package()
        result = self._run(self._ssh("printf 'SONGSKETCH_SSH_OK\\n'; sudo -n true", password), timeout=30, password=password)
        self._require_ok(result)
        if "SONGSKETCH_SSH_OK" not in result["stdout"]:
            raise SetupError("unexpected_connection", "The SSH connection returned an unexpected response.", "Verify the Pi address and account.", ["probe"])
        self._update("SSH identity and noninteractive administrator access checked.", stage="transfer", progress=20)
        transfer = "umask 077; mkdir -m 700 " + shlex.quote(stage) + " && tar -xzf - -C " + shlex.quote(stage)
        result = self._run(self._ssh(transfer, password), input_bytes=package, timeout=60, password=password)
        self._require_ok(result)
        remote_finished = False
        try:
            self._update("Bundled setup files transferred.", stage="diagnose" if operation == "diagnose" else "provision", progress=25)
            command = "sudo -n python3 " + shlex.quote(stage + "/scripts/commission-pi.py")
            provision = None
            if operation == "diagnose":
                command += " --diagnose"
            else:
                command += " --provision -"
                provision = json.dumps({"schema_version": 1, "server_url": inputs["server_url"],
                                       "station_id": self.config.values["station_id"],
                                       "token": self.config.secrets["station_token"],
                                       "latitude": inputs["latitude"], "longitude": inputs["longitude"],
                                       "timezone": self.config.values["timezone"],
                                       "use_existing_birdnet": inputs.get("use_existing_birdnet", False),
                                       **({"capture_device": inputs["capture_device"]} if inputs.get("capture_device") else {})}).encode()

            def progress(line):
                if not line.startswith("SONGSKETCH_PROGRESS "):
                    return
                try:
                    item = self._clean(protocol_json(line[len("SONGSKETCH_PROGRESS "):]), password)
                    if not isinstance(item, dict):
                        return
                    number = item.get("progress")
                    fields = {"remote_progress": item}
                    if isinstance(number, (int, float)) and not isinstance(number, bool) and math.isfinite(number):
                        fields["progress"] = max(self.job["progress"], min(95, 25 + int(max(0, number) * .7)))
                    if isinstance(item.get("stage"), str):
                        fields["stage"] = item["stage"][:80]
                    self._update(item.get("message") if isinstance(item.get("message"), str) else None, **fields)
                except (ValueError, TypeError):
                    return

            result = self._run(self._ssh(command, password), input_bytes=provision,
                               timeout=180 if operation == "diagnose" else 1800,
                               password=password, on_stdout=progress)
            remote = None
            for line in reversed(result["stdout"].splitlines()):
                try:
                    item = protocol_json(line)
                    accepted = ("complete", "needs_input", "failed", "diagnostic") if operation == "diagnose" else ("complete", "needs_input", "failed")
                    if isinstance(item, dict) and item.get("status") in accepted:
                        remote = self._clean(item, password)
                        # These finite protocol constants are not secret-bearing
                        # prose. A password that happens to equal "complete" or
                        # "in" must never change the operation's outcome/lock.
                        remote["status"] = item["status"]
                        if item.get("code") == "commissioning_in_progress":
                            remote["code"] = "commissioning_in_progress"
                        break
                except ValueError:
                    continue
            if remote is None:
                self._require_ok(result)
                raise SetupError("missing_result", "The Pi did not return a complete setup result.",
                                 "The operation may have partially completed. Run diagnostics before retrying.")
            remote_finished = True
            state = {"complete": "completed", "diagnostic": "completed", "needs_input": "needs_input", "failed": "failed"}[remote["status"]]
            still_running = remote.get("operation_running") is True or remote.get("code") == "commissioning_in_progress"
            if still_running:
                remote["operation_running"] = True
                state = "needs_input"
                remote["human_action"] = "The Pi is still working on an earlier setup operation. Wait, then run diagnostics again."
            if result["returncode"] and state == "completed":
                state = "failed"
                remote["status"] = "failed"
                remote["message"] = "The Pi returned success data but its setup process exited unsuccessfully."
            extra = {"installation_result": remote} if operation != "diagnose" else {}
            if operation != "diagnose" and state == "completed":
                extra.update(commissioned=True, last_successful_install={"at": utc_string(),
                             "operation_id": remote.get("operation_id"), "checks": remote.get("checks", {}),
                             "message": "The bundled Pi installer completed; physical microphone placement and a real bird remain commissioning checks."})
            if operation == "diagnose" and "capture_sources" not in remote:
                remote["capture_sources"] = (self.job.get("result") or {}).get("capture_sources", [])
            self._update(remote.get("message", "Pi diagnostic snapshot received." if operation == "diagnose" else "Pi setup check finished."), state=state,
                         stage=remote.get("stage", state), progress=100 if state == "completed" else self.job["progress"],
                         result=remote, error={"code": remote.get("code", "remote_failed"), "message": remote.get("message", "Pi setup needs attention.")} if state == "failed" else None,
                         human_action=remote.get("human_action"), next_actions=["diagnose"] if still_running else ["diagnose", "retry", "probe"], **extra)
        finally:
            if remote_finished and not self.cancel_event.is_set():
                # Exact random staging path only; no token/password files are
                # here. Cleanup failure is advisory, never an automatic retry.
                try:
                    result = self._run(self._ssh("rm -rf -- " + shlex.quote(stage), password), timeout=15, password=password)
                    if result["returncode"]:
                        self._update("Temporary setup files could not be removed from the Pi; no credentials were in that folder.")
                except (SetupError, SetupCancelled, OSError):
                    self._update("Temporary setup files remain on the Pi; no credentials were in that folder.")
            elif not remote_finished:
                self._update("Remote completion is unconfirmed. Its temporary helper files were left in place in case the Pi is still using them; no credentials were in that folder.")

    def _require_ok(self, result):
        if result["returncode"] == 0:
            return
        stderr = result.get("stderr", "").lower()
        if "host key verification failed" in stderr or "remote host identification has changed" in stderr:
            raise SetupError("host_key_changed", "The Pi's SSH identity no longer matches the trusted key.",
                             "Stop and compare the fingerprint directly on the Pi. Probe again only after checking its identity.", ["probe"])
        if "permission denied" in stderr or "authentication failed" in stderr:
            raise SetupError("authentication_failed", "SSH authentication was not accepted.",
                             "Check the Pi username and local SSH key/agent, or enter its password again. Nothing is saved.", ["retry", "probe"])
        if "sudo:" in stderr:
            raise SetupError("sudo_required", "The Pi account cannot run the installer without an interactive sudo prompt.",
                             "Use the Pi's administrator account with noninteractive sudo configured. The SSH password is never reused for sudo.", ["retry", "probe"])
        raise SetupError("remote_command_failed", "The fixed Pi setup command did not complete successfully.",
                         "Check Pi power, networking and free storage. Run diagnostics before retrying.")

    @staticmethod
    def _stop_process(process):
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=3)

    def _run(self, argv, input_bytes=None, timeout=30, password="", on_stdout=None):
        """Bounded subprocess group, streaming protocol, capped output, no shell."""
        if self.cancel_event.is_set():
            raise SetupCancelled()
        with password_channel(password) as askpass:
            environment = dict(os.environ)
            environment.update(askpass)
            if not password:
                environment.pop("SSH_ASKPASS", None)
                environment["SSH_ASKPASS_REQUIRE"] = "never"
            process = subprocess.Popen(argv, stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
                                       start_new_session=True, close_fds=True)
            self.process = process
            buffers = {"stdout": bytearray(), "stderr": bytearray()}
            excessive = threading.Event()

            def drain(name, stream):
                pending, total = b"", 0
                try:
                    while True:
                        chunk = os.read(stream.fileno(), 4096)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > 1024 * 1024:
                            excessive.set()
                            return
                        buffers[name].extend(chunk)
                        del buffers[name][:-65536]
                        if name == "stdout" and on_stdout:
                            pending += chunk
                            while b"\n" in pending:
                                line, pending = pending.split(b"\n", 1)
                                if len(line) <= 16384:
                                    on_stdout(line.decode("utf-8", "replace"))
                            if len(pending) > 16384:
                                pending = b""
                finally:
                    stream.close()

            readers = [threading.Thread(target=drain, args=(name, stream), daemon=True)
                       for name, stream in (("stdout", process.stdout), ("stderr", process.stderr))]
            for reader in readers:
                reader.start()

            def feed():
                try:
                    process.stdin.write(input_bytes)
                    process.stdin.flush()
                except (BrokenPipeError, OSError):
                    pass
                finally:
                    process.stdin.close()

            writer = None
            if input_bytes is not None:
                writer = threading.Thread(target=feed, daemon=True)
                writer.start()
            deadline = time.monotonic() + timeout
            try:
                while process.poll() is None:
                    if self.cancel_event.wait(.1):
                        raise SetupCancelled()
                    if excessive.is_set():
                        raise SetupError("excessive_output", "The remote operation exceeded its safe output limit.",
                                         "Run diagnostics before retrying.")
                    if time.monotonic() >= deadline:
                        raise SetupError("operation_timeout", "The setup connection exceeded its time limit.",
                                         "Remote work may still be running. Diagnose the Pi before retrying.")
                for reader in readers:
                    reader.join(3)
                if writer:
                    writer.join(1)
                if self.cancel_event.is_set():
                    raise SetupCancelled()
                if excessive.is_set():
                    raise SetupError("excessive_output", "The remote operation exceeded its safe output limit.")
                return {"returncode": process.returncode,
                        **{name: bytes(data).decode("utf-8", "replace") for name, data in buffers.items()}}
            finally:
                self._stop_process(process)
                self.process = None

    def close(self):
        """Stop only this manager's owned SSH subprocess; do not retry remotely."""
        self.cancel_event.set()
        thread = self.thread
        if thread and thread.is_alive():
            thread.join(8)
