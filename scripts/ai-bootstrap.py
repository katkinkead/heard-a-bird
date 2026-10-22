#!/usr/bin/env python3
"""Prepare a managed Songsketch copy, start its helper, and open a private session.

A local assistant obtains this release/checkout first. No persistent service is
installed, no Pi is contacted, and no SD card is written by this bootstrap.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from songsketch import __version__
from songsketch.config import Config, data_directory, private_json
from songsketch.setup_client import SetupClient
from songsketch.supervisor import health_check, port_is_open
from songsketch.github_launcher import LaunchError, read_details

CONTENTS = ("songsketch","scripts","pi","static","guide","docs","artwork","README.md","AGENTS.md","CLAUDE.md","LICENSE","Start Songsketch.command","Pair Garden Pi.command","Open simulated garden.command","Install Mac Background Service.command","integration-plan.md","dashboard-requirements.md","maintenance-requirements.md","RELEASE_NOTES.md")


def managed_copy(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        return "current"
    if destination.exists():
        if (destination/"songsketch/server.py").is_file():
            # Never overlay an installation or a friend's changes silently.
            return "existing"
        raise RuntimeError("The managed app location already contains other files. Ask the local assistant to inspect it; nothing was overwritten.")
    destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    stage = Path(tempfile.mkdtemp(prefix=".songsketch-install-",dir=str(destination.parent)))
    try:
        for name in CONTENTS:
            src = source/name
            if not src.exists(): continue
            if src.is_symlink(): raise RuntimeError("Release contains a symlink; inspect the source before installing")
            if src.is_dir():
                if any(p.is_symlink() for p in src.rglob("*")):
                    raise RuntimeError("Release contains a symlink; inspect the source before installing")
                shutil.copytree(src,stage/name,ignore=shutil.ignore_patterns("__pycache__","*.pyc","*.log*","*.sqlite*",".DS_Store"))
            else: shutil.copy2(src,stage/name)
        for required in ("songsketch/server.py","scripts/setup-assistant.py","artwork/catalogue.json","guide/index.html"):
            if not (stage/required).is_file(): raise RuntimeError("Release is missing required files: "+required)
        stage.rename(destination)
    finally:
        if stage.exists(): shutil.rmtree(stage)
    return "installed"


def apply_saved_setup_preferences(client, directory):
    """Import only the requested recipient; never echo private setup values."""
    source = Path(directory) / "setup-details.json"
    if not source.exists(): return {}
    details = read_details(source)
    recipient = details.get("notification_email")
    if not recipient: return {}
    acknowledged = client.request("/api/admin/settings", {"notification_email": recipient})
    if not isinstance(acknowledged, dict) or acknowledged.get("ok") is not True:
        raise RuntimeError("The server did not confirm the saved notification preference.")
    return {"notification_recipient_saved": True, "email_delivery_verified": False}


def bootstrap(directory, port, no_open=False, dry_run=False):
    directory = Path(directory).expanduser().resolve()
    destination = directory/"app"
    if dry_run:
        return {"dry_run":True,"source":str(ROOT),"application":str(destination),"private_data":str(directory),"persistent_service":False,"pi_contacted":False}
    cfg = Config(directory)
    client = SetupClient(cfg,port)
    if port_is_open(port):
        if health_check(port).state != "healthy":
            raise RuntimeError("The port is in use by a service that did not pass Songsketch's health check. No process was stopped; inspect the existing service.")
        context = client.request("/api/admin/setup-context") # verifies existing credentials + new helper capability
        result = {"ok":True,"reused_running_server":True,"version":context.get("version"),"guide":client.base+"/guide/index.html"}
        result.update(apply_saved_setup_preferences(client, directory))
        if not no_open: result.update(client.open_guide())
        return result
    install = managed_copy(ROOT,destination)
    logs = directory/"logs"
    logs.mkdir(mode=0o700,exist_ok=True)
    # Supervisor and server own rotating logs; bootstrap stdio is not retained.
    # A race on port ownership is handled by the supervisor without killing it.
    child = subprocess.Popen([sys.executable,"-m","songsketch.supervisor","--port",str(port),"--data-dir",str(directory)],cwd=str(destination),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    ready = False
    try:
        for _ in range(60):
            if child.poll() is not None: raise RuntimeError("The local helper stopped during startup. Inspect logs/supervisor.log and supervisor-status.json in the private data folder.")
            if health_check(port).state == "healthy":
                context = client.request("/api/admin/setup-context")
                ready = True
                break
            time.sleep(.5)
        if not ready: raise RuntimeError("The helper did not become ready. Its saved logs explain the startup failure; no Pi settings were changed.")
        private_json(directory/"bootstrap.json",{"version":context.get("version"),"application":str(destination),"supervisor_pid":child.pid})
        if sys.platform == "darwin":
            subprocess.Popen(["/usr/bin/caffeinate","-i","-w",str(child.pid)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
        result = {"ok":True,"installation":install,"version":context.get("version"),"application":str(destination),"private_data":str(directory),"guide":client.base+"/guide/index.html","supervisor_pid":child.pid,"persistent_service":False}
        result.update(apply_saved_setup_preferences(client, directory))
        if not no_open: result.update(client.open_guide())
        return result
    except Exception:
        if not ready and child.poll() is None:
            child.terminate()
            try: child.wait(timeout=25)
            except subprocess.TimeoutExpired:
                # Supervisor owns cleanup. Do not kill it and orphan its child.
                pass
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir")
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--no-open",action="store_true")
    parser.add_argument("--dry-run",action="store_true")
    args = parser.parse_args(argv)
    try:
        result = bootstrap(args.data_dir or data_directory(),args.port,args.no_open,args.dry_run)
        print(json.dumps(result,indent=2))
        return 0
    except (OSError,RuntimeError,ValueError,LaunchError) as exc:
        print(json.dumps({"ok":False,"error":str(exc),"next":"Read docs/ai-setup.md. Inspect the current installation and its private logs; preserve history and existing credentials."}))
        return 1

if __name__ == "__main__": raise SystemExit(main())
