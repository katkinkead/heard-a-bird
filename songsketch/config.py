"""Portable configuration. Secrets live outside the checkout, never in exports."""
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import tempfile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = {
    "site_name": "Our little patch", "timezone": "Europe/London",
    "profile": "mac-mvp", "confidence_threshold": 0.7,
    "display_cooldown_seconds": 600, "heartbeat_timeout_seconds": 150,
    "painting_seconds": 75, "hold_seconds": 20, "station_id": "garden",
    "notification_email": "", "smtp_host": "", "smtp_port": 587,
    "smtp_user": "", "smtp_from": "", "smtp_tls": True,
    "ai_text_model": "gpt-5.5", "ai_image_model": "gpt-image-2.5-flare",
    "ai_daily_job_limit": 3, "detection_retention_days": 730,
}
SECRET_FIELDS = {"admin_token", "station_token", "smtp_password", "openai_api_key"}

def data_directory():
    if os.environ.get("SONGSKETCH_DATA_DIR"):
        return Path(os.environ["SONGSKETCH_DATA_DIR"]).expanduser().resolve()
    base = Path.home() / ("Library/Application Support" if sys.platform == "darwin" else ".local/share")
    return base / "Songsketch"

def private_json(path, value):
    path = Path(path)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=str(path.parent))
    tmp = Path(tmp_name)
    with os.fdopen(fd, "w") as f:
        json.dump(value, f, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    os.chmod(path, 0o600)

class Config:
    def __init__(self, directory=None):
        self.lock = threading.RLock()
        self.directory = Path(directory or data_directory())
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        self.values = dict(DEFAULTS)
        p = self.directory / "config.json"
        if p.exists():
            self.values.update(json.loads(p.read_text()))
        ZoneInfo(self.values["timezone"])
        sp = self.directory / "secrets.json"
        self.secrets = json.loads(sp.read_text()) if sp.exists() else {}
        needs_secrets = not all(k in self.secrets for k in ("admin_token", "station_token"))
        self.secrets.setdefault("admin_token", secrets.token_urlsafe(32))
        self.secrets.setdefault("station_token", secrets.token_urlsafe(32))
        if needs_secrets:
            private_json(sp, self.secrets)
        os.chmod(sp, 0o600)
        if not p.exists():
            private_json(p, self.values)

    def public(self):
        d = dict(self.values)
        d["email_configured"] = bool(d["smtp_host"] and d["smtp_from"] and d["notification_email"])
        d["ai_configured"] = bool(self.secrets.get("openai_api_key"))
        return d

    def update(self, patch):
        with self.lock:
            return self._update(patch)

    def _update(self, patch):
        values, credentials = dict(self.values), dict(self.secrets)
        for key, value in patch.items():
            if key in {"smtp_password", "openai_api_key"}:
                if not isinstance(value, str) or len(value) > 4096:
                    raise ValueError("Invalid credential")
                # Blank means leave saved secret; explicit null is not accepted.
                if value:
                    credentials[key] = value.strip()
            elif key == "remove_ai_key" and value is True:
                credentials.pop("openai_api_key", None)
            elif key == "remove_smtp_password" and value is True:
                credentials.pop("smtp_password", None)
            elif key in DEFAULTS:
                values[key] = value
            else:
                raise ValueError("Unknown setting: " + key)
        for k in ["site_name", "timezone", "notification_email", "smtp_host", "smtp_user", "smtp_from", "ai_text_model", "ai_image_model", "station_id", "profile"]:
            if not isinstance(values[k], str) or len(values[k]) > 200 or any(c in values[k] for c in "\r\n\x00"):
                raise ValueError("Invalid " + k)
        ZoneInfo(values["timezone"])
        for k, low, high in [("confidence_threshold", 0, 1), ("display_cooldown_seconds", 0, 86400), ("heartbeat_timeout_seconds", 30, 600), ("hold_seconds", 0, 600), ("smtp_port", 1, 65535), ("ai_daily_job_limit", 1, 20), ("detection_retention_days", 30, 3650)]:
            if isinstance(values[k], bool) or not isinstance(values[k], (int, float)) or not low <= values[k] <= high:
                raise ValueError("Invalid " + k)
        for key in ("notification_email", "smtp_from"):
            if values[key] and ("@" not in values[key] or " " in values[key]):
                raise ValueError("Enter an email address for " + key)
        if not isinstance(values["smtp_tls"], bool):
            raise ValueError("smtp_tls must be true or false")
        if values["profile"] not in ("mac-mvp", "linux-production"):
            raise ValueError("Unknown profile")
        values["painting_seconds"] = 75
        private_json(self.directory / "config.json", values)
        private_json(self.directory / "secrets.json", credentials)
        self.values, self.secrets = values, credentials
        return self.public()
