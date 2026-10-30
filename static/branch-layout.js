/* Deterministic local tree geometry, registered to each bird's feet. */
(function(){
'use strict';
function build(ids, registrations){
 const regs=Object.fromEntries(registrations.map(r=>[r.id,r]));
 function place(id,cx,fy,height,width=Infinity){const r=regs[id],b=r?.birdBounds||[200,100,700,600],anchor=r?.perchAnchor||[450,580],s=Math.min(height/(b[3]-b[1]),width/(b[2]-b[0])),x=cx-anchor[0]*s,y=fy-anchor[1]*s;return {id,cx,fy,x,y,s,bounds:[x+b[0]*s,y+b[1]*s,x+b[2]*s,y+b[3]*s],contacts:(r?.footContacts?.length?r.footContacts:[anchor]).map(p=>[x+p[0]*s,y+p[1]*s]),mode:r?.placementMode||'perched'};}
 const n=ids.length;if(!n)return {nodes:[],edges:[],camera:{s:1,x:0,y:0}};
 let nodes=[],edges=[];
 if(n<=5){const slots=n===1?[[1000,810,648]]:n===2?[[650,735,475],[1460,735,475]]:[[650,735,475],[1460,735,475],[2150,500,475],[2820,1300,475],[3300,600,475]];
  nodes=ids.map((id,i)=>place(id,...slots[i]));
  // Adapt spacing to actual silhouettes, including long tails and left-facing birds.
  for(let i=1;i<n;i++){for(let j=0;j<i;j++){const a=nodes[j].bounds,b=nodes[i].bounds;if(Math.min(a[3]+120,b[3]+120)>Math.max(a[1],b[1])&&b[0]<a[2]+100){const dx=a[2]+100-b[0];nodes[i]=place(ids[i],nodes[i].cx+dx,nodes[i].fy,475);}}}

  const foot=p=>p.contacts.slice().sort((a,b)=>a[0]-b[0]);
  if(n===1)edges.push({id:0,points:[[96,835],[350,816],[650,833],...foot(nodes[0]),[1330,824],[1700,783],[1820,774]],width:27,owner:0});
  else {const joint=[Math.max(nodes[1].bounds[2]+80,nodes[1].cx+260),nodes[1].fy-12];
   edges.push({id:0,points:[[30,745],[280,722],...foot(nodes[0]),[(nodes[0].cx+nodes[1].cx)/2,726],...foot(nodes[1]),joint,[joint[0]+100,joint[1]-9]],width:21,owner:0});
   if(n>=3){const p=nodes[2],end=[Math.max(p.bounds[2]+50,p.contacts.at(-1)[0]+200),p.fy+55];
    edges.push({id:2,points:[joint,[joint[0]+(p.cx-joint[0])*.35,joint[1]-70],[p.cx-160,p.fy+65],...foot(p),[end[0]-160,end[1]-23],end],width:10,owner:2});
    if(n>=5){const w=nodes[4],from=[end[0]-160,end[1]-23];edges.push({id:4,points:[from,[from[0]+(w.cx-from[0])*.3,from[1]+80],[w.cx-280,w.fy+45],...foot(w),[w.bounds[2]+50,w.fy-20]],width:6,owner:4});}}
   if(n>=4){const p=nodes[3];edges.push({id:3,points:[joint,[joint[0]+200,joint[1]+142],[p.cx-640,p.fy-185],[p.cx-340,p.fy-20],...foot(p),[p.bounds[2]+50,p.fy-15]],width:12,owner:3});}}

  const cam=n===1||n===2?{s:1,x:0,y:0}:n===3?{s:.68,x:80,y:180}:n===4?{s:.54,x:65,y:90}:{s:.47,x:70,y:150};
  // Very long-tailed species need a wider overall fit than the five benchmarks.
  const projected=nodes.flatMap(p=>[[p.bounds[0]*cam.s+cam.x,p.bounds[1]*cam.s+cam.y],[p.bounds[2]*cam.s+cam.x,p.bounds[3]*cam.s+cam.y]]);
  if(projected.every(p=>p[0]>=40&&p[0]<=1880&&p[1]>=40&&p[1]<=950))return {nodes,edges,camera:cam};
 }else{
  const counts=[3,4,5,5,5,5,6,6,6],columns=[];while(counts.reduce((a,b)=>a+b,0)<n)counts.push(6);let i=0;
  for(let col=0;col<counts.length&&i<n;col++){const list=[],span=2200+Math.min(col,5)*330;
   for(let j=0;j<counts[col]&&i<n;j++,i++){let p=place(ids[i],500+col*900+j*30,2700-span/2+j*span/(counts[col]-1),400,500);list.push({p,i});nodes.push(p);}
   columns.push(list);
  }
  columns.forEach((list,col)=>list.forEach(({p,i})=>{const prev=col?columns[col-1].reduce((a,b)=>Math.abs(a.p.fy-p.fy)<Math.abs(b.p.fy-p.fy)?a:b):null,from=prev?[prev.p.cx,prev.p.fy+10]:[0,2700],feet=p.contacts.slice().sort((a,b)=>a[0]-b[0]);const to=feet[0],dx=to[0]-from[0];edges.push({id:i,owner:i,parent:prev?.i??null,width:Math.max(7,40-col*3),points:[from,[from[0]+dx*.32,from[1]+(to[1]-from[1])*.12],[from[0]+dx*.69,to[1]+(i%2?35:-35)],...feet,[feet.at(-1)[0]+80,feet.at(-1)[1]-10]]});}));
 }
 const bounds=[Math.min(0,...nodes.map(p=>p.bounds[0])),Math.min(...nodes.map(p=>p.bounds[1]))-100,Math.max(...nodes.map(p=>p.bounds[2]))+180,Math.max(...nodes.map(p=>p.bounds[3]))+380],s=Math.min(1760/(bounds[2]-bounds[0]),850/(bounds[3]-bounds[1]));
 return {nodes,edges,camera:{s,x:80-bounds[0]*s,y:95-bounds[1]*s}};
}
window.BranchLayout={build};
})();
