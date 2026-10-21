#!/usr/bin/env python3
"""Read-only local preflight, independent of external accounts and hardware."""
import json
from pathlib import Path
import sqlite3
import sys
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent
errors = []
if sys.version_info < (3,9): errors.append("Python 3.9 or newer is required")
try: ZoneInfo("Europe/London")
except Exception: errors.append("Timezone database is missing (install tzdata on Linux)")
catalogue = json.loads((ROOT/"artwork/catalogue.json").read_text())
for bird in catalogue["birds"]:
    for key in ("image_url","animation_url"):
        if not (ROOT/bird[key].lstrip("/")).is_file(): errors.append("Missing "+bird[key])
for file in ("guide/index.html","static/display.html","static/dashboard.html","pi/relay.py"):
    if not (ROOT/file).is_file(): errors.append("Missing "+file)
db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE test (id INTEGER)"); db.close()
print(json.dumps({"ok":not errors,"python":sys.version.split()[0],"approved_birds":len(catalogue["birds"]),"errors":errors,"not_checked":["real Pi","microphone","reboot recovery","SMTP delivery","paid AI access"]},indent=2))
raise SystemExit(1 if errors else 0)
