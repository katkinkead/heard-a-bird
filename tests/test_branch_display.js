/* Exercise the real display controller against delayed local artwork and changing
   server snapshots. Canvas is a no-op: visual checks are separate browser work. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const root=require('path').resolve(__dirname,'..');
async function main(){let now=1000, raf, timers=[],resolvePainter,creations=0,texts=[],imagesDrawn=[],data={period:'day',period_key:'day:2026-10-22',generation:'test',server_now:new Date(Date.now()+1000).toISOString(),station:{connected:true,listening:'available'},simulation:true,species:1,bouts:1,observations:1,birds:[{id:'robin',name:'Robin',scientific_name:'Erithacus rubecula',count:1,observations:1,last_heard:new Date().toISOString(),live_until:new Date(Date.now()+60000).toISOString(),live:true,art_ready:true,atmosphere:'daytime'}]};
 const store=new Map(),controls=new Map(),context=new Proxy({measureText(s){return {width:s.length*10}},fillText(s){texts.push(s)},drawImage(im){imagesDrawn.push(im?.source||'')},createLinearGradient(){return{addColorStop(){}};}},{get:(o,k)=>k in o?o[k]:()=>{},set:(o,k,v)=>(o[k]=v,true)}),canvas=()=>({width:1920,height:1080,getContext:()=>context});
 const get=id=>{if(!controls.has(id))controls.set(id,id==='garden'?canvas():{value:'',textContent:'',hidden:true});return controls.get(id);};
 const g={window:null,document:{getElementById:get,createElement:canvas,documentElement:{requestFullscreen(){}},exitFullscreen(){}},localStorage:{getItem:k=>store.get(k),setItem:(k,v)=>store.set(k,v)},performance:{now:()=>now},console,Date,Intl,Promise,Map,Set,Math,JSON,fetch:async()=>({ok:true,json:async()=>JSON.parse(JSON.stringify(data))}),setTimeout:f=>{timers.push(f)},requestAnimationFrame:f=>{raf=f},decodeBirdsongImage:async source=>({source,width:1920,height:1080}),loadBirdsongAsset:async id=>({id}),createBirdsongPainter:async()=>{creations++;return new Promise(r=>{resolvePainter=r})}};g.window=g;vm.createContext(g);
 for(const f of ['artwork/branch/product/branch-motion/registrations.js','static/branch-layout.js','artwork/branch/branch-screen/runtime/branch-ink.js'])vm.runInContext(fs.readFileSync(root+'/'+f,'utf8'),g);
 await vm.runInContext(fs.readFileSync(root+'/static/branch.js','utf8'),g);const settle=()=>new Promise(r=>setImmediate(r));await settle();
 assert.equal(creations,1);for(let i=0;i<4;i++){timers.shift()();await settle();}assert.equal(g.branchDisplay.getState().queue.length,0,'slow load must not enqueue duplicates');
 resolvePainter({birdCanvas:canvas(),renderAt(){}});await settle();texts=[];now+=150;raf(now);assert(texts.includes('Singing now'),'fresh activity must be visible while the bird is still painting');assert(!g.branchDisplay.getState().done.includes('robin'));g.branchDisplay.setSpeed(8);for(let i=0;i<66;i++){now+=150;raf(now);}await settle();assert.deepEqual([...g.branchDisplay.getState().done],['robin']);assert.equal(creations,1);
 data.birds[0].count=2;data.bouts=2;timers.shift()();await settle();texts=[];now+=2000;raf(now);assert(texts.some(s=>s.includes('Heard 2 times')),'repeat count must update existing caption');assert.equal(creations,1,'repeat must not repaint');
 // Status assets must keep their approved meanings; a decorative feather is not interchangeable.
 data.birds[0].assessment={unusual:true,rare:false};timers.shift()();await settle();imagesDrawn=[];texts=[];now+=100;raf(now);
 assert(imagesDrawn.some(p=>p.endsWith('/symbols/unusual-visitor-v2.png')),'garden-unusual uses the approved iridescent feather');
 assert(!imagesDrawn.some(p=>p.endsWith('/symbols/rare-v2.png')),'garden-unusual must not become regional rarity');
 assert(imagesDrawn.some(p=>p.endsWith('/symbols/singing-now.png')),'live mark uses the approved perspective ripple');
 data.birds[0].assessment={unusual:false,rare:true};timers.shift()();await settle();imagesDrawn=[];now+=100;raf(now);
 assert(imagesDrawn.some(p=>p.endsWith('/symbols/rare-v2.png')),'regional rarity uses its separate gold feather');
 assert(!imagesDrawn.some(p=>p.endsWith('/symbols/unusual-visitor-v2.png')));
 data.station.listening='unavailable';timers.shift()();await settle();texts=[];now+=100;raf(now);assert(!texts.includes('Singing now'),'unhealthy listening hides live labels');
 data.station.listening='available';timers.shift()();await settle();texts=[];now+=6100;raf(now);assert(!texts.includes('Singing now'),'stale server snapshots cannot claim live audio');
 timers.shift()();await settle();data.birds[0].assessment={};
 data.birds[0].live=false;timers.shift()();await settle();texts=[];now+=100;raf(now);assert(!texts.includes('Singing now'));
 assert([...store.values()].some(v=>v.includes('robin')),'finished state must be saved');
 data.generation='reset';data.birds=[];data.species=0;timers.shift()();await settle();assert.equal(g.branchDisplay.getState().shown.length,0,'reset must clear display state');
 // A delayed frame must advance the painting clock by elapsed time, not a capped frame duration.
 data.generation='clock';data.birds=[{id:'robin',name:'Robin',scientific_name:'Erithacus rubecula',count:1,observations:1,last_heard:new Date().toISOString(),live_until:new Date(Date.now()+60000).toISOString(),live:true,art_ready:true}];data.species=1;timers.shift()();await settle();resolvePainter({birdCanvas:canvas(),renderAt(){}});await settle();g.branchDisplay.setSpeed(1);now+=80000;raf(now);await settle();assert(g.branchDisplay.getState().done.includes('robin'),'elapsed wall time must complete after a delayed frame');
 const priorCreations=creations;data.period='month';data.period_key='month:2026-10-01';await get('period').onchange({target:{value:'month'}});await settle();assert.equal(creations,priorCreations,'browsing another period must not replay recently completed species');assert(g.branchDisplay.getState().done.includes('robin'));
 console.log('PASS: delayed-load deduplication, full completion, persisted finish, repeat caption update, no repeat repaint, live expiry, isolated reset');
}
main().catch(e=>{console.error(e);process.exitCode=1});
