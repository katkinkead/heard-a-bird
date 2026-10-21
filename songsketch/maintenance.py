"""Bounded, deterministic housekeeping. Never executes AI-generated commands."""
from datetime import timedelta
from email.message import EmailMessage
import json
import logging
import os
from pathlib import Path
import shutil
import smtplib
import sqlite3
import ssl
import threading
import time
from .store import iso, utcnow, redact, timestamp

class Maintenance:
    def __init__(self, store):
        self.store = store
        self.config = store.config
        self.stop = threading.Event()
        self.mail_lock = threading.Lock()
        self.last_cycle = 0

    def backup(self):
        folder = self.config.directory / "backups"
        folder.mkdir(exist_ok=True, mode=0o700)
        dest = folder / (utcnow().strftime("%Y%m%d-%H%M%S-%f") + ".sqlite3")
        try:
            with self.store.lock:
                copy = sqlite3.connect(str(dest))
                try:
                    self.store.conn.backup(copy)
                    if copy.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                        raise RuntimeError("Backup integrity check failed")
                finally:
                    copy.close()
            os.chmod(dest, 0o600)
            for old in sorted(folder.glob("*.sqlite3"))[:-7]:
                old.unlink()
            self.store.set_meta("last_backup", iso())
            return {"ok":True,"filename":dest.name,"message":"Database snapshot saved; seven most recent are retained. Export a migration pack to include approved custom art."}
        except Exception:
            self.store.issue("backup-failed", "error", "The database backup failed. Check free disk space and the data folder permissions.")
            raise

    def check(self):
        station = self.store.station_status()
        if station["ever_connected"] and not station["connected"]:
            self.store.issue("pi-disconnected", "warning", "The Pi has stopped checking in. Paintings continue; reconnect the Pi to recover buffered detections.")
        if station["connected"] and station["listening"] == "unavailable":
            self.store.issue("audio-unavailable", "error", "The Pi is connected but audio or inference reports a fault.")
        elif station["listening"] == "available":
            with self.store.tx() as db:
                db.execute("UPDATE issues SET resolved=1 WHERE id='audio-unavailable'")
        disk = shutil.disk_usage(self.config.directory)
        if disk.free < 512 * 1024 * 1024:
            self.store.issue("low-disk", "error", "Less than 512 MB is free on the server disk. Move backups or free space; history has not been erased.")
        else:
            with self.store.tx() as db:
                db.execute("UPDATE issues SET resolved=1 WHERE id='low-disk'")
        if self.store.query("PRAGMA quick_check")[0]["quick_check"] != "ok":
            self.store.issue("database-integrity", "error", "Database integrity check failed. Stop the service and restore a verified backup.")
        return {"ok":True,"station":station,"disk_free_bytes":disk.free,"last_backup":self.store.meta("last_backup"),"issues":self.store.query("SELECT * FROM issues WHERE resolved=0 ORDER BY last_seen DESC LIMIT 50")}

    def cleanup(self):
        with self.store.tx() as db:
            db.execute("DELETE FROM reports WHERE received_at<? OR report_id NOT IN (SELECT report_id FROM reports ORDER BY received_at DESC LIMIT 5000)", (iso(utcnow()-timedelta(days=30)),))
            db.execute("DELETE FROM issues WHERE resolved=1 AND last_seen<?", (iso(utcnow()-timedelta(days=30)),))
            db.execute("DELETE FROM detections WHERE (test=1 AND received_at<?) OR observed_at<?", (iso(utcnow()-timedelta(days=7)),iso(utcnow()-timedelta(days=self.config.values["detection_retention_days"]))))
        with self.store.lock:
            self.store.conn.execute("PRAGMA wal_checkpoint(PASSIVE)")

    def send_mail(self):
        if not self.config.public()["email_configured"] or not self.mail_lock.acquire(blocking=False):
            return 0
        sent = 0
        try:
            rows = self.store.query("SELECT * FROM email_outbox WHERE status IN ('pending','failed') AND attempts<5 AND next_attempt<=? ORDER BY created_at LIMIT 5", (iso(),))
            for row in rows:
                if self.store.bird(row["species"]):
                    with self.store.tx() as db:
                        db.execute("UPDATE email_outbox SET status='resolved' WHERE id=?", (row["id"],))
                    continue
                details = self.store.query("SELECT * FROM missing_art WHERE scientific_name=? AND resolved=0", (row["species"],))
                if not details: continue
                d, c = details[0], self.config.values
                msg = EmailMessage()
                msg["From"], msg["To"] = c["smtp_from"], c["notification_email"]
                msg["Subject"] = "A new visitor needs a portrait: " + d["common_name"]
                msg["Message-ID"] = "<" + row["id"] + "@songsketch.local>"
                msg.set_content("Songsketch heard " + d["common_name"] + " (" + d["scientific_name"] + ").\n\nFirst qualifying detection: " + d["first_seen"] + "\nThis species has no approved artwork yet. Its detections are safely recorded, and the display is continuing with the birds it knows.\n\nOpen the Songsketch dashboard on the server computer to review it. You will receive just this first missing-artwork notice for this species.\n")
                with self.store.tx() as db:
                    db.execute("UPDATE email_outbox SET status='sending',attempts=attempts+1 WHERE id=?", (row["id"],))
                submission_started = False
                try:
                    cls = smtplib.SMTP_SSL if int(c["smtp_port"]) == 465 else smtplib.SMTP
                    kwargs = {"host":c["smtp_host"],"port":int(c["smtp_port"]),"timeout":15}
                    if cls is smtplib.SMTP_SSL: kwargs["context"] = ssl.create_default_context()
                    with cls(**kwargs) as smtp:
                        if c["smtp_tls"] and cls is smtplib.SMTP:
                            smtp.starttls(context=ssl.create_default_context())
                        if c["smtp_user"]:
                            if cls is smtplib.SMTP and not c["smtp_tls"]:
                                raise ValueError("Enable TLS before using SMTP credentials")
                            smtp.login(c["smtp_user"],self.config.secrets.get("smtp_password", ""))
                        submission_started = True
                        smtp.send_message(msg)
                    with self.store.tx() as db:
                        db.execute("UPDATE email_outbox SET status='sent',sent_at=?,last_error=NULL WHERE id=?", (iso(),row["id"]))
                    sent += 1
                except (smtplib.SMTPResponseException, smtplib.SMTPRecipientsRefused, ConnectionRefusedError, ValueError) as exc:
                    delay = min(3600,60 * 2**row["attempts"])
                    with self.store.tx() as db:
                        db.execute("UPDATE email_outbox SET status='failed',next_attempt=?,last_error=? WHERE id=?", (iso(utcnow()+timedelta(seconds=delay)),redact(str(exc),self.config.secrets.values()),row["id"]))
                except Exception:
                    # SMTP can disconnect after accepting DATA. Human check prevents surprise duplicate notices.
                    with self.store.tx() as db:
                        if submission_started:
                            db.execute("UPDATE email_outbox SET status='uncertain',last_error='Delivery result is uncertain. Check the recipient inbox before retrying.' WHERE id=?", (row["id"],))
                        else:
                            delay = min(3600,60 * 2**row["attempts"])
                            db.execute("UPDATE email_outbox SET status='failed',next_attempt=?,last_error='Mail service could not be reached before sending. Will retry with backoff.' WHERE id=?", (iso(utcnow()+timedelta(seconds=delay)),row["id"]))
        finally:
            self.mail_lock.release()
        return sent

    def retry_email(self):
        with self.store.tx() as db:
            db.execute("UPDATE email_outbox SET status='pending',attempts=0,next_attempt=? WHERE status='failed'", (iso(),))
        return {"ok":True,"message":"Failed deliveries are ready to retry. Uncertain deliveries need inbox confirmation first."}

    def run(self):
        while not self.stop.wait(1):
            try:
                self.store.tick()
                if time.monotonic() - self.last_cycle >= 60:
                    self.last_cycle = time.monotonic()
                    self.check()
                    last = self.store.meta("last_backup")
                    if not last or (utcnow()-timestamp(last)).total_seconds() > 86400:
                        self.backup()
                    self.cleanup()
                    self.send_mail()
            except Exception as exc:
                logging.error("Housekeeping needs attention: %s", redact(str(exc),self.config.secrets.values()))
                try: self.store.issue("maintenance-failed", "error", "Housekeeping could not complete. Check the local service log and disk space.")
                except Exception: pass
