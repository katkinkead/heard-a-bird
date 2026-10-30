"""Versioned, sourced content and conservative seasonal garden comparisons."""
from datetime import timedelta
from functools import lru_cache
import json
import time
from zoneinfo import ZoneInfo
from .config import ROOT
from .store import timestamp, iso

RULE = 'seasonal-garden-v1'
MIN_DAYS = 30
MIN_HOURS_PER_DAY = 4
MAX_PREVIOUS_DAYS = 2

@lru_cache(maxsize=1)
def catalogue():
    path=ROOT/'artwork/branch/content.json'
    return json.loads(path.read_text()) if path.exists() else {'version':1,'birds':{}}

def coverage(store,start,end):
    """Only observed healthy spans count; stale heartbeat tails add no coverage."""
    rows=store.query('SELECT start_at,last_at FROM listening_windows WHERE last_at>=? AND start_at<=? ORDER BY start_at',(iso(start),iso(end)))
    intervals=[]
    for row in rows:
        lo=max(start,timestamp(row['start_at']));hi=min(end,timestamp(row['last_at']))
        if hi<=lo:continue
        if intervals and lo<=intervals[-1][1]:intervals[-1]=(intervals[-1][0],max(hi,intervals[-1][1]))
        else:intervals.append((lo,hi))
    from .capture_exclusion import subtract
    return subtract(store, intervals)

def baseline(store,now):
    zone=ZoneInfo(store.config.values['timezone']);today=now.astimezone(zone).replace(hour=0,minute=0,second=0,microsecond=0)
    cached=getattr(store,'_seasonal_baseline',None)
    floor=max(today-timedelta(days=730),now-timedelta(days=store.config.values['detection_retention_days']))
    pruned=store.meta('detection_history_floor')
    if pruned:floor=max(floor,timestamp(pruned))
    local_floor=floor.astimezone(zone)
    midnight=local_floor.replace(hour=0,minute=0,second=0,microsecond=0)
    if local_floor!=midnight:floor=midnight+timedelta(days=1)
    cache_key=(today.date(),store.config.values['timezone'],store.meta('branch_generation','garden'),store.config.values['detection_retention_days'],pruned)
    if cached and cached[0]==cache_key and time.monotonic()-cached[1]<30:return cached[2]
    days={}
    for lo,hi in coverage(store,floor,today):
        cursor=lo
        while cursor<hi:
            local=cursor.astimezone(zone);midnight=(local.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)).astimezone(cursor.tzinfo)
            stop=min(hi,midnight);day=local.date();days[day]=days.get(day,0)+(stop-cursor).total_seconds()/3600;cursor=stop
    observations=store.query('SELECT scientific_name,observed_at FROM detections WHERE test=0 AND qualifies=1 AND observed_at>=? AND observed_at<?',(iso(floor),iso(today)))
    by_species={}
    for r in observations:by_species.setdefault(r['scientific_name'].casefold(),set()).add(timestamp(r['observed_at']).astimezone(zone).date())
    result={'day':today.date(),'days':days,'observations':by_species}
    store._seasonal_baseline=(cache_key,time.monotonic(),result)
    return result

def decision(bird,record,history):
    season=record.get('season',{});months=season.get('months',[]);today=history['day'];in_season=today.month in months if months else None
    # Match the same part of the year; an empty summer is not a winter baseline.
    def comparable(day):
        if day.month not in months:return False
        a=day.replace(year=2000).timetuple().tm_yday;b=today.replace(year=2000).timetuple().tm_yday;delta=abs(a-b)
        return min(delta,366-delta)<=45
    valid={day for day,hours in history['days'].items() if hours>=MIN_HOURS_PER_DAY and comparable(day)}
    prior=history['observations'].get(bird['scientific_name'].casefold(),set())
    prior_days=len(prior&valid);enough=len(valid)>=MIN_DAYS
    unusual=bool(in_season and enough and prior_days<=MAX_PREVIOUS_DAYS)
    reason='Seasonal evidence not curated' if in_season is None else 'Outside the usual seasonal window; record retained' if not in_season else 'Seasonal baseline developing' if not enough else 'In season and infrequent in comparable garden history' if unusual else 'Regularly heard in comparable garden history'
    rare=record.get('regional',{})
    return {'rare':rare.get('eligible') is True,'regional':rare,'unusual':unusual,'unusual_reason':reason,'in_season':in_season,'season':season,'rule':RULE,'baseline_days':len(valid),'minimum_days':MIN_DAYS,'minimum_daily_hours':MIN_HOURS_PER_DAY,'prior_detection_days':prior_days,'maximum_prior_days':MAX_PREVIOUS_DAYS,'provisional':True}

def evidence(store,period='day',now=None):
    """Operator-only explanation of the same read model used by the artwork."""
    from .branch import snapshot
    from .store import utcnow
    now=now or utcnow();state=snapshot(store,period,now)
    start=timestamp(state['period_start']);spans=coverage(store,start,now)
    seconds=sum((hi-lo).total_seconds() for lo,hi in spans)
    elapsed=max(0,(now-start).total_seconds())
    lags=store.query('SELECT observed_at,received_at FROM detections WHERE test=0 AND qualifies=1 AND observed_at>=? AND observed_at<=? ORDER BY received_at DESC LIMIT 2000',(iso(start),iso(now)))
    values=sorted(max(0,(timestamp(r['received_at'])-timestamp(r['observed_at'])).total_seconds()) for r in lags)
    state['coverage'].update({'confirmed_hours':round(seconds/3600,2),'unconfirmed_hours':round(max(0,elapsed-seconds)/3600,2),'fraction':round(seconds/elapsed,4) if elapsed else 0})
    state['delivery']={'sample_size':len(values),'median_seconds':round(values[len(values)//2],1) if values else None,'p95_seconds':round(values[min(len(values)-1,int(len(values)*.95))],1) if values else None,'note':'Latest 2,000 accepted non-test records in this period; receive time minus observation time.'}
    records=catalogue().get('birds',{})
    state['library']={'species':len(records),'facts':sum(bool(b.get('facts')) for b in records.values()),'recordings':sum(b.get('audio',{}).get('available',False) for b in records.values()),'regional_candidates':sum(b.get('regional',{}).get('eligible',False) for b in records.values()),'note':'Regional evidence is dated; seasonal thresholds remain provisional. Audio still needs speaker/microphone feedback commissioning.'}
    return state
