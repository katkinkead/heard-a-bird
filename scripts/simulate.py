#!/usr/bin/env python3
"""Start the separate, local-only Songsketch test garden."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from songsketch.simulation import main
if __name__ == "__main__":
    raise SystemExit(main())
