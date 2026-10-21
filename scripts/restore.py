#!/usr/bin/env python3
"""Restore a migration export safely, with the server stopped and a rollback copy."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
from urllib.request import urlopen
import zipfile
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from songsketch.config import Config, private_json, data_directory
from songsketch.locking import RunLock

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive",type=Path)
    parser.add_argument("--data-dir",type=Path)
    args = parser.parse_args()
    try:
        with urlopen("http://localhost:8765/health",timeout=1) as r:
            if json.load(r).get("application") == "songsketch":
                raise SystemExit("Stop Songsketch and its background service before restoring.")
    except (OSError,ValueError): pass
    run_lock = RunLock(args.data_dir or data_directory())
    cfg = Config(args.data_dir)
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        with zipfile.ZipFile(args.archive) as archive:
            if sum(i.file_size for i in archive.infolist()) > 2*1024**3: raise SystemExit("Migration pack is over the 2 GB safety limit")
            for item in archive.infolist():
                p = Path(item.filename)
                allowed = item.filename in ("songsketch.sqlite3","config.json","approved-artwork.json","RESTORE.txt") or (len(p.parts)==2 and p.parts[0]=="approved" and p.suffix==".png")
                if p.is_absolute() or ".." in p.parts or not allowed: raise SystemExit("Unexpected migration entry: "+item.filename)
                archive.extract(item,temp)
        db = temp/"songsketch.sqlite3"
        if not db.is_file(): raise SystemExit("No database in this migration pack")
        conn = sqlite3.connect(str(db))
        try:
            if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok": raise SystemExit("Database integrity check failed")
            if conn.execute("PRAGMA user_version").fetchone()[0] != 1: raise SystemExit("Unsupported database version")
        finally: conn.close()
        settings = json.loads((temp/"config.json").read_text())
        rollback = cfg.directory/("before-restore-"+datetime.now().strftime("%Y%m%d-%H%M%S"))
        rollback.mkdir(mode=0o700)
        for name in ("songsketch.sqlite3","songsketch.sqlite3-wal","songsketch.sqlite3-shm","config.json","approved-artwork.json","approved"):
            old = cfg.directory/name
            if old.exists(): shutil.move(str(old),str(rollback/name))
        try:
            cfg.update(settings)
            for name in ("songsketch.sqlite3","approved-artwork.json","approved"):
                src = temp/name
                if src.exists(): shutil.move(str(src),str(cfg.directory/name))
        except Exception:
            for item in rollback.iterdir():
                dest = cfg.directory/item.name
                if dest.is_dir(): shutil.rmtree(dest)
                elif dest.exists(): dest.unlink()
                shutil.copytree(item,dest) if item.is_dir() else shutil.copy2(item,dest)
            raise
    print("History and approved custom art restored. Original data is in "+str(rollback))
    print("Credentials were not imported. Re-pair the Pi and re-enter optional email/AI credentials.")
    run_lock.close()

if __name__ == "__main__": main()
