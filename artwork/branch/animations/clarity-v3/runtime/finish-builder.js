/* Species-independent, reference-guided dry pigment. The reference supplies
 * colours and line tangents; every output item deposits an actual polyline.
 * It never returns a raster reveal, bitmap overlay, mask, or final-image swap. */
function buildSpeciesFinish({pixels,width,height,config}) {
  const data=pixels.data||pixels,out=[],W=1000,H=750;
  let seed=config.seed||834715;
  const rand=()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t^=t+Math.imul(t^t>>>7,61|t);return((t^t>>>14)>>>0)/4294967296;};
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const lum=c=>.213*c[0]+.715*c[1]+.072*c[2];
  const dist=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2]);
  const raw=(x,y)=>{
    const sx=clamp(x*width/W,0,width-1.001),sy=clamp(y*height/H,0,height-1.001),ix=sx|0,iy=sy|0,fx=sx-ix,fy=sy-iy,i=(iy*width+ix)*4,j=i+width*4;
    return [0,1,2].map(k=>data[i+k]*(1-fx)*(1-fy)+data[i+4+k]*fx*(1-fy)+data[j+k]*(1-fx)*fy+data[j+4+k]*fx*fy);
  };
  const sample=(x,y,r=0)=>{
    if(!r)return raw(x,y);
    const c=raw(x,y),cs=[raw(x-r,y),raw(x+r,y),raw(x,y-r),raw(x,y+r)];
    return c.map((v,i)=>(v*4+cs.reduce((s,z)=>s+z[i],0))/8);
  };
  const polys=config.birdPolys||(config.birdPoly?[config.birdPoly]:[]);
  const inPoly=(x,y,p)=>{
    let c=false;
    for(let i=0,j=p.length-1;i<p.length;j=i++){
      const a=p[i],b=p[j];
      if((a[1]>y)!==(b[1]>y)&&x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])c=!c;
    }
    return c;
  };
  const boxOf=b=>Array.isArray(b)?b:(b.box||[b.x,b.y,b.x+b.width,b.y+b.height]);
  const inBox=(x,y,b)=>{const r=boxOf(b);return x>=r[0]&&y>=r[1]&&x<r[2]&&y<r[3];};
  const excluded=(x,y)=>(config.excludeBoxes||[]).some(b=>inBox(x,y,b))||(config.textBoxes||[]).some(b=>inBox(x,y,b));
  const polyBounds=polys.map(p=>[Math.min(...p.map(v=>v[0])),Math.min(...p.map(v=>v[1])),Math.max(...p.map(v=>v[0])),Math.max(...p.map(v=>v[1]))]);
  const isBird=(x,y)=>polys.some((p,i)=>inBox(x,y,polyBounds[i])&&inPoly(x,y,p));
  const ellipse=(part,fallback)=>{
    if(!part)return fallback;
    if(Array.isArray(part))return {cx:part[0],cy:part[1],rx:part[2]||70,ry:part[3]||70,angle:part[4]||0};
    return {cx:part.cx??part.x??part.center?.[0]??fallback.cx,cy:part.cy??part.y??part.center?.[1]??fallback.cy,rx:part.rx??part.radius??fallback.rx,ry:part.ry??part.radius??fallback.ry,angle:part.angle??fallback.angle};
  };
  const head=ellipse(config.head,{cx:400,cy:200,rx:100,ry:100,angle:0});
  const body=ellipse(config.body,{cx:500,cy:380,rx:170,ry:180,angle:1.1});
  const wing=ellipse(config.wing,{cx:570,cy:370,rx:150,ry:85,angle:.7});
  const tail=ellipse(config.tail,{cx:720,cy:480,rx:140,ry:35,angle:.7});
  const elDistance=(x,y,e)=>{const c=Math.cos(e.angle),s=Math.sin(e.angle),dx=x-e.cx,dy=y-e.cy;return((dx*c+dy*s)/e.rx)**2+((-dx*s+dy*c)/e.ry)**2;};
  const extras=config.extrasBoxes||[],backgrounds=config.backgroundBoxes||[];
  const mask=new Uint8Array(W*H),group=new Uint8Array(W*H),bgMask=new Uint8Array(W*H);
  let x0=W,y0=H,x1=0,y1=0;
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){
    if(excluded(x,y))continue;
    const bird=isBird(x,y),extra=!bird&&extras.some(b=>inBox(x,y,b));
    if(bird||extra){
      const c=bird?null:raw(x,y),l=c?lum(c):0;
      const foot=!config.approvedOriginal&&!bird&&(config.feetBoxes||[]).some(b=>inBox(x,y,b))&&(config.feetPolys||[]).some(p=>inPoly(x,y,p));
      const qualifies=bird||foot||l<(config.extrasLuminance??180)||(c[0]-c[1]>27&&c[2]>c[1]*.65);
      if(qualifies){
        const q=y*W+x;mask[q]=1;
        group[q]=!bird?6:elDistance(x,y,head)<1.3?0:elDistance(x,y,tail)<1.1?5:elDistance(x,y,wing)<1.1?3:x<body.cx?1:y>body.cy?2:4;
        x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y);
      }
    }
    if(!bird&&!mask[y*W+x]&&backgrounds.some(b=>inBox(x,y,b))){
      const c=raw(x,y),chroma=Math.max(...c)-Math.min(...c);
      if(chroma>(config.backgroundChroma??13)||lum(c)<(config.backgroundLuminance??221))bgMask[y*W+x]=1;
    }
  }
  const inMask=(x,y,m=mask)=>x>=0&&x<W&&y>=0&&y<H&&m[(y|0)*W+(x|0)]===1;
  const direction=(x,y,scale)=>{
    let a;
    if(elDistance(x,y,head)<1.3)a=Math.atan2((y-head.cy)/head.ry,(x-head.cx)/head.rx)+Math.PI*.5;
    else if(elDistance(x,y,tail)<1.15)a=tail.angle;
    else if(elDistance(x,y,wing)<1.3)a=wing.angle;
    else a=body.angle+(x-body.cx)*.0007-(y-body.cy)*.0011;
    for(const r of config.directionRegions||[])if(inBox(x,y,r.box)){a=r.angle;break;}
    if(scale>=1){
      const left=sample(x-1.2,y,.4),right=sample(x+1.2,y,.4),top=sample(x,y-1.2,.4),bot=sample(x,y+1.2,.4);
      let dx=0,dy=0;
      for(let k=0;k<3;k++){const gx=right[k]-left[k],gy=bot[k]-top[k];if(Math.hypot(gx,gy)>Math.hypot(dx,dy)){dx=gx;dy=gy;}}
      if(Math.hypot(dx,dy)>25){
        let tangent=Math.atan2(dy,dx)+Math.PI/2;
        while(tangent-a>Math.PI/2)tangent-=Math.PI;
        while(tangent-a< -Math.PI/2)tangent+=Math.PI;
        a=a*.12+tangent*.88;
      }
    }
    return a;
  };
  const mark=(points,color,breadth,start,duration,section)=>({points,color:color.map(Math.round),width:breadth,opacity:1,kind:'pencil',profile:'flat',finishStyle:'reference',start,duration,region:section});
  const makeMark=(x,y,c,breadth,length,tolerance,blur,pass,maskType=mask)=>{
    const angle=maskType===bgMask?-.3+rand()*1.6:direction(x,y,pass),v=[Math.cos(angle),Math.sin(angle)],n=[-v[1],v[0]];
    let w=breadth;
    for(let j=0;j<4;j++){
      const a=[x+n[0]*w*.48,y+n[1]*w*.48],b=[x-n[0]*w*.48,y-n[1]*w*.48];
      if(inMask(...a,maskType)&&inMask(...b,maskType)&&dist(sample(...a,blur),c)<tolerance*1.2&&dist(sample(...b,blur),c)<tolerance*1.2)break;
      w*=.66;
    }
    const ends=[];
    for(const sign of [-1,1]){
      const ps=[],limit=length*.5;let at=0;
      for(let s=.7;s<=limit;s+=.75){
        const curve=Math.sin(s/Math.max(4,length)*Math.PI)*Math.min(.35,length*.025),xx=x+v[0]*s*sign+n[0]*curve,yy=y+v[1]*s*sign+n[1]*curve;
        if(!inMask(xx,yy,maskType)||dist(sample(xx,yy,blur),c)>tolerance)break;
        at=s;if(s>limit*.38&&s<limit*.72)ps.push([xx,yy]);
      }
      const len=Math.max(.2,at);ends.push({p:[x+v[0]*len*sign,y+v[1]*len*sign],mid:ps[Math.floor(ps.length/2)]});
    }
    const points=[ends[0].p];if(ends[0].mid)points.push(ends[0].mid);points.push([x,y]);if(ends[1].mid)points.push(ends[1].mid);points.push(ends[1].p);
    const m=mark(points,c,w,0,.18,maskType===bgMask?7:group[(y|0)*W+(x|0)]);m.pass=pass;return m;
  };
  const batches=[[],[],[]],passes=[
    {grid:6.7,width:10,length:19,tolerance:89,blur:2},
    {grid:3.45,width:5.1,length:10,tolerance:64,blur:.8},
    {grid:2.15,width:2.8,length:7,tolerance:40,blur:0}
  ];
  passes.forEach((p,pass)=>{
    for(let y=y0;y<=y1;y+=p.grid)for(let x=x0;x<=x1;x+=p.grid){
      const xx=x+(rand()-.5)*p.grid*.58,yy=y+(rand()-.5)*p.grid*.58;if(!inMask(xx,yy))continue;
      const c=sample(xx,yy,p.blur);let wid=p.width,len=p.length;
      if(group[(yy|0)*W+(xx|0)]===6){wid*=.54;len*=.85;}
      const m=makeMark(xx,yy,c,wid,len,p.tolerance,p.blur,pass);m.order=rand();batches[pass].push(m);
    }
  });
  for(let y=y0;y<=y1;y+=1.35)for(let x=x0;x<=x1;x+=1.35){
    const xx=x+(rand()-.5)*.5,yy=y+(rand()-.5)*.5;if(!inMask(xx,yy))continue;
    const c=raw(xx,yy),local=[raw(xx-1,yy),raw(xx+1,yy),raw(xx,yy-1),raw(xx,yy+1)],edge=Math.max(...local.map(z=>dist(c,z)));
    if(edge<35||rand()>.82)continue;
    const m=makeMark(xx,yy,c,1.03,4.2,27,0,2);m.order=rand();m.accent=true;batches[2].push(m);
  }
  const focal=[];
  for(const boxItem of config.focalBoxes||[]){
    const box=boxOf(boxItem);
    for(let y=box[1];y<box[3];y+=.92)for(let x=box[0];x<box[2];x+=.92){
      if(!inMask(x,y))continue;
      const c=raw(x,y),edge=Math.max(dist(c,raw(x-1,y)),dist(c,raw(x+1,y)),dist(c,raw(x,y-1)),dist(c,raw(x,y+1)));
      if(edge<21&&rand()>.32)continue;
      const m=makeMark(x,y,c,1.03,2.1,21,0,2);m.order=rand();m.focal=true;focal.push(m);
    }
  }
  const ranges=[[40,53.5],[53,68.5],[68,83]];
  batches.forEach((batch,pass)=>{
    const pools=Array.from({length:8},()=>[]);for(const m of batch)pools[m.region].push(m);
    pools.forEach(p=>p.sort((a,b)=>(a.accent?-1:0)-(b.accent?-1:0)||a.order-b.order));
    const sequence=[],regionOrder=[0,1,3,4,2,5,0,4,3,2,6,7];let left=batch.length;
    while(left)for(const r of regionOrder){const p=pools[r];for(let k=0;k<38&&p.length;k++){sequence.push(p.pop());left--;}}
    const [a,b]=ranges[pass];let total=0;
    for(const m of sequence){m.cost=.6+Math.sqrt(m.width)*.21;total+=m.cost;}
    let done=0;
    for(const m of sequence){m.start=a+(b-a)*done/total;m.duration=pass===0?.22:pass===1?.18:.115;done+=m.cost;delete m.cost;delete m.order;out.push(m);}
  });
  focal.sort((a,b)=>(a.region===0?1:0)-(b.region===0?1:0)||a.order-b.order);
  focal.forEach((m,i)=>{m.start=83.1+3.7*i/Math.max(1,focal.length);m.duration=.1;delete m.order;out.push(m);});
  // The geometry receives a light, deliberately sparse first wash, then short
  // return visits restore its broken pigment edges and paper grain.
  const bgBatches=[[],[],[]],bgSpecs=[
    {grid:8.5,width:12,length:23,tolerance:94,blur:2.5},
    {grid:4.3,width:6.2,length:11,tolerance:68,blur:1},
    {grid:3.1,width:4,length:6.7,tolerance:48,blur:0}
  ];
  if(backgrounds.length)bgSpecs.forEach((p,pass)=>{
    for(let y=0;y<H;y+=p.grid)for(let x=0;x<W;x+=p.grid){
      const xx=x+(rand()-.5)*p.grid*.5,yy=y+(rand()-.5)*p.grid*.5;if(!inMask(xx,yy,bgMask))continue;
      const m=makeMark(xx,yy,sample(xx,yy,p.blur),p.width,p.length,p.tolerance,p.blur,pass,bgMask);m.order=rand();
      if(pass===0){m.opacity=.30;m.kind='wash';m.profile='flat';m.duration=.3;}
      bgBatches[pass].push(m);
    }
  });
  const bgRanges=[[13,35],[37,55],[55,78]];
  bgBatches.forEach((list,pass)=>{
    list.sort((a,b)=>a.order-b.order);
    const [a,b]=bgRanges[pass];
    list.forEach((m,i)=>{m.start=a+(b-a)*i/Math.max(1,list.length);m.duration=pass===0?.3:.12;m.contextSection='geometric background';delete m.order;out.push(m);});
  });
  // Source lettering, when present in the selected source, is traced as actual
  // calligraphic paths. Cropped names may instead be drawn by the shared view.
  function traceInk(item){
    const box=boxOf(item),limit=item.limit??155,start=item.start??87,end=item.end??89.7;
    const [bx0,by0,bx1,by1]=box,scale=1.3,w=Math.ceil((bx1-bx0)*scale)+2,h=Math.ceil((by1-by0)*scale)+2;
    const ink=new Uint8Array(w*h),distance=new Float32Array(w*h);
    for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){
      const c=raw(bx0+(x-1)/scale,by0+(y-1)/scale),q=y*w+x;
      if(lum(c)<limit){ink[q]=1;distance[q]=1e5;}
    }
    for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){const q=y*w+x;if(ink[q])distance[q]=Math.min(distance[q],distance[q-1]+1,distance[q-w]+1,distance[q-w-1]+1.414,distance[q-w+1]+1.414);}
    for(let y=h-2;y>0;y--)for(let x=w-2;x>0;x--){const q=y*w+x;if(ink[q])distance[q]=Math.min(distance[q],distance[q+1]+1,distance[q+w]+1,distance[q+w+1]+1.414,distance[q+w-1]+1.414);}
    const off=[-w,-w+1,1,w+1,w,w-1,-1,-w-1];
    for(let iteration=0;iteration<35;iteration++){
      let removed=0;
      for(let phase=0;phase<2;phase++){
        const remove=[];
        for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){
          const q=y*w+x;if(!ink[q])continue;
          const p=off.map(d=>ink[q+d]),n=p.reduce((a,b)=>a+b,0);if(n<2||n>6)continue;
          let transitions=0;for(let k=0;k<8;k++)if(!p[k]&&p[(k+1)%8])transitions++;if(transitions!==1)continue;
          if(!phase?(p[0]*p[2]*p[4]||p[2]*p[4]*p[6]):(p[0]*p[2]*p[6]||p[0]*p[4]*p[6]))continue;
          remove.push(q);
        }
        remove.forEach(q=>ink[q]=0);removed+=remove.length;
      }
      if(!removed)break;
    }
    const neighbors=q=>off.map(d=>q+d).filter(i=>ink[i]),seen=new Set(),key=(a,b)=>a<b?a+':'+b:b+':'+a,paths=[];
    function walk(a,b){
      const path=[a],initial=a;let prev=a,q=b;seen.add(key(a,b));
      for(let k=0;k<2000;k++){
        path.push(q);const ns=neighbors(q).filter(n=>n!==prev);
        if(ns.length!==1)break;const next=ns[0],edge=key(q,next);if(seen.has(edge))break;
        seen.add(edge);prev=q;q=next;if(q===initial)break;
      }
      if(path.length>1)paths.push(path);
    }
    for(let q=w+1;q<ink.length-w-1;q++)if(ink[q]&&neighbors(q).length!==2)for(const b of neighbors(q))if(!seen.has(key(q,b)))walk(q,b);
    for(let q=w+1;q<ink.length-w-1;q++)if(ink[q])for(const b of neighbors(q))if(!seen.has(key(q,b)))walk(q,b);
    const marks=[];
    for(const path of paths)for(let i=0;i<path.length-1;){
      const begin=i,base=distance[path[i]];let j=i+1;
      while(j<path.length-1&&j-begin<13&&Math.abs(distance[path[j]]-base)<Math.max(.9,base*.3))j++;
      const segment=path.slice(begin,j+1),points=segment.map(q=>[bx0+(q%w-1)/scale,by0+((q/w|0)-1)/scale]),middle=points[points.length>>1];
      const breadth=segment.reduce((s,q)=>s+distance[q],0)/segment.length*1.86/scale,m=mark(points,raw(...middle),Math.max(.7,breadth),0,.11,8);
      m.order=points.reduce((s,p)=>s+p[0],0)/points.length;m.contextSection=item.label||'handwritten name';marks.push(m);i=j;
    }
    marks.sort((a,b)=>a.order-b.order);
    marks.forEach((m,i)=>{m.start=start+(end-start)*i/Math.max(1,marks.length-1);delete m.order;out.push(m);});
  }
  for(const item of config.textBoxes||[])traceInk(item);
  return out;
}
