const assert=require('assert');
const Reporter=require('../static/display-reports.js');
(async()=>{
 let online=false,requests=[],timers=[],store=new Map(),n=0,now=Date.now();
 const storage={getItem:k=>store.get(k),setItem:(k,v)=>store.set(k,v)};
 const fetch=async(url,o={})=>{requests.push({url,o});if(!online)throw Error('offline');return {ok:true,status:200,json:async()=>({token:'scoped'})};};
 const args={fetch,storage,now:()=>now,uuid:()=>`00000000-0000-0000-0000-${String(++n).padStart(12,'0')}`,schedule:fn=>{timers.push(fn);return timers.length;}};
 let r=new Reporter(args);r.report('artwork-load','robin');r.report('artwork-load','robin');assert.equal(r.queue.length,1);
 const id=r.queue[0].report_id;await r.flush();assert.equal(r.queue.length,1);assert.equal(r.delay,4000);
 r=new Reporter(args);assert.equal(r.queue[0].report_id,id,'retry survives reload with same id');online=true;await r.flush();assert.equal(r.queue.length,0);assert.equal(JSON.parse(requests.at(-1).o.body).report_id,id);
 r.report('arbitrary');assert.equal(r.queue.length,0);
 for(let i=0;i<30;i++){now+=60001;r.report('artwork-load','robin');}assert.equal(r.queue.length,20);
 now+=8*86400000;await r.flush();assert.equal(r.queue.length,0,'expired reports discarded');
 const broken=new Reporter({...args,storage:{getItem(){throw Error()},setItem(){throw Error()}}});broken.report('render-failed');await broken.flush();assert.equal(broken.queue.length,0);
 let status=401;const retry=new Reporter({...args,fetch:async url=>url.endsWith('session')?{ok:true,json:async()=>({token:'fresh'})}:{ok:status===200,status}});
 retry.report('render-failed');await retry.flush();assert.equal(retry.token,null);assert.equal(retry.queue.length,1);status=200;await retry.flush();assert.equal(retry.queue.length,0);
 console.log('PASS: bounded offline retry, stable IDs, expiry, storage failure, renewed capability and fixed codes');
})().catch(e=>{console.error(e);process.exitCode=1});
