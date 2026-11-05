#!/usr/bin/env python3
"""Isolated cloud QA server and bounded browser observer; no external email/AI."""
import argparse,json,os,sys,threading,time,uuid,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from songsketch.simulation import SimulationApp, SimulationServer

def write(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2));os.replace(temp,path)
    if path.parent.name=="evidence":os.chmod(path,0o644)

def cgroup_memory_bytes():
    try:
        group=next(line.split(':',2)[2] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0:'))
        return int((Path('/sys/fs/cgroup')/group.lstrip('/')/'memory.current').read_text())
    except (OSError,ValueError,StopIteration):return 0

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--port',type=int,default=8768)
    p.add_argument('--duration-hours',type=float,default=24);p.add_argument('--public-url',required=True)
    a=p.parse_args()
    if not 0<a.duration_hours<=48:raise ValueError('Duration must be 0–48 hours')
    folder=a.run_dir;folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    evidence=folder/'evidence';evidence.mkdir(exist_ok=True,mode=0o755)
    planpath=folder/'plan.json'
    if planpath.exists():plan=json.loads(planpath.read_text())
    else:
        plan={'run_id':uuid.uuid4().hex,'started':time.time()+120,'duration_seconds':a.duration_hours*3600,'url':a.public_url,'synthetic':True}
        write(planpath,plan)
    app=SimulationApp(folder/'runtime');server=SimulationServer(('127.0.0.1',a.port),app)
    threading.Thread(target=server.serve_forever,daemon=True).start();app.start_ticks()
    write(evidence/'qa-marker.json',{'run_id':plan['run_id'],'synthetic':True})
    from songsketch.branch import catalogue
    write(folder/'station-config.json',{**plan,'token':app.config.secrets['station_token'],'species':[{k:b[k] for k in ('scientific_name','common_name')} for b in catalogue()]});os.chmod(folder/'station-config.json',0o600)
    reportpath=evidence/'report.json'
    report=json.loads(reportpath.read_text()) if reportpath.exists() else {'run_id':plan['run_id'],'started':plan['started'],'duration_seconds':plan['duration_seconds'],'frames':[],'findings':[],'limits':['Synthetic IDs from the physical Pi; no BirdNET/microphone recognition.','Practice Garden captures missing-art notices locally; real SMTP remains a separate pending check.','Time-lapse screenshots plus up to 12 short WebM clips; not a continuous day-long recording.','Automatic checks do not approve visual quality or edit production code.'],'external_email_sent':False}
    html='''<!doctype html><meta charset="utf-8"><title>Pepper’s rehearsal</title><style>body{font:17px system-ui;background:#f6f3ec;color:#26372c;max-width:1100px;margin:40px auto;padding:20px}img,video{width:100%}button,input{margin:8px}pre{white-space:pre-wrap}</style><h1>Pepper’s rehearsal</h1><p>Synthetic garden · physical Pi delivery · cloud browser capture</p><p id="summary">Loading…</p><button id="play">Play / pause</button><label>Frames/sec <input id="speed" type="number" min="1" max="12" value="2"></label><input id="seek" type="range" min="0" value="0"><p id="caption"></p><img id="shot"><h2>Screen recordings</h2><div id=videos></div><p><a href=qa-prd-coverage.json>PRD coverage</a> · <a href=regression-results.json>Software test results</a></p><h2>Findings and limits</h2><pre id="details"></pre><script>let r,i=0,playing=false;const el=id=>document.getElementById(id);function show(){let f=r.frames[i];if(!f)return;el('shot').src=f.file;el('seek').value=i;el('caption').textContent=new Date(f.at*1000).toLocaleString()+' · '+f.phase+' · observations '+f.observations}async function load(){r=await(await fetch('report.json',{cache:'no-store'})).json();el('summary').textContent=r.status+' · '+r.frames.length+' screenshots · '+r.findings.length+' findings';if(el('videos').dataset.count!==String((r.videos||[]).length)){el('videos').replaceChildren();for(const clip of (r.videos||[])){const label=document.createElement('p');label.textContent=new Date(clip.at*1000).toLocaleString()+' · '+clip.phase;const v=document.createElement('video');v.controls=true;v.preload='metadata';v.src=clip.file;el('videos').append(label,v)}el('videos').dataset.count=String((r.videos||[]).length)}el('seek').max=Math.max(0,r.frames.length-1);el('details').textContent=JSON.stringify({findings:r.findings,limits:r.limits,mail:r.mail},null,2);show()}el('seek').oninput=e=>{i=+e.target.value;show()};el('play').onclick=()=>playing=!playing;let last=0;setInterval(()=>{if(playing&&r&&Date.now()-last>1000/Math.max(1,+el('speed').value)){i=(i+1)%r.frames.length;show();last=Date.now()}},80);load();setInterval(load,30000)</script>'''
    (evidence/'index.html').write_text(html);os.chmod(evidence/'index.html',0o644)
    from playwright.sync_api import sync_playwright
    browser=None;context=None;page=None;repairs=0
    report.setdefault('videos',[])
    clips=evidence/'clips';clips.mkdir(exist_ok=True,mode=0o755);os.chmod(clips,0o755)
    storage_path=folder/'browser-state.json'
    storage=json.loads(storage_path.read_text()) if storage_path.exists() else None
    recording=False;video_at=0;video_phase=None;last_video_phase=None
    next_capture=0;last_memory_recycle=0
    report.setdefault('recovery_actions',[])
    def close_context():
        nonlocal context,page,storage,recording
        if context is None:return
        try:
            storage=context.storage_state();write(storage_path,storage);os.chmod(storage_path,0o600)
        except Exception:pass
        video=page.video if page and recording else None
        context.close()
        if video:
            path=Path(video.path());os.chmod(path,0o644)
            report['videos'].append({'file':'clips/'+path.name,'at':video_at,'phase':video_phase,'seconds':round(time.time()-video_at,1),'note':'Observer context reloads between clips; saved browser completion state is retained.'})
            write(reportpath,report)
        context=None;page=None;recording=False
    def finding(code,detail):
        if len(report['findings'])<100 and not any(x['code']==code and x['detail']==detail for x in report['findings']):report['findings'].append({'at':time.time(),'code':code,'detail':detail,'review_required':True,'next_check':{'browser-error':'Inspect the linked frame and browser stack before changing the renderer.','http-asset-error':'Check the asset path and proxy response; preserve approved artwork.','unexpected-pi-disconnect':'Check Pi power, Wi-Fi and station-state.json; do not reflash.','capture-failure-not-observed':'Compare sender phase and heartbeat timestamps.','observer-error':'Check browser/service logs and available memory; stop after bounded retries.'}.get(code,'Review the phase timeline and retained evidence before repair.')})
    report['limits']=[x for x in report['limits'] if x!='Screenshots are time-lapse evidence, not continuous video.']
    if not any('WebM' in x for x in report['limits']):report['limits'].append('Time-lapse screenshots plus up to 12 short WebM clips; not a continuous day-long recording.')
    try:
        with sync_playwright() as pw:
            while time.time()<plan['started']+plan['duration_seconds']:
                now=time.time();elapsed=now-plan['started'];minute=int(max(0,elapsed)//60)%20
                phase='offline' if 8<=minute<12 else 'capture-failed' if 5<=minute<7 else 'healthy'
                try:
                    memory=cgroup_memory_bytes()
                    if browser and memory>850_000_000 and now-last_memory_recycle>300:
                        close_context();browser.close();browser=None;last_memory_recycle=now
                        report['recovery_actions'].append({'at':now,'action':'recycle-qa-browser','reason':'QA cgroup memory above 850 MB','observed_bytes':memory})
                        report['recovery_actions']=report['recovery_actions'][-100:];write(reportpath,report)
                    if browser is None:
                        browser=pw.chromium.launch(headless=True,args=['--disable-dev-shm-usage'])
                    if context and recording and time.time()-video_at>=120:close_context()
                    want_video=len(report['videos'])<12 and phase!=last_video_phase
                    if context and not recording and want_video:close_context()
                    if context is None:
                        opts={'viewport':{'width':1280,'height':720}}
                        if storage:opts['storage_state']=storage
                        recording=want_video
                        if recording:
                            opts.update(record_video_dir=str(clips),record_video_size={'width':960,'height':540})
                            video_at=time.time();video_phase=phase;last_video_phase=phase
                        context=browser.new_context(**opts)
                        page=context.new_page();page.on('pageerror',lambda error:finding('browser-error',str(error)[:300]))
                        page.on('response',lambda response:finding('http-asset-error',response.url.split('?')[0]+' '+str(response.status)) if response.status>=400 else None)
                        page.goto(a.public_url+'/branch',wait_until='domcontentloaded');next_capture=0
                    if time.time()<next_capture:
                        time.sleep(max(0,min(5,next_capture-time.time())));continue
                    app.maintenance.send_mail()
                    from songsketch.branch import snapshot
                    state=snapshot(app.store);station=state['station']
                    # Allow actual heartbeat timeout and transition delivery latency.
                    in_cycle=max(0,elapsed)%1200
                    if elapsed>60 and 650<in_cycle<710 and station['connected']:finding('disconnect-not-observed','Pi remained connected after expected heartbeat expiry')
                    if elapsed>60 and (60<in_cycle<290 or 760<in_cycle<1150) and not station['connected']:finding('unexpected-pi-disconnect','No heartbeat during a scheduled online phase')
                    if 340<in_cycle<410 and station['listening']!='unavailable':finding('capture-failure-not-observed','Expected connected Pi with unavailable capture')
                    size=sum(f.stat().st_size for f in evidence.rglob('*') if f.is_file())
                    if size>500_000_000 or shutil.disk_usage(folder).free<2_000_000_000:
                        finding('capture-storage-limit','Capture paused at configured storage threshold');report['status']='blocked-storage';write(reportpath,report);break
                    name='frame-%05d.jpg'%len(report['frames']);page.screenshot(path=str(evidence/name),type='jpeg',quality=70);os.chmod(evidence/name,0o644)
                    browser_state=page.evaluate("""() => {
                        const s=window.branchDisplay?.getState();
                        const c=document.getElementById('garden');
                        let ink=0,samples=0;
                        if(c){const x=c.getContext('2d');for(let y=30;y<c.height;y+=60)for(let z=30;z<c.width;z+=80){const p=x.getImageData(z,y,1,1).data;samples++;if(Math.abs(p[0]-245)+Math.abs(p[1]-240)+Math.abs(p[2]-230)>18)ink++;}}
                        return {ready:!!s,view:document.getElementById('view')?.value,period:document.getElementById('period')?.value,shown:s?.shown?.length,done:s?.done?.length,queued:s?.queue?.length,active:s?.active,error:s?.error,server_species:s?.snapshot?.species,connection:document.getElementById('connection')?.textContent,canvas_ink_samples:ink,canvas_samples:samples};
                    }""")
                    if browser_state.get('server_species',0) and browser_state.get('shown',0) and browser_state.get('canvas_ink_samples',0)<3:
                        finding('blank-canvas-with-history','Canvas looks empty despite displayed history; inspect frame '+name+' and context reload timing. Product change requires review.')
                    if browser_state.get('error'):finding('display-reported-error',browser_state['error'][:300])
                    report['frames'].append({'file':name,'at':now,'phase':phase,'observations':state['observations'],'station':station,'browser':browser_state})
                    report['mail']=app.store.meta('simulation_mail',[])
                    report['status']='running';report['updated']=time.time();report['qa_memory_bytes']=memory;write(reportpath,report)
                    storage=context.storage_state();write(storage_path,storage);os.chmod(storage_path,0o600)
                    print(json.dumps({'frame':len(report['frames']),'phase':phase,'observations':state['observations'],'findings':len(report['findings'])}),flush=True)
                    # Early faults at 5–12 minutes are captured every 30 s; later 5 min.
                    next_capture=time.time()+(15 if recording else 30 if elapsed<900 else 300)
                    time.sleep(min(5,max(0,plan['started']+plan['duration_seconds']-time.time())))
                except Exception as exc:
                    finding('observer-error',type(exc).__name__+': '+str(exc)[:300]);report['status']='recovering';write(reportpath,report)
                    if browser:
                        try:close_context();browser.close()
                        except Exception:pass
                    browser=None;repairs+=1
                    if repairs>2:report['status']='blocked-browser';write(reportpath,report);break
                    time.sleep(5)
            else:
                report['status']='completed-with-findings' if report['findings'] else 'completed-awaiting-visual-review';report['finished']=time.time();write(reportpath,report)
            if browser:close_context();browser.close()
    finally:
        server.shutdown();server.server_close();app.close()
if __name__=='__main__':main()
