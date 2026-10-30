/* Fixed diagnostics only: no stack traces, URLs, credentials or arbitrary text. */
(function(root){
  const KEY='songsketch-display-reports-v1',TTL=7*86400000;
  const codes=new Set(['artwork-load','painting-timeout','render-failed','decoration-load']);
  class DisplayReporter {
    constructor({fetch:request,storage,now=Date.now,uuid=()=>crypto.randomUUID(),schedule=setTimeout,view='branch'}){
      Object.assign(this,{request,storage,now,uuid,schedule,view});this.token=null;this.busy=false;this.timer=null;this.delay=2000;this.seen=new Map();this.queue=[];
      try{const raw=storage?.getItem(KEY)||'[]';const rows=raw.length<=32768?JSON.parse(raw):[];if(Array.isArray(rows))this.queue=rows.filter(r=>this.valid(r)).slice(-20);}catch{}
      if(this.queue.length)this.later();
    }
    valid(r){return r&&Object.keys(r).sort().join(',')==='bird,code,observed_at,report_id,view'&&/^[a-f0-9-]{36}$/.test(r.report_id)&&codes.has(r.code)&&['branch','portrait'].includes(r.view)&&(r.bird===null||/^[a-z-]{1,80}$/.test(r.bird))&&Number.isFinite(Date.parse(r.observed_at))&&this.now()-Date.parse(r.observed_at)<=TTL&&Date.parse(r.observed_at)<=this.now()+300000;}
    save(){try{this.storage?.setItem(KEY,JSON.stringify(this.queue));}catch{/* Memory retry still works when storage is disabled. */}}
    report(code,bird=null){
      if(!codes.has(code))return;
      const key=code+':'+bird,now=this.now();if(now-(this.seen.get(key)??-Infinity)<60000)return;
      const r={report_id:this.uuid(),code,view:this.view,bird,observed_at:new Date(now).toISOString()};if(!this.valid(r))return;
      this.seen.set(key,now);if(this.seen.size>200)this.seen.delete(this.seen.keys().next().value);
      this.queue.push(r);this.queue=this.queue.slice(-20);this.save();this.later();
    }
    later(){if(this.timer!==null||!this.queue.length)return;this.timer=this.schedule(()=>{this.timer=null;this.flush();},this.delay);}
    async flush(){
      if(this.busy)return;this.busy=true;
      this.queue=this.queue.filter(r=>this.valid(r));this.save();
      try{
        if(!this.queue.length)return;
        if(!this.token){const r=await this.request('/api/display/session',{cache:'no-store',signal:AbortSignal.timeout(8000)});if(!r.ok)throw Error('Session unavailable');this.token=(await r.json()).token;}
        const item=this.queue[0],r=await this.request('/api/display/reports',{method:'POST',headers:{'Content-Type':'application/json','X-Display-Token':this.token},body:JSON.stringify(item),signal:AbortSignal.timeout(8000)});
        if(r.ok||r.status===400){this.queue=this.queue.filter(x=>x.report_id!==item.report_id);this.save();this.delay=2000;}
        else{if(r.status===401||r.status===429)this.token=null;throw Error('Report deferred');}
      }catch{this.delay=Math.min(60000,this.delay*2);}finally{this.busy=false;this.later();}
    }
  }
  if(typeof module!=='undefined')module.exports=DisplayReporter;
  if(root.document){
    let storage;try{storage=root.localStorage;}catch{}
    root.displayReporter=new DisplayReporter({fetch:root.fetch.bind(root),storage,view:root.location.pathname.startsWith('/branch')?'branch':'portrait'});
    root.addEventListener('online',()=>root.displayReporter.flush());
    root.addEventListener('error',()=>root.displayReporter.report('render-failed'));
    root.addEventListener('unhandledrejection',()=>root.displayReporter.report('render-failed'));
  }
})(typeof window==='undefined'?globalThis:window);
