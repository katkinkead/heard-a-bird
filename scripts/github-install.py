#!/usr/bin/env python3
"""Repository entrypoint; the downloadable .command embeds this same module."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from songsketch.github_launcher import main
if __name__ == "__main__": raise SystemExit(main())
