#!/usr/bin/env python3
"""macOS service entry: keep the watchdog's intentional stop limits intact."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from songsketch.supervisor import main
code = main()
# launchd has no per-exit-code RestartPreventExitStatus. An occupied port or
# exhausted bounded restart budget is an intentional stop, recorded in logs.
raise SystemExit(0 if code in (3,4) else code)
