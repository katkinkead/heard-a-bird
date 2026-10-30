function settleClarityBackground(legacy){
  const background=legacy.filter(s=>s.contextSection&&/background|geometry|tooth/.test(s.contextSection)&&s.pass>0);
  if(background.length){const a=background.reduce((n,s)=>Math.min(n,s.start),Infinity),b=background.reduce((n,s)=>Math.max(n,s.start+s.duration),0),scale=(48.8-a)/(b-a);for(const s of background){s.start=a+(s.start-a)*scale;s.duration=Math.max(.012,s.duration*scale);}}
}
function retimeClarityFinish(legacy,refinement,config){
  const centre=s=>s.points.reduce((a,p)=>[a[0]+p[0]/s.points.length,a[1]+p[1]/s.points.length],[0,0]);
  const inside=(x,y,e)=>{const dx=x-e.cx,dy=y-e.cy,c=Math.cos(e.angle||0),z=Math.sin(e.angle||0);return ((dx*c+dy*z)/e.rx)**2+((-dx*z+dy*c)/e.ry)**2<1;};
  const box=(x,y,b)=>x>=b[0]&&x<=b[2]&&y>=b[1]&&y<=b[3];
  const phrase=s=>{const [x,y]=centre(s);if(s.clarityRole==='edge-correction')return'edge correction';if(s.clarityRole==='perch')return'perch';if((config.feetBoxes||[]).some(b=>box(x,y,b)))return'feet';if((config.perchBoxes||[]).some(b=>box(x,y,b)))return'perch';if(inside(x,y,config.head))return'head';if(inside(x,y,config.tail))return'tail';if(inside(x,y,config.wing))return'wing';if(y>config.body.cy+config.body.ry*.23)return'lower breast';return'breast';};
  // Keep the approved opening. Earlier dry passes establish form; the new
  // precise pencil follows them locally, never hidden by a later coarse pass.
  const endBy={'head':49,'breast':53,'shoulder':55,'lower breast':59,'tail':56,'flight feathers':59,'patterned wing':60,'outer contour':59,'feet':64,'perch':65};
  settleClarityBackground(legacy);
  const pools=new Map();
  for(const s of legacy){if(s.finishStyle!=='reference'||s.contextSection)continue;const label=s.pacingPhrase||s.robinPacingPhrase||s.wrenPacingPhrase||s.blackbirdPacingPhrase||s.blueTitPacingPhrase||s.goldfinchPacingPhrase||'outer contour';if(!pools.has(label))pools.set(label,[]);pools.get(label).push(s);}
  for(const [label,list]of pools){const min=Math.min(...list.map(s=>s.start)),max=Math.max(...list.map(s=>s.start+s.duration)),end=endBy[label]||60,start=Math.min(min,end-6);const scale=(end-start)/(max-min||1);for(const s of list){s.start=start+(s.start-min)*scale;s.duration=Math.max(.012,s.duration*scale);}}
  const windows={'edge correction':[[67,70.4],[70.6,74.7]],head:[[49.1,55.4],[55.6,61.5]],breast:[[53.1,61.5],[61.7,69]],'lower breast':[[59.1,66.6],[66.8,73.6]],tail:[[56.1,63.3],[63.5,71.5]],wing:[[60.1,67.4],[67.6,74.6]],feet:[[64.1,69.4],[69.6,74.4]],perch:[[65.1,70],[70.2,74.4]]};
  const grouped=new Map();for(const s of refinement){const label=phrase(s);s.pacingPhrase=label;const key=label+':'+(s.clarityStage==='detail'?1:0);if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(s);}
  for(const [key,list]of grouped){const [label,stage]=key.split(':'),[a,b]=windows[label][+stage];const length=s=>s.points.slice(1).reduce((n,p,i)=>n+Math.hypot(p[0]-s.points[i][0],p[1]-s.points[i][1]),0);const costs=list.map(s=>Math.max(.2,Math.sqrt(length(s)*s.width))),total=costs.reduce((a,b)=>a+b,0);let at=0;for(let i=0;i<list.length;i++){const s=list[i];s.start=a+(b-a-.08)*at/total;s.duration=.07;s.pass=2;at+=costs[i];}}
}
