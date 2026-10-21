#!/usr/bin/env python3
"""Machine-readable, guarded setup interface for a local terminal-capable AI."""
import argparse
import getpass
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from songsketch.config import Config, data_directory
from songsketch.setup_client import SetupClient


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", help="Existing private data folder; defaults to the platform location")
    parser.add_argument("--port", type=int, default=8765)
    sub = parser.add_subparsers(dest="command",required=True)
    sub.add_parser("status"); sub.add_parser("open"); sub.add_parser("diagnose",help="Read a local recovery packet without changing the Pi")
    probe = sub.add_parser("probe",help="Validate settings and obtain an SSH host-key challenge")
    for name in ("hostname","username","server-url"):
        probe.add_argument("--"+name,required=True)
    probe.add_argument("--latitude",type=float,required=True)
    probe.add_argument("--longitude",type=float,required=True)
    trust = sub.add_parser("trust",help="Record a host fingerprint only after informed confirmation")
    for name in ("job-id","challenge-id","fingerprint"):
        trust.add_argument("--"+name,required=True)
    trust.add_argument("--confirmed",action="store_true",required=True)
    for command in ("install","retry","diagnose-pi","cancel"):
        action = sub.add_parser(command)
        action.add_argument("--job-id",required=True)
        if command != "cancel":
            action.add_argument("--ask-password",action="store_true",help="Prompt locally without echo; prefer an existing SSH key/agent")
            if command != "diagnose-pi": action.add_argument("--capture-device")
            action.add_argument("--wait",action="store_true",help="Poll for up to ten minutes; expiration does not cancel the job")
    args = parser.parse_args(argv)
    directory = Path(args.data_dir).expanduser() if args.data_dir else data_directory()
    if not (directory/"secrets.json").is_file():
        parser.error("No existing Songsketch installation here. Run ai-bootstrap.py first; do not create new credentials for an existing server.")
    client = SetupClient(Config(directory),args.port)
    try:
        if args.command == "open": result = client.open_guide()
        elif args.command == "status": result = client.request("/api/admin/setup")
        elif args.command == "diagnose": result = client.request("/api/admin/setup-context")
        else:
            fields = ("hostname","username","server_url","latitude","longitude","job_id","challenge_id","fingerprint","confirmed","capture_device")
            data = {key:getattr(args,key) for key in fields if getattr(args,key,None) is not None}
            if getattr(args,"ask_password",False):
                if not sys.stdin.isatty(): raise RuntimeError("Use the local guide password field or a real secure terminal; do not paste passwords into AI chat.")
                data["password"] = getpass.getpass("Pi SSH password (not saved): ")
            action = "diagnose" if args.command == "diagnose-pi" else args.command
            try: result = client.request("/api/admin/setup/"+action,data)
            finally: data.pop("password",None)
            if getattr(args,"wait",False):
                until = time.monotonic()+600
                while time.monotonic()<until:
                    result = client.request("/api/admin/setup")
                    if (result.get("job") or {}).get("state") not in ("probing","running","installing","diagnosing","connecting","cancelling"):
                        break
                    time.sleep(2)
        print(json.dumps(result,indent=2,allow_nan=False))
        return 0
    except (RuntimeError,ValueError) as exc:
        print(json.dumps({"ok":False,"error":str(exc),"next":"Read docs/ai-setup.md and the saved setup checkpoint. Do not repeat the same repair more than twice."}))
        return 1

if __name__ == "__main__": raise SystemExit(main())
