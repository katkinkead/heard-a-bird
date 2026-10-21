#!/usr/bin/env python3
"""Install a per-user launchd service; does not require root or edit sleep settings."""
import argparse
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from songsketch.config import Config

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",action="store_true")
    parser.add_argument("--remove",action="store_true")
    args = parser.parse_args()
    if sys.platform != "darwin": raise SystemExit("This helper is for macOS. Use the Linux service helper on a Linux mini PC.")
    dest = Path.home()/"Library/Application Support/Songsketch/app"
    plist = Path.home()/"Library/LaunchAgents/garden.songsketch.server.plist"
    domain = "gui/"+str(os.getuid())
    command = [sys.executable,str(dest/"scripts/service-entry.py")]
    spec = {"Label":"garden.songsketch.server","ProgramArguments":["/usr/bin/caffeinate","-i"]+command,"WorkingDirectory":str(dest),"RunAtLoad":True,"KeepAlive":{"SuccessfulExit":False},"ThrottleInterval":60,"EnvironmentVariables":{"PYTHONDONTWRITEBYTECODE":"1"},"StandardOutPath":"/dev/null","StandardErrorPath":"/dev/null"}
    if args.dry_run:
        print(plistlib.dumps(spec).decode()); return
    if args.remove:
        subprocess.run(["launchctl","bootout",domain,str(plist)],check=False)
        if plist.exists(): plist.unlink()
        print("Background service removed. Artwork and history are preserved."); return
    cfg = Config(dest.parent)
    if ROOT.resolve() != dest.resolve():
        dest.mkdir(parents=True,exist_ok=True)
        shutil.copytree(ROOT,dest,dirs_exist_ok=True,ignore=shutil.ignore_patterns(".git","__pycache__","dist","runtime","work","*.sqlite*","*.log*"))
    plist.parent.mkdir(parents=True,exist_ok=True)
    with plist.open("wb") as f: plistlib.dump(spec,f)
    subprocess.run(["launchctl","bootout",domain,str(plist)],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(["launchctl","bootstrap",domain,str(plist)],check=True)
    print("Songsketch is installed for this Mac account and starts after login. Leave the lid open and power connected.")
    print("Ask your local assistant to open the private guide with scripts/setup-assistant.py open. Setup: http://localhost:8765/setup")

if __name__ == "__main__": main()
