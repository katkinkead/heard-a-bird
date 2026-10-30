"""Explicit simulation-only controls; every detection crosses authenticated HTTP ingress."""
from datetime import timedelta
import uuid
from .branch import catalogue, snapshot, boundaries
from .config import private_json
from .store import utcnow, iso, timestamp


def action(app, data):
    if not isinstance(data,dict) or set(data)-{'action','id','confidence'}: raise ValueError('Invalid branch rehearsal action')
    kind=data.get('action'); mapping={b['id']:b for b in catalogue()}
    with app.scenario_lock:
        if kind in ('flow-start','flow-stop'):
            app.store.set_meta('branch_flow',{'running':kind=='flow-start','started_at':iso(),'next':0})
            if kind=='flow-start':
                app.store.set_meta('branch_history_only',False)
                app.send_heartbeat()
        elif kind=='reset':
            app.reset_fixture(); app.send_heartbeat()
            # Synthetic Dorset coordinates; never overwrite the real installation.
            private_json(app.config.directory/'setup-details.json',{'latitude':50.75,'longitude':-2.3})
        elif kind in ('connect','microphone','recognition','disconnect'):
            if kind=='disconnect': app.age_heartbeat()
            else: app.send_heartbeat({'audio_status':'failed' if kind=='microphone' else 'healthy','inference_status':'failed' if kind=='recognition' else 'healthy'})
        elif kind in ('send','retry','repeat','chorus','all','history','unknown'):
            if kind=='retry':
                event=app.store.meta('branch_last_event')
                if not event: raise ValueError('Send a bird before retrying its message')
                response=app.local_ingest('detections',event)
                return {'result':response,'state':snapshot(app.store)}
            if kind in ('all','history'):
                app.reset_fixture();app.send_heartbeat()
                private_json(app.config.directory/'setup-details.json',{'latitude':50.75,'longitude':-2.3})
            if kind=='repeat':
                # An explicit lab clock-age fixture: retain all IDs but age observations
                # and healthy coverage so another bout can be tested without waiting.
                with app.store.tx() as db:
                    for r in db.execute('SELECT id,observed_at FROM detections').fetchall():
                        db.execute('UPDATE detections SET observed_at=? WHERE id=?',(iso(timestamp(r['observed_at'])-timedelta(seconds=181)),r['id']))
                    for r in db.execute('SELECT id,start_at,last_at FROM listening_windows').fetchall():
                        db.execute('UPDATE listening_windows SET start_at=?,last_at=? WHERE id=?',(iso(timestamp(r['start_at'])-timedelta(seconds=181)),iso(utcnow()),r['id']))
                app.send_heartbeat()
            chosen=[mapping[data.get('id')]] if data.get('id') in mapping else []
            if kind=='chorus': chosen=[mapping[k] for k in ['tawny-owl','robin','goldfinch','blue-tit','wren']]
            if kind in ('all','history'): chosen=list(mapping.values())
            if kind=='unknown': chosen=[{'scientific_name':'Songsketch qa_species','common_name':'Unillustrated practice visitor'}]
            if not chosen: raise ValueError('Choose a species in the branch catalogue')
            sent=[];now=utcnow();app.store.set_meta('branch_history_only',kind in ('all','history'))
            for i,b in enumerate(chosen):
                when=now
                if kind=='all':
                    start,_=boundaries('day',now,app.config.values['timezone']);span=min(5400,max(1,(now-start).total_seconds()-1));when=now-timedelta(seconds=span*(1-i/max(1,len(chosen))))
                if kind=='history': when=now-timedelta(days=(i%10),minutes=50-i)
                event={'station_id':app.config.values['station_id'],'event_id':'branch-lab-'+uuid.uuid4().hex,'scientific_name':b['scientific_name'],'common_name':b['common_name'],'confidence':data.get('confidence',.96),'observed_at':iso(when),'test':False}
                sent.append(app.local_ingest('detections',event));app.store.set_meta('branch_last_event',event)
            app.maintenance.send_mail()
            result={'sent':len(sent),'responses':sent,'fixture_age_seconds':181 if kind=='repeat' else 0}
            app.store.set_meta('branch_last_action',{'action':kind,'at':iso(),'result':result})
        else: raise ValueError('Unknown branch rehearsal action')
        return {'simulation':True,'state':snapshot(app.store),'last_action':app.store.meta('branch_last_action')}


def flow_status(app):
    return app.store.meta('branch_flow', {'running':False})


def advance_flow(app, now=None):
    """Bounded rehearsal through the same ingress; never external BirdNET or mail."""
    flow=flow_status(app)
    if not flow.get('running'): return
    now=now or utcnow()
    elapsed=(now-timestamp(flow['started_at'])).total_seconds()
    species=['tawny-owl','robin','goldfinch','blue-tit','wren']
    schedule=[(i*90+j*20,b) for i,b in enumerate(species) for j in range(5)]
    index=flow.get('next',0)
    if index>=len(schedule):
        flow['running']=False;app.store.set_meta('branch_flow',flow);return
    delay,id=schedule[index]
    if elapsed<delay:return
    b=next(b for b in catalogue() if b['id']==id)
    event={'station_id':app.config.values['station_id'],'event_id':'branch-flow-'+flow['started_at']+'-'+str(index),'scientific_name':b['scientific_name'],'common_name':b['common_name'],'confidence':.96,'observed_at':iso(now),'test':False}
    app.local_ingest('detections',event)
    flow['next']=index+1;flow['running']=flow['next']<len(schedule)
    app.store.set_meta('branch_flow',flow)
