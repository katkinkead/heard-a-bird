"""Durable observed-time windows for commissioning audio, including delayed relay delivery."""
from datetime import timedelta
from .store import iso, timestamp, utcnow

KEY = 'commissioning_capture_windows'


def intervals(store):
    return [(timestamp(w['start']), timestamp(w['end'])) for w in store.meta(KEY, [])]


def contains(store, when):
    return any(lo <= when < hi for lo, hi in intervals(store))


def subtract(store, spans):
    for lo, hi in intervals(store):
        remaining = []
        for a, b in spans:
            if hi <= a or lo >= b:
                remaining.append((a, b))
            else:
                if a < lo: remaining.append((a, lo))
                if hi < b: remaining.append((hi, b))
        spans = remaining
    return spans


def status(store):
    now = utcnow()
    active = next((w for w in store.meta(KEY, []) if timestamp(w['start']) <= now < timestamp(w['end'])), None)
    return {'active': bool(active), 'until': active['end'] if active else None}


def action(store, data):
    if set(data) != {'action'} or data['action'] not in ('start', 'stop'):
        raise ValueError('Choose start or stop for the ten-minute capture test')
    with store.tx():
        now = utcnow()
        windows = store.meta(KEY, [])
        if data['action'] == 'start':
            if status(store)['active']: return status(store)
            # Bound storage without discarding exclusions for buffered old reports.
            if len(windows) >= 4096: raise ValueError('Capture history is full; export it before maintenance')
            windows.append({'start': iso(now), 'end': iso(now+timedelta(minutes=10))})
        else:
            for w in windows:
                if timestamp(w['start']) <= now < timestamp(w['end']): w['end'] = iso(now)
        store.set_meta(KEY, windows)
        store._seasonal_baseline = None
    return status(store)
