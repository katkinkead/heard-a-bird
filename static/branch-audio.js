/* Fresh, deduplicated bout playback. No backlog, no automatic unmute. */
(function(root){
'use strict';
class BoutAudio {
 constructor({play,stop=()=>{},storage=null,clock=()=>Date.now(),status=()=>{}}={}){this.play=play;this.stopSound=stop;this.storage=storage;this.clock=clock;this.status=status;this.enabled=false;this.volume=.35;this.busy=false;this.serial=0;this.seen=new Set();this.pending=new Map();this.generation=null;this.healthy=false;}
 persist(){if(this.seen.size>1500)this.seen=new Set([...this.seen].slice(-1500));try{this.storage?.setItem('songsketch-audio-bouts',JSON.stringify({generation:this.generation,seen:[...this.seen].slice(-1500)}));}catch{}}
 setEnabled(value){this.enabled=!!value;if(!value){this.serial++;this.busy=false;this.pending.clear();this.stopSound();}this.status(value?'Sound enabled · one clip per new bout':'Sound muted');}
 update(state,ready=[]){const time=Date.parse(state.server_now);this.healthy=state.station?.listening==='available';this.now=time;this.received=this.clock();if(!this.healthy){this.serial++;this.busy=false;this.pending.clear();this.stopSound();}
  if(this.generation!==state.generation){this.generation=state.generation;this.pending.clear();this.seen.clear();try{const old=JSON.parse(this.storage?.getItem('songsketch-audio-bouts')||'null');if(old?.generation===this.generation)this.seen=new Set(old.seen||[]);}catch{}// A refresh must not replay the birds already on the screen.
   for(const b of state.birds)if(b.latest_bout)this.seen.add(b.latest_bout.id);this.persist();return;}
  for(const b of state.birds){const bout=b.latest_bout;if(!bout||this.seen.has(bout.id))continue;this.seen.add(bout.id);if(this.enabled&&this.healthy&&!state.rehearsal_history&&b.content?.audio?.available&&time-Date.parse(bout.started_at)>=0&&time-Date.parse(bout.started_at)<60000)this.pending.set(b.id,b);}
  this.persist();for(const id of ready)this.begin(id);for(const [id,b]of this.pending)if(time-Date.parse(b.latest_bout.started_at)>=60000)this.pending.delete(id);
 }
 async begin(id){const b=this.pending.get(id);if(!b)return;this.pending.delete(id);const age=this.now+this.clock()-this.received-Date.parse(b.latest_bout.started_at);if(!this.enabled||!this.healthy||this.clock()-this.received>6000||this.busy||age<0||age>=60000)return;
  this.busy=true;const serial=++this.serial;try{await this.play(b.content.audio.url,this.volume,()=>serial===this.serial&&this.enabled&&this.healthy&&this.clock()-this.received<6000);if(serial===this.serial)this.status('Reference clip finished · listening continues');}catch{if(serial===this.serial)this.status('This recording could not play. The painting continues.');}finally{if(serial===this.serial)this.busy=false;}}
 disconnect(){this.healthy=false;this.pending.clear();this.serial++;this.busy=false;this.stopSound();}
}
root.BoutAudio=BoutAudio;if(typeof module!=='undefined')module.exports=BoutAudio;
})(typeof window!=='undefined'?window:globalThis);
