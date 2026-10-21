#!/usr/bin/env python3
"""Double-click fallback for the same managed, AI-led setup bootstrap."""
from pathlib import Path
import runpy
ROOT = Path(__file__).resolve().parent.parent
if __name__ == "__main__":
    runpy.run_path(str(ROOT/"scripts/ai-bootstrap.py"),run_name="__main__")
