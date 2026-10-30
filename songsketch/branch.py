"""Read model for the shared garden display. Raw observations remain authoritative."""
from collections import defaultdict
from datetime import timedelta
from functools import lru_cache
import json
import hashlib
from zoneinfo import ZoneInfo
from .config import ROOT
from .store import iso, timestamp, utcnow

LIVE_SECONDS = 60
BOUT_GAP = 120
RULE = 'branch-bouts-v1-coverage-aware'

@lru_cache(maxsize=1)
def catalogue():
    p = ROOT / 'artwork/branch/manifest.json'
    return json.loads(p.read_text())['birds'] if p.exists() else []

def boundaries(period, now, zone):
    if period not in ('day', 'week', 'month'): raise ValueError('Choose day, week or month')
    local = now.astimezone(ZoneInfo(zone))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == 'week': start -= timedelta(days=start.weekday())
    if period == 'month': start = start.replace(day=1)
    return start, local

def record_health(db, data, now, timeout):
    healthy = data.get('audio_status') == data.get('inference_status') == 'healthy'
    last = db.execute('SELECT * FROM listening_windows ORDER BY id DESC LIMIT 1').fetchone()
    if healthy:
        if last and last['open'] and (now-timestamp(last['last_at'])).total_seconds() <= timeout:
            db.execute('UPDATE listening_windows SET last_at=? WHERE id=?', (iso(now),last['id']))
        else:
            db.execute('UPDATE listening_windows SET open=0 WHERE open=1')
            db.execute('INSERT INTO listening_windows(start_at,last_at,open) VALUES (?,?,1)',(iso(now),iso(now)))
    else:
        db.execute('UPDATE listening_windows SET open=0 WHERE open=1')

@lru_cache(maxsize=2048)
def solar(day, zone, lat, lon):
    if lat is None or lon is None: return {'available':False,'reason':'Garden location not configured'}
    try:
        from astral import Observer
        from astral.sun import sun
        events = sun(Observer(float(lat),float(lon)), date=day, tzinfo=ZoneInfo(zone))
        return {'available':True, **{k:iso(v) for k,v in events.items()}}
    except (ImportError, ValueError, TypeError) as exc:
        return {'available':False,'reason':'Local solar calculation unavailable: '+type(exc).__name__}

def location(store):
    # Existing setup details are already validated by the commissioning service.
    p = store.config.directory / 'setup-details.json'
    try:
        data=json.loads(p.read_text()) if p.is_file() else {}
        return data.get('latitude'),data.get('longitude')
    except (ValueError,OSError): return None,None

def snapshot(store, period='day', now=None):
    now = now or utcnow(); zone=store.config.values['timezone']; start,_=boundaries(period,now,zone)
    birds=catalogue(); names={n.casefold():b for b in birds for n in [b['scientific_name'],b['common_name'],*b.get('aliases',[])]}
    # One day of lookback preserves a bout crossing a period boundary. A gap
    # without listening coverage never becomes proven quiet simply by absence.
    rows=store.query('SELECT * FROM detections WHERE test=0 AND qualifies=1 AND observed_at>=? AND observed_at<=? ORDER BY observed_at,id',(iso(start-timedelta(days=1)),iso(now)))
    health=store.station_status(); windows=store.query('SELECT * FROM listening_windows WHERE last_at>=? ORDER BY start_at',(iso(start-timedelta(days=1)),))
    intervals=[(timestamp(w['start_at']),now if w['open'] and health['listening']=='available' else timestamp(w['last_at'])) for w in windows]
    from .capture_exclusion import subtract
    intervals = subtract(store, intervals)
    def covered(a,b): return any(lo<=a and hi>=b for lo,hi in intervals)
    groups=defaultdict(list)
    for r in rows:
        b=names.get(r['scientific_name'].casefold()) or names.get(r['common_name'].casefold())
        key=b['id'] if b else 'unknown:'+r['scientific_name']
        groups[key].append((r,b))
    result=[]
    from .bird_content import catalogue as content_catalogue, baseline, decision
    content=content_catalogue();history=baseline(store,now)
    lat,lon=location(store)
    for key, records in groups.items():
        selected=[r for r,b in records if timestamp(r['observed_at'])>=start]
        if not selected: continue
        bouts=[]; uncertain=False; prev=None
        for r,b in records:
            at=timestamp(r['observed_at'])
            if prev is None: bouts.append([])
            elif (at-prev).total_seconds()>=BOUT_GAP:
                if covered(prev,at): bouts.append([])
                else: uncertain=True
            bouts[-1].append(r);prev=at
        count=sum(any(timestamp(r['observed_at'])>=start for r in bout) for bout in bouts)
        b=records[-1][1];first,last=selected[0],selected[-1];observed=timestamp(last['observed_at']);age=(now-observed).total_seconds()
        events=solar(timestamp(first['observed_at']).astimezone(ZoneInfo(zone)).date(),zone,lat,lon)
        phase='daytime'
        if events['available']:
            at=timestamp(first['observed_at']);rise=timestamp(events['sunrise']);setting=timestamp(events['sunset'])
            phase='night' if at<timestamp(events['dawn']) or at>timestamp(events['dusk']) else 'sunrise' if at<rise+timedelta(minutes=50) else 'sunset' if at>setting-timedelta(minutes=50) else 'daytime'
        bout=bouts[-1];bout_id=hashlib.sha256((bout[0]['station_id']+':'+bout[0]['event_id']).encode()).hexdigest()[:24]
        details=content.get('birds',{}).get(b['id'] if b else '',{})
        assessment=decision({'scientific_name':last['scientific_name']},details,history)
        result.append({'content':details,'assessment':assessment,'latest_bout':{'id':bout_id,'started_at':bout[0]['observed_at'],'last_at':bout[-1]['observed_at']},'id':b['id'] if b else None,'scientific_name':last['scientific_name'],'name':b['common_name'] if b else last['common_name'],'count':count,'observations':len(selected),'first_heard':first['observed_at'],'last_heard':last['observed_at'],'last_received':last['received_at'],'live_until':iso(observed+timedelta(seconds=LIVE_SECONDS)), 'live':health['listening']=='available' and 0<=age<LIVE_SECONDS,'count_uncertain':uncertain,'atmosphere':phase,'sunrise':events.get('sunrise'),'art_ready':bool(b)})
    result.sort(key=lambda b:(b['first_heard'],b['scientific_name']))
    return {'version':1,'rule':RULE,'server_now':iso(now),'period':period,'period_key':period+':'+start.date().isoformat(),'period_start':iso(start),'timezone':zone,'birds':result,'species':len(result),'bouts':sum(b['count'] for b in result),'observations':sum(b['observations'] for b in result),'count_uncertain':any(b['count_uncertain'] for b in result),'station':health,'simulation':bool(store.meta('simulation',False)),'generation':store.meta('branch_generation','garden'),'rehearsal_history':bool(store.meta('branch_history_only',False)),'rehearsal_flow':store.meta('branch_flow',{'running':False}) if store.meta('simulation',False) else None,'timing':{'live_seconds':LIVE_SECONDS,'bout_gap_seconds':BOUT_GAP,'painting_seconds':75,'provisional':True},'solar':solar(now.astimezone(ZoneInfo(zone)).date(),zone,lat,lon),'coverage':{'windows':len(windows),'note':'Only confirmed healthy intervals separate bouts; gaps leave counts uncertain.'}}
