"""A narrow, bounded capability for display diagnostics, never administrator access."""
import re
import secrets
import time
from .store import iso, timestamp, utcnow

CODES = {
    'artwork-load': 'A display could not load local artwork; it retained the available painting.',
    'painting-timeout': 'A display timed out preparing a painting; it retained the previous artwork.',
    'render-failed': 'A display renderer failed. Reload the display after checking local assets.',
    'decoration-load': 'A display could not load a local atmosphere or status illustration.',
}


class DisplayReports:
    def __init__(self):
        self.tokens = {}
        self.accepted = []
        self.minted = []

    def issue(self):
        now = time.monotonic()
        self.tokens = {k: v for k, v in self.tokens.items() if v[0] > now}
        self.minted = [t for t in self.minted if now-t < 60]
        if len(self.tokens) >= 128 or len(self.minted) >= 30:
            return None
        token = secrets.token_urlsafe(32)
        self.tokens[token] = (now+3600, 0)
        self.minted.append(now)
        return token

    def receive(self, token, data, store):
        now = time.monotonic()
        expiry, count = self.tokens.get(token, (0, 0))
        if expiry <= now:
            raise PermissionError('Display reporting session expired')
        if set(data) != {'report_id', 'code', 'view', 'bird', 'observed_at'}:
            raise ValueError('Only fixed display diagnostic fields are accepted')
        rid, code, view, bird = (data.get(k) for k in ('report_id', 'code', 'view', 'bird'))
        if not isinstance(rid, str) or not re.fullmatch(r'[a-f0-9-]{36}', rid):
            raise ValueError('Invalid display report identifier')
        if not isinstance(code, str) or code not in CODES or view not in ('branch', 'portrait'):
            raise ValueError('Unknown display diagnostic')
        from .branch import catalogue
        if bird is not None and (not isinstance(bird, str) or bird not in {b['id'] for b in catalogue()}):
            raise ValueError('Unknown bird')
        when = timestamp(data.get('observed_at'))
        age = (utcnow()-when).total_seconds()
        if not -300 <= age <= 7*86400:
            raise ValueError('Display report outside retention window')
        # A lost acknowledgement must not consume another allowance or issue occurrence.
        report_id = 'display:'+rid
        if store.query('SELECT 1 FROM reports WHERE report_id=?', (report_id,)):
            return {'ok': True, 'duplicate': True}
        self.accepted = [t for t in self.accepted if now-t < 3600]
        if count >= 20 or len(self.accepted) >= 100:
            return None
        result = store.report({'report_id': report_id, 'station_id': 'display',
            'message': CODES[code], 'severity': 'warning',
            'details': {'component': view+':'+code, 'bird': bird, 'observed_at': iso(when)}})
        self.tokens[token] = (expiry, count+1)
        self.accepted.append(now)
        return result
