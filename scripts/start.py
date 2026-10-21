#!/usr/bin/env python3
"""Double-click launcher. Keep the terminal for the setup code and Ctrl-C shutdown."""
from pathlib import Path
import json
import os
import signal
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from songsketch.config import Config

def running():
    try:
        with urlopen("http://localhost:8765/health",timeout=1) as r:
            return json.load(r).get("application") == "songsketch"
    except Exception: return False

def main():
    config = Config()
    print("\n  SONGSKETCH\n  A listening garden. A slowly painted bird.\n")
    print("Your private setup code (paste it into the dashboard):\n\n"+config.secrets["admin_token"]+"\n")
    print("Keep this code on the server computer. It is not the Pi pairing token.\n")
    if running():
        webbrowser.open("http://localhost:8765/setup")
        print("Songsketch is already running. The guide is opening.\n")
        return
    child = subprocess.Popen([sys.executable,"-m","songsketch.supervisor"],cwd=str(ROOT))
    awake = None
    if sys.platform == "darwin":
        awake = subprocess.Popen(["/usr/bin/caffeinate","-i","-w",str(child.pid)])
    try:
        for _ in range(40):
            if child.poll() is not None: raise RuntimeError("Songsketch could not start. Port 8765 may already be in use.")
            if running(): break
            time.sleep(.25)
        else: raise RuntimeError("The server did not become ready. Check the logs in your Songsketch data folder.")
        webbrowser.open("http://localhost:8765/setup")
        print("Keep this window open for the MacBook MVP. Press Control-C to stop.\nLeave the Mac plugged in with its lid open.\n")
        child.wait()
    except KeyboardInterrupt:
        child.terminate()
        child.wait(timeout=25)
    finally:
        if child.poll() is None: child.terminate()
        if awake and awake.poll() is None: awake.terminate()

if __name__ == "__main__": main()
