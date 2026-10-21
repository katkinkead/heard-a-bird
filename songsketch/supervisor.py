"""Bounded, local HTTP watchdog for the Songsketch server process.

This process owns only the child it launches. It never reads/writes the server
database, executes model suggestions, or terminates a process found on a port.
"""
import argparse
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .config import ROOT, data_directory, private_json

HEALTH_INTERVAL = 30
HEALTH_FAILURES = 3
HEALTH_TIMEOUT = 5
RESTART_WINDOW = 15 * 60
MAX_RESTARTS = 5
MAX_BACKOFF = 120
STABLE_RESET = 5 * 60
STOP_TIMEOUT = 10
ALLOWED_HOSTS = ("0.0.0.0", "127.0.0.1", "localhost")


@dataclass(frozen=True)
class Health:
    state: str
    reason: str


class NoHealthRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def health_check(port, opener=None):
    """Return bounded evidence, never persist response text or credentials."""
    client = opener or build_opener(ProxyHandler({}),NoHealthRedirect())
    request = Request(f"http://127.0.0.1:{port}/health", headers={"Accept":"application/json"})
    try:
        with client.open(request, timeout=HEALTH_TIMEOUT) as response:
            if response.status != 200:
                return Health("unhealthy", "Health endpoint did not return HTTP 200")
            raw = response.read(16385)
        if len(raw) > 16384:
            return Health("unhealthy", "Health response exceeded 16 KB")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return Health("unhealthy", "Health response was not an object")
        if data.get("application") not in (None, "songsketch"):
            return Health("foreign", "The port reports a different application")
        if data.get("application") == "songsketch" and data.get("ok") is True:
            return Health("healthy", "Songsketch HTTP health check passed")
        return Health("unhealthy", "Songsketch did not report healthy")
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, UnicodeError):
        return Health("unhealthy", "Songsketch health endpoint is unavailable or invalid")


def port_is_open(port):
    try:
        with socket.create_connection(("127.0.0.1",port), timeout=1):
            return True
    except OSError:
        return False


class RestartBudget:
    """Sliding-window restart limit, independent of wall-clock adjustments."""
    def __init__(self, maximum=MAX_RESTARTS, window=RESTART_WINDOW):
        self.maximum = maximum
        self.window = window
        self.times = deque()

    def available(self, now):
        while self.times and self.times[0] <= now-self.window:
            self.times.popleft()
        return len(self.times) < self.maximum

    def record(self, now):
        if not self.available(now):
            return False
        self.times.append(now)
        return True


class Supervisor:
    def __init__(self, host="0.0.0.0", port=8765, directory=None, *,
                 process_factory=None, probe=None, port_probe=None,
                 clock=None, wait=None, logger=None):
        if host not in ALLOWED_HOSTS:
            raise ValueError("Use 0.0.0.0, 127.0.0.1 or localhost so local health checks can reach the server")
        if isinstance(port,bool) or not isinstance(port,int) or not 1 <= port <= 65535:
            raise ValueError("Port must be an integer from 1 to 65535")
        self.host, self.port = host, port
        self.directory = Path(directory or data_directory()).expanduser().resolve()
        self.directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        os.chmod(self.directory,0o700)
        self.stop = threading.Event()
        self.process_factory = process_factory or subprocess.Popen
        self.probe = probe or health_check
        self.port_probe = port_probe or port_is_open
        self.clock = clock or time.monotonic
        self.wait = wait or self.stop.wait
        self.logger = logger or logging.getLogger("songsketch.supervisor")
        self.child = None
        self.budget = RestartBudget()
        self.consecutive_restarts = 0
        self.total_restarts = 0
        self.last_note = None

    @property
    def command(self):
        return [sys.executable,"-m","songsketch.server","--host",self.host,
                "--port",str(self.port),"--data-dir",str(self.directory)]

    def request_stop(self, *_args):
        self.stop.set()

    def note(self, state, reason):
        # Notes contain fixed operational descriptions, never child output,
        # environment variables, HTTP bodies, incoming URLs or configuration.
        value = {"state":state,"reason":reason,"updated_at":datetime.now(timezone.utc).isoformat(),
                 "supervisor_pid":os.getpid(),"child_pid":self.child.pid if self.child else None,
                 "restarts_this_run":self.total_restarts}
        try:
            private_json(self.directory / "supervisor-status.json",value)
        except OSError:
            # Full/read-only storage must not lose ownership of a running
            # child or prevent recovery. The normal server reports disk faults.
            self.logger.error("Could not save supervisor status; check data-folder storage")
        if (state,reason) != self.last_note:
            level = logging.INFO if state in ("starting","healthy","stopped") else logging.WARNING
            self.logger.log(level,"%s: %s",state,reason)
            self.last_note = (state,reason)

    def launch(self):
        try:
            # A private process session prevents terminal Ctrl-C from racing
            # the parent's bounded shutdown. Only this child is ever stopped.
            self.child = self.process_factory(self.command,cwd=str(ROOT),start_new_session=True)
        except OSError:
            self.child = None
            self.note("restarting","The server process could not be started")
            return False
        self.note("starting","Starting the local Songsketch server")
        return True

    def stop_child(self):
        child = self.child
        if child is None:
            return
        reaped = False
        try:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=STOP_TIMEOUT)
                except subprocess.TimeoutExpired:
                    self.logger.warning("Owned server did not stop within %s seconds; terminating it",STOP_TIMEOUT)
                    child.kill()
                    child.wait(timeout=STOP_TIMEOUT)
            else:
                child.wait(timeout=STOP_TIMEOUT)
            reaped = True
        except ProcessLookupError:
            # The process can finish between poll() and terminate(); still reap
            # the child instead of abandoning a completed process handle.
            child.wait(timeout=STOP_TIMEOUT)
            reaped = True
        finally:
            if reaped:
                self.child = None

    def occupied(self):
        if not self.port_probe(self.port):
            return False
        health = self.probe(self.port)
        message = ("Songsketch is already running on this port. Open the existing display or stop its launcher first."
                   if health.state == "healthy" else
                   "The selected port is already occupied. Stop that service or choose a different port; no process was terminated.")
        self.note("already_running",message)
        return True

    def run(self):
        if self.occupied():
            return 3
        self.launch()
        started = self.clock()
        next_health = started+HEALTH_INTERVAL
        failures = 0
        try:
            while not self.stop.is_set():
                now = self.clock()
                return_code = self.child.poll() if self.child else None
                reason = "The server process could not be started" if self.child is None else None
                if self.child and return_code is not None:
                    reason = f"The owned server process exited with code {return_code}"
                elif self.child and now >= next_health:
                    health = self.probe(self.port)
                    next_health = self.clock()+HEALTH_INTERVAL
                    if health.state == "foreign":
                        self.note("failed","A different application answered on the health port; stopping only the owned child")
                        return 3
                    if health.state == "healthy":
                        failures = 0
                        self.note("healthy","Songsketch HTTP health check passed")
                        if now-started >= STABLE_RESET:
                            self.consecutive_restarts = 0
                    else:
                        failures += 1
                        self.note("checking",f"Health check {failures} of {HEALTH_FAILURES} failed")
                        if failures >= HEALTH_FAILURES:
                            reason = "Three consecutive local health checks failed"
                if reason:
                    self.note("restarting",reason)
                    self.stop_child()
                    if self.stop.is_set():
                        break
                    if not self.budget.available(self.clock()):
                        self.note("failed","Restart limit reached: five restarts within fifteen minutes. Check the supervisor log and server diagnostics.")
                        return 4
                    delay = min(MAX_BACKOFF,2**min(self.consecutive_restarts,10))
                    self.note("restarting",f"Waiting {delay} seconds before a bounded restart")
                    if self.wait(delay) or self.stop.is_set():
                        break
                    # A different process may have claimed the port while our
                    # child was stopped. Never treat that process as ours.
                    if self.occupied():
                        return 3
                    if not self.budget.record(self.clock()):
                        self.note("failed","Restart limit reached before launch")
                        return 4
                    self.consecutive_restarts += 1
                    self.total_restarts += 1
                    self.launch()
                    started = self.clock()
                    next_health = started+HEALTH_INTERVAL
                    failures = 0
                    continue
                if self.wait(min(1,max(0.01,next_health-self.clock()))):
                    break
            self.note("stopped","Launcher stopped; the owned server is being closed")
            return 0
        finally:
            self.stop_child()
            if self.last_note:
                self.note(*self.last_note)


class PrivateRotatingFileHandler(RotatingFileHandler):
    def doRollover(self):
        super().doRollover()
        os.chmod(self.baseFilename,0o600)


def configure_logging(directory):
    folder = Path(directory) / "logs"
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    path = folder / "supervisor.log"
    # Create before the rotating handler so fresh logs start private.
    descriptor = os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
    os.close(descriptor)
    os.chmod(path,0o600)
    handler = PrivateRotatingFileHandler(path,maxBytes=1024*1024,backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger = logging.getLogger("songsketch.supervisor")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(handler)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("Songsketch: %(message)s"))
    logger.addHandler(console)
    return logger


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run Songsketch with bounded local health recovery")
    parser.add_argument("--host",default="0.0.0.0",choices=ALLOWED_HOSTS)
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--data-dir")
    args = parser.parse_args(argv)
    directory = Path(args.data_dir).expanduser().resolve() if args.data_dir else data_directory()
    try:
        supervisor = Supervisor(args.host,args.port,directory)
    except ValueError as exc:
        parser.error(str(exc))
    supervisor.logger = configure_logging(supervisor.directory)
    signal.signal(signal.SIGINT,supervisor.request_stop)
    signal.signal(signal.SIGTERM,supervisor.request_stop)
    try:
        return supervisor.run()
    except Exception:
        supervisor.logger.exception("Supervisor failed; stopping its owned child")
        supervisor.stop_child()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
