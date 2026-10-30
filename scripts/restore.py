#!/usr/bin/env python3
"""Restore a migration export while holding the target data-directory lock."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import zipfile
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from songsketch.config import Config, data_directory, DEFAULTS
from songsketch.locking import RunLock
NAMES=('songsketch.sqlite3','songsketch.sqlite3-wal','songsketch.sqlite3-shm','config.json','approved-artwork.json','approved')

def restore(archive_path,directory=None):
    directory=Path(directory or data_directory())
    # The lock belongs to this runtime, independent of its port or other gardens.
    run_lock=RunLock(directory)
    try:
        with tempfile.TemporaryDirectory(prefix='songsketch-restore-') as temp:
            temp=Path(temp)
            with zipfile.ZipFile(archive_path) as archive:
                infos=archive.infolist()
                if sum(i.file_size for i in infos)>2*1024**3:raise ValueError('Migration pack is over the 2 GB safety limit')
                seen=set()
                for item in infos:
                    p=Path(item.filename)
                    allowed=item.filename in ('songsketch.sqlite3','config.json','approved-artwork.json','RESTORE.txt') or (len(p.parts)==2 and p.parts[0]=='approved' and p.suffix=='.png')
                    if p.is_absolute() or '..' in p.parts or not allowed or item.filename in seen or (item.external_attr>>16)&0o170000==0o120000:raise ValueError('Unexpected migration entry: '+item.filename)
                    seen.add(item.filename);archive.extract(item,temp)
            db=temp/'songsketch.sqlite3'
            if not db.is_file():raise ValueError('No database in this migration pack')
            conn=sqlite3.connect(str(db))
            try:
                if conn.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Database integrity check failed')
                if conn.execute('PRAGMA user_version').fetchone()[0]!=1:raise ValueError('Unsupported database version')
                tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not {'detections','stations','meta','queue','email_outbox'}.issubset(tables):raise ValueError('Incomplete Songsketch database')
            finally:conn.close()
            settings=json.loads((temp/'config.json').read_text())
            if not isinstance(settings,dict) or set(settings)-set(DEFAULTS):raise ValueError('Unexpected or secret settings in migration pack')
            Config(temp/'validation').update(settings) # Validate before touching target files.
            art=temp/'approved-artwork.json'
            if art.exists():
                value=json.loads(art.read_text())
                if not isinstance(value,dict) or not isinstance(value.get('birds'),list):raise ValueError('Invalid custom artwork catalogue')
            cfg=Config(directory)
            rollback=directory/('before-restore-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            rollback.mkdir(mode=0o700)
            for name in NAMES:
                old=directory/name
                if old.exists():shutil.copytree(old,rollback/name) if old.is_dir() else shutil.copy2(old,rollback/name)
            try:
                for name in NAMES:
                    dest=directory/name
                    if dest.is_dir():shutil.rmtree(dest)
                    elif dest.exists():dest.unlink()
                cfg.update(settings)
                for name in ('songsketch.sqlite3','approved-artwork.json','approved'):
                    src=temp/name
                    if src.exists():shutil.move(str(src),str(directory/name))
            except Exception:
                for name in NAMES:
                    dest=directory/name
                    if dest.is_dir():shutil.rmtree(dest)
                    elif dest.exists():dest.unlink()
                    old=rollback/name
                    if old.exists():shutil.copytree(old,dest) if old.is_dir() else shutil.copy2(old,dest)
                raise
            return rollback
    finally:run_lock.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);parser.add_argument('--data-dir',type=Path);args=parser.parse_args()
    try:rollback=restore(args.archive,args.data_dir)
    except (ValueError,RuntimeError,OSError,sqlite3.DatabaseError,zipfile.BadZipFile) as exc:raise SystemExit('Restore stopped: '+str(exc)) from None
    print('History and approved custom art restored. Original data is in '+str(rollback))
    print('Credentials were not imported. Re-pair the Pi and re-enter optional email/AI credentials on a new host.')
if __name__=='__main__':main()
