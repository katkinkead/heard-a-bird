#!/usr/bin/env python3
"""Isolated cloud QA server and bounded browser observer; no external email/AI."""
import argparse,json,os,sys,threading,time,uuid,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from songsketch.simulation import SimulationApp, SimulationServer

def write(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2));os.replace(temp,path)
    if path.parent.name=="evidence":os.chmod(path,0o644)

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
    write(folder/'station-config.json',{**plan,'token':app.config.secrets['station_token']});os.chmod(folder/'station-config.json',0o600)
    reportpath=evidence/'report.json'
    report=json.loads(reportpath.read_text()) if reportpath.exists() else {'run_id':plan['run_id'],'started':plan['started'],'duration_seconds':plan['duration_seconds'],'frames':[],'findings':[],'limits':['Synthetic IDs from the physical Pi; no BirdNET/microphone recognition.','Practice Garden captures missing-art notices locally; real SMTP remains a separate pending check.','Screenshots are time-lapse evidence, not continuous video.','Automatic checks do not approve visual quality or edit production code.'],'external_email_sent':False}
    html='''<!doctype html><meta charset="utf-8"><title>Pepper’s rehearsal</title><style>body{font:17px system-ui;background:#f6f3ec;color:#26372c;max-width:1100px;margin:40px auto;padding:20px}img,video{width:100%}button,input{margin:8px}pre{white-space:pre-wrap}</style><h1>Pepper’s rehearsal</h1><p>Synthetic garden · physical Pi delivery · cloud browser capture</p><p id="summary">Loading…</p><button id="play">Play / pause</button><label>Frames/sec <input id="speed" type="number" min="1" max="12" value="2"></label><input id="seek" type="range" min="0" value="0"><p id="caption"></p><img id="shot"><h2>Findings and limits</h2><pre id="details"></pre><script>let r,i=0,playing=false;const el=id=>document.getElementById(id);function show(){let f=r.frames[i];if(!f)return;el('shot').src=f.file;el('seek').value=i;el('caption').textContent=new Date(f.at*1000).toLocaleString()+' · '+f.phase+' · observations '+f.observations}async function load(){r=await(await fetch('report.json',{cache:'no-store'})).json();el('summary').textContent=r.status+' · '+r.frames.length+' screenshots · '+r.findings.length+' findings';el('seek').max=Math.max(0,r.frames.length-1);el('details').textContent=JSON.stringify({findings:r.findings,limits:r.limits,mail:r.mail},null,2);show()}el('seek').oninput=e=>{i=+e.target.value;show()};el('play').onclick=()=>playing=!playing;let last=0;setInterval(()=>{if(playing&&r&&Date.now()-last>1000/Math.max(1,+el('speed').value)){i=(i+1)%r.frames.length;show();last=Date.now()}},80);load();setInterval(load,30000)</script>'''
    (evidence/'index.html').write_text(html);os.chmod(evidence/'index.html',0o644)
    from playwright.sync_api import sync_playwright
    browser=None;context=None;page=None;repairs=0
    def finding(code,detail):
        if len(report['findings'])<100 and not any(x['code']==code and x['detail']==detail for x in report['findings']):report['findings'].append({'at':time.time(),'code':code,'detail':detail,'review_required':True,'next_check':{'browser-error':'Inspect the linked frame and browser stack before changing the renderer.','http-asset-error':'Check the asset path and proxy response; preserve approved artwork.','unexpected-pi-disconnect':'Check Pi power, Wi-Fi and station-state.json; do not reflash.','capture-failure-not-observed':'Compare sender phase and heartbeat timestamps.','observer-error':'Check browser/service logs and available memory; stop after bounded retries.'}.get(code,'Review the phase timeline and retained evidence before repair.')})
    try:
        with sync_playwright() as pw:
            while time.time()<plan['started']+plan['duration_seconds']:
                now=time.time();elapsed=now-plan['started'];minute=int(max(0,elapsed)//60)%20
                phase='offline' if 8<=minute<12 else 'capture-failed' if 5<=minute<7 else 'healthy'
                try:
                    if browser is None:
                        browser=pw.chromium.launch(headless=True,args=['--disable-dev-shm-usage'])
                        context=browser.new_context(viewport={'width':1440,'height':900})
                        page=context.new_page();page.on('pageerror',lambda error:finding('browser-error',str(error)[:300]))
                        page.on('response',lambda response:finding('http-asset-error',response.url.split('?')[0]+' '+str(response.status)) if response.status>=400 else None)
                        page.goto(a.public_url+'/branch',wait_until='domcontentloaded')
                    app.maintenance.send_mail()
                    from songsketch.branch import snapshot
                    state=snapshot(app.store);station=state['station']
                    # Allow actual heartbeat timeout and transition delivery latency.
                    in_cycle=max(0,elapsed)%1200
                    if elapsed>60 and 650<in_cycle<710 and station['connected']:finding('disconnect-not-observed','Pi remained connected after expected heartbeat expiry')
                    if elapsed>60 and (60<in_cycle<290 or 760<in_cycle<1150) and not station['connected']:finding('unexpected-pi-disconnect','No heartbeat during a scheduled online phase')
                    if 340<in_cycle<410 and station['listening']!='unavailable':finding('capture-failure-not-observed','Expected connected Pi with unavailable capture')
                    size=sum(f.stat().st_size for f in evidence.iterdir() if f.is_file())
                    if size>500_000_000 or shutil.disk_usage(folder).free<2_000_000_000:
                        finding('capture-storage-limit','Capture paused at configured storage threshold');report['status']='blocked-storage';write(reportpath,report);break
                    name='frame-%05d.jpg'%len(report['frames']);page.screenshot(path=str(evidence/name),type='jpeg',quality=70);os.chmod(evidence/name,0o644)
                    report['frames'].append({'file':name,'at':now,'phase':phase,'observations':state['observations'],'station':station})
                    report['mail']=app.store.meta('simulation_mail',[])
                    report['status']='running';report['updated']=time.time();write(reportpath,report)
                    print(json.dumps({'frame':len(report['frames']),'phase':phase,'observations':state['observations'],'findings':len(report['findings'])}),flush=True)
                    # Early faults at 5–12 minutes are captured every 30 s; later 5 min.
                    time.sleep(min(30 if elapsed<900 else 300,max(0,plan['started']+plan['duration_seconds']-time.time())))
                except Exception as exc:
                    finding('observer-error',type(exc).__name__+': '+str(exc)[:300]);report['status']='recovering';write(reportpath,report)
                    if browser:
                        try:browser.close()
                        except Exception:pass
                    browser=None;repairs+=1
                    if repairs>2:report['status']='blocked-browser';write(reportpath,report);break
                    time.sleep(5)
            else:
                report['status']='completed-with-findings' if report['findings'] else 'completed-awaiting-visual-review';report['finished']=time.time();write(reportpath,report)
            if browser:browser.close()
    finally:
        server.shutdown();server.server_close();app.close()
if __name__=='__main__':main()
