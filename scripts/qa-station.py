#!/usr/bin/env python3
"""Bounded synthetic station. Run on Pi; never opens audio or changes networking."""
import argparse, datetime, json, os, time, urllib.request
from pathlib import Path

def phase(elapsed):
    minute = int(elapsed // 60) % 20
    return 'offline' if 8 <= minute < 12 else 'capture-failed' if 5 <= minute < 7 else 'healthy'

def save(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value)); os.chmod(temp, 0o600); os.replace(temp, path)

def request(config, route, data=None):
    headers = {'Content-Type':'application/json'}
    if data is not None: headers['Authorization'] = 'Bearer ' + config['token']
    req = urllib.request.Request(config['url'] + route, data=None if data is None else json.dumps(data).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=15) as response: return json.load(response)

def deliver_pending(config, state, statepath):
    for _ in range(min(20,len(state['pending']))):
        event=state['pending'][0]; ack=request(config,'/api/ingest/detections',event)
        if ack.get('ok') is not True or ack.get('id')!=event['event_id']: raise ValueError('Acknowledgement mismatch')
        state['accepted']+=1;state['duplicate_acks']+=int(ack.get('duplicate',False));state['pending'].pop(0);save(statepath,state)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--config',required=True,type=Path); a=p.parse_args()
    c=json.loads(a.config.read_text())
    if not c['url'].startswith('https://'): raise ValueError('HTTPS required')
    if request(c,'/qa-marker.json').get('run_id') != c['run_id']: raise ValueError('QA identity mismatch; refusing delivery')
    statepath=a.config.parent/'station-state.json'
    state=json.loads(statepath.read_text()) if statepath.exists() else {'next':0,'pending':[],'accepted':0,'duplicate_acks':0,'errors':0}
    start=c['started']; end=start+c['duration_seconds']; next_heartbeat=0
    species=[('Erithacus rubecula','Robin'),('Erithacus rubecula','Robin'),('Cyanistes caeruleus','Blue tit'),('Songsketch qa_species','[TEST] Pepper rehearsal visitor'),('Songsketch qa_species','[TEST] Pepper rehearsal visitor'),('Troglodytes troglodytes','Wren'),('Carduelis carduelis','Goldfinch')]
    while time.time()<end:
        now=time.time(); elapsed=now-start
        if elapsed<0: time.sleep(min(5,-elapsed)); continue
        while state['next']*60 <= elapsed and state['next']*60<c['duration_seconds']:
            i=state['next']
            catalogue=c.get('species',[])
            if i>=20 and catalogue:
                bird=catalogue[(i-20)%len(catalogue)];scientific,common=bird['scientific_name'],bird['common_name']
            else:scientific,common=species[i%len(species)]
            event={'station_id':'garden','event_id':c['run_id']+'-'+str(i),'scientific_name':scientific,'common_name':common,'confidence':.4 if i%20==15 else .98,'observed_at':datetime.datetime.fromtimestamp(start+i*60,datetime.timezone.utc).isoformat(),'test':False}
            state['pending'].append(event)
            if i%20==1: state['pending'].append(dict(event))
            state['next']+=1
        save(statepath,state) # Persist before any delivery; retry exact IDs after a crash.
        if phase(elapsed)!='offline':
            try:
                if now>=next_heartbeat:
                    request(c,'/api/ingest/heartbeat',{'station_id':'garden','audio_status':'failed' if phase(elapsed)=='capture-failed' else 'healthy','inference_status':'healthy'})
                    next_heartbeat=now+20
                deliver_pending(c,state,statepath)
                state['last_success']=now
            except Exception as exc:
                state['errors']+=1;state['last_error_type']=type(exc).__name__ # Never serialize credentials or response bodies.
        state.update(phase=phase(elapsed),updated=now,simulation=True,hardware_capture_verified=False)
        save(statepath,state);time.sleep(5)
    state.update(finished=time.time(),complete=not state['pending']);save(statepath,state)
if __name__=='__main__':main()
