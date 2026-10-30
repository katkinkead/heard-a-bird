#!/usr/bin/env python3
"""Exercise the owned isolated server over HTTP, then optionally start its visible 75s show."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import http.client
import json
from pathlib import Path
import sys
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from songsketch.simulation import SimulationConfig, MODE, prepare_directory
from songsketch.store import iso, utcnow

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',required=True,type=Path)
    parser.add_argument('--port',type=int,default=8772)
    parser.add_argument('--report',required=True,type=Path)
    parser.add_argument('--reset-isolated',action='store_true',required=True)
    parser.add_argument('--start-show',action='store_true')
    args=parser.parse_args()
    if not (args.data_dir/'simulation.json').is_file():raise RuntimeError('An existing marked rehearsal is required')
    _,marker=prepare_directory(args.data_dir)
    def request(method,path,data=None,kind=None,extra=None,expect=200):
        headers=dict(extra or {})
        if kind:headers['Authorization']='Bearer '+config.secrets[kind+'_token']
        if data is not None:headers['Content-Type']='application/json'
        conn=http.client.HTTPConnection('127.0.0.1',args.port,timeout=20)
        try:
            conn.request(method,path,body=json.dumps(data) if data is not None else None,headers=headers)
            response=conn.getresponse();body=json.loads(response.read())
            if response.status!=expect:raise RuntimeError('Unexpected HTTP status at '+path+': '+str(response.status))
            return body
        finally:conn.close()
    health=request('GET','/health')
    if health.get('mode')!=MODE or health.get('data_id')!=marker['id']:
        raise RuntimeError('Refusing to alter a server that is not this isolated practice garden')
    config=SimulationConfig(args.data_dir)
    checks=[]
    def check(name,actual,expected=True):
        checks.append({'name':name,'actual':actual,'expected':expected,'passed':actual==expected})
        if actual!=expected:raise AssertionError(name)
    def act(action,id='robin'):
        return request('POST','/api/simulation/branch',{'action':action,'id':id},'admin')['state']
    def state():return request('GET','/api/branch/state')
    def event(name='Erithacus rubecula',when=None):return {'station_id':'garden','event_id':str(uuid.uuid4()),'scientific_name':name,'confidence':.98,'observed_at':iso(when or utcnow())}
    started=iso();completed=False
    try:
        act('reset');check('fresh first species',act('send')['species'],1)
        check('retry deduplicated',act('retry')['observations'],1)
        check('continuous matches remain one bout',act('send')['bouts'],1)
        # This fixture ages records and coverage; it is not a measured three-minute silence.
        check('new bout after fixture quiet gap',act('repeat')['bouts'],2)
        events=[event(n) for n in ['Turdus merula','Troglodytes troglodytes','Cyanistes caeruleus']]
        with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lambda e:request('POST','/api/ingest/detections',e,'station'),events))
        check('overlapping species retained',state()['species'],4)
        request('POST','/api/ingest/detections',event('Carduelis carduelis',utcnow()-timedelta(minutes=10)),'station')
        check('delayed arrival is not singing now',next(b for b in state()['birds'] if b['id']=='goldfinch')['live'],False)
        check('microphone failed with Pi connected',act('microphone')['station']['listening'],'unavailable')
        check('Pi heartbeat loss',act('disconnect')['station']['connected'],False)
        check('Pi recovery',act('connect')['station']['listening'],'available')
        before=state()['observations'];request('POST','/api/admin/capture-test',{'action':'start'},'admin')
        test=event('Unillustrated test species');check('test audio tagged',request('POST','/api/ingest/detections',test,'station')['commissioning_capture'])
        request('POST','/api/admin/capture-test',{'action':'stop'},'admin')
        test['event_id']=str(uuid.uuid4());check('buffered test tagged after stop',request('POST','/api/ingest/detections',test,'station')['test'])
        check('test sounds excluded from counts',state()['observations'],before)
        check('test sounds do not queue missing-art mail',len(request('GET','/api/admin/status',kind='admin')['notifications']),0)
        session=request('GET','/api/display/session',extra={'Sec-Fetch-Site':'same-origin'})
        diagnostic={'report_id':str(uuid.uuid4()),'code':'artwork-load','view':'branch','bird':'robin','observed_at':iso()}
        headers={'Sec-Fetch-Site':'same-origin','X-Display-Token':session['token']}
        request('POST','/api/display/reports',diagnostic,extra=headers)
        check('display retry deduplicated',request('POST','/api/display/reports',diagnostic,extra=headers)['duplicate'])
        check('display fault appears on Garden desk',any('display could not load' in i['message'] for i in request('GET','/api/admin/status',kind='admin')['issues']))
        check('station authentication required','error' in request('POST','/api/ingest/detections',event(),expect=401))
        check('all approved species available',act('all')['species'],45)
        check('solar computation available',state()['solar']['available'])
        for period in ['day','week','month']:check(period+' view retains all species',request('GET','/api/branch/state?period='+period)['species'],45)
        act('reset')
        if args.start_show:check('normal-speed visible sequence started',act('flow-start')['rehearsal_flow']['running'])
        completed=True
    finally:
        result={'started':started,'finished':iso(),'simulation':True,'hardware_verified':False,'real_birdnet_run':False,'external_messages_sent':False,'checks':checks,'passed':completed and bool(checks) and all(c['passed'] for c in checks),'limits':['Synthetic species IDs over authenticated HTTP.','Repeat-bout and heartbeat-loss scenarios use explicit clock-age fixtures.','Painting appearance is verified separately in the browser.']}
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'checks':len(checks),'show_started':args.start_show}))
if __name__=='__main__':main()
