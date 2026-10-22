/*
 * Species-specific opening: authored graphite gestures, three selected wet
 * passages, and pressure-sensitive pigment ribbons. Source pixels supply
 * colour only; there is no finished-image reveal or bitmap overlay.
 *
 * buildSpeciesOpening({pixels,width,height,config}) -> drawable marks
 * drawSpeciesWet(context, mark, normalizedProgress) -> moving wet pigment
 */
(function () {
  const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
  const ease=v=>{v=clamp(v);return v*v*(3-2*v);};
  const dist=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2]);
  const inside=(x,y,p)=>{
    let hit=false;
    for(let i=0,j=p.length-1;i<p.length;j=i++){
      const a=p[i],b=p[j];
      if((a[1]>y)!==(b[1]>y)&&x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])hit=!hit;
    }
    return hit;
  };
  const bounds=p=>{
    const xs=p.map(v=>v[0]),ys=p.map(v=>v[1]);
    return [Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)];
  };
  const pathFor=p=>{
    const pair=v=>v.map(n=>n.toFixed(2)).join(' ');
    let path='M '+pair(p[0]);
    for(let i=0;i<p.length;i++){
      const a=p[(i+p.length-1)%p.length],b=p[i],c=p[(i+1)%p.length],d=p[(i+2)%p.length];
      const c1=[b[0]+(c[0]-a[0])*.13,b[1]+(c[1]-a[1])*.13];
      const c2=[c[0]-(d[0]-b[0])*.13,c[1]-(d[1]-b[1])*.13];
      path+=' C '+pair(c1)+' '+pair(c2)+' '+pair(c);
    }
    return path+' Z';
  };
  function canvas(w,h){const c=document.createElement('canvas');c.width=w;c.height=h;return c;}
  function edgeDistance(x,y,polygon) {
    let nearest=1e5;
    for(let i=0;i<polygon.length;i++){
      const a=polygon[i],b=polygon[(i+1)%polygon.length],dx=b[0]-a[0],dy=b[1]-a[1];
      const t=clamp(((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy||1));
      nearest=Math.min(nearest,Math.hypot(x-a[0]-t*dx,y-a[1]-t*dy));
    }
    return nearest;
  }
  function pointsFromPath(d) {
    if(Array.isArray(d))return d;
    const p=document.createElementNS('http://www.w3.org/2000/svg','path');
    p.setAttribute('d',d);
    const length=p.getTotalLength(),n=Math.max(10,Math.ceil(length/3.2));
    return Array.from({length:n+1},(_,i)=>{const a=p.getPointAtLength(length*i/n);return[a.x,a.y];});
  }
  function pixelReader(pixels,width,height) {
    const data=pixels.data||pixels;
    const sample=(x,y)=>{
      const i=(clamp(Math.round(y*height/750),0,height-1)*width+clamp(Math.round(x*width/1000),0,width-1))*4;
      return [data[i],data[i+1],data[i+2]];
    };
    return (x,y,r=4)=>{
      const base=sample(x,y),sum=[...base];let count=1;
      for(let n=0;n<8;n++){
        const a=n*Math.PI/4,c=sample(x+Math.cos(a)*r,y+Math.sin(a)*r);
        // Avoid mixing the bright paper into a neighbouring dark feather.
        if(dist(base,c)<75){for(let k=0;k<3;k++)sum[k]+=c[k];count++;}
      }
      return sum.map(v=>Math.round(v/count));
    };
  }
  function noise(x,y,seed) {
    function h(a,b){const n=Math.sin(a*127.1+b*311.7+seed*73.9)*43758.5453;return(n-Math.floor(n))*2-1;}
    function v(a,b){
      const ix=Math.floor(a),iy=Math.floor(b),fx=ease(a-ix),fy=ease(b-iy);
      return (h(ix,iy)*(1-fx)+h(ix+1,iy)*fx)*(1-fy)+(h(ix,iy+1)*(1-fx)+h(ix+1,iy+1)*fx)*fy;
    }
    return .64*v(x*.075,y*.075)+.26*v(x*.173+11.7,y*.173-8.4)+.10*v(x*.411-3.1,y*.411+5.9);
  }
  const wetStep=2.7,frameCount=43;
  function arrival(mask,wet,w,h,sources,direction,box) {
    const n=w*h,field=new Float32Array(n);field.fill(1e9);
    const heap=[];
    function push(i,d){
      let p=heap.length;heap.push([i,d]);
      while(p){const q=(p-1)>>1;if(heap[q][1]<=d)break;heap[p]=heap[q];p=q;}
      heap[p]=[i,d];
    }
    function pop(){
      const a=heap[0],z=heap.pop();
      if(heap.length){let p=0;while(p*2+1<heap.length){
        let q=p*2+1;if(q+1<heap.length&&heap[q+1][1]<heap[q][1])q++;
        if(heap[q][1]>=z[1])break;heap[p]=heap[q];p=q;
      }heap[p]=z;}
      return a;
    }
    sources.forEach(s=>{
      const x=clamp(Math.round((s[0]-box[0])/wetStep),0,w-1),y=clamp(Math.round((s[1]-box[1])/wetStep),0,h-1),i=y*w+x;
      if(mask[i]){field[i]=0;push(i,0);}
    });
    const dirs=[[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[1,-1],[-1,1]];
    while(heap.length){
      const [i,d]=pop();if(d>field[i]+.0001)continue;const x=i%w,y=(i/w)|0;
      for(const [dx,dy] of dirs){
        const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=w||yy>=h)continue;
        const j=yy*w+xx;if(mask[j]<.02)continue;
        const l=Math.hypot(dx,dy),along=(dx*direction[0]+dy*direction[1])/l;
        const dd=d+l*(1.23-.40*along)/(.22+.78*(wet[i]+wet[j])*.5);
        if(dd<field[j]){field[j]=dd;push(j,dd);}
      }
    }
    const vals=Array.from(field).filter((v,i)=>mask[i]>.08&&v<1e8).sort((a,b)=>a-b);
    const scale=vals[Math.floor(vals.length*.98)]||1;
    for(let i=0;i<n;i++)field[i]/=scale;
    return field;
  }
  function buildWetPatch(d) {
    const [ox,oy,bw,bh]=d.box,w=Math.ceil(bw/wetStep),h=Math.ceil(bh/wetStep),n=w*h;
    const mc=canvas(w,h),mg=mc.getContext('2d');
    mg.scale(1/wetStep,1/wetStep);mg.translate(-ox,-oy);
    mg.fill(new Path2D(d.path));
    const mp=mg.getImageData(0,0,w,h).data,mask=new Float32Array(n),wet=new Float32Array(n);
    const grain=new Float32Array(n),pools=new Float32Array(n),edge=new Float32Array(n);
    for(let i=0;i<n;i++){
      const x=ox+(i%w)*wetStep,y=oy+((i/w)|0)*wetStep;
      mask[i]=mp[i*4+3]/255;wet[i]=clamp(.72+noise(x*.60,y*.60,d.seed)*.25,.25,1);
      grain[i]=noise(x*3.7,y*3.7,d.seed+13);pools[i]=1+noise(x*.8,y*.8,d.seed)*.32;
    }
    for(let i=0;i<n;i++){
      if(!mask[i])continue;const x=i%w,y=(i/w)|0;let near=0;
      for(let k=1;k<=4;k++){
        const v=Math.min(mask[y*w+Math.max(0,x-k)],mask[y*w+Math.min(w-1,x+k)],mask[Math.max(0,y-k)*w+x],mask[Math.min(h-1,y+k)*w+x]);
        if(v<.5){near=1-k/5;break;}
      }
      edge[i]=near;mask[i]*=1-near*.42;
    }
    const field=arrival(mask,wet,w,h,d.sources,d.direction,d.box),frames=[];
    for(let f=0;f<frameCount;f++){
      const p=f/(frameCount-1),c=canvas(w,h),g=c.getContext('2d'),im=g.createImageData(w,h),out=im.data;
      const reach=1.15*Math.pow(ease(p/.61),.65),settle=ease((p-.43)/.57);
      for(let i=0;i<n;i++){
        if(!mask[i]||field[i]>1e7)continue;
        const a=field[i],front=ease((reach-a+.075)/.17),charge=ease(p/.075);
        const concentration=.24+.48*Math.exp(-a*2.5)*(1-.40*ease(p/.47));
        const gran=1+grain[i]*d.granulation*settle,rim=settle*edge[i]*.16*(.58+.42*wet[i]);
        const alpha=clamp((concentration*pools[i]*gran+rim)*front*mask[i]*charge,0,.70);
        const tint=clamp((a*.21)+(.5-grain[i])*.035+edge[i]*settle*.21);
        for(let k=0;k<3;k++)out[i*4+k]=d.color[k]*(1-tint)+d.rim[k]*tint;
        out[i*4+3]=alpha*255;
      }
      g.putImageData(im,0,0);frames.push(c);
    }
    return {frames,blend:canvas(w,h),box:d.box,path:new Path2D(d.path),definition:d};
  }
  function getRegions(config) {
    if(config.paintRegions?.length)return config.paintRegions;
    return ['head','body','wing','tail'].map(name=>{
      const box=config[name+'Box'];if(!box)return null;
      const [x,y,w,h]=box,c=config[name]||[x+w/2,y+h/2];
      return {name,center:c,polygon:[[x,y],[x+w,y],[x+w,y+h],[x,y+h]],direction:[.7,.7]};
    }).filter(Boolean);
  }
  function makeRibbons(region,birdPoly,sample,pass) {
    const poly=region.polygon,center=region.center||poly.reduce((a,p)=>[a[0]+p[0]/poly.length,a[1]+p[1]/poly.length],[0,0]);
    const dd=region.direction||[.5,.86],len=Math.hypot(...dd)||1,u=[dd[0]/len,dd[1]/len],v=[-u[1],u[0]];
    const toUV=p=>[(p[0]-center[0])*u[0]+(p[1]-center[1])*u[1],(p[0]-center[0])*v[0]+(p[1]-center[1])*v[1]];
    const projected=poly.map(toUV),b=bounds(projected),across=b[3]-b[1];
    const isTail=/tail/i.test(region.name),isHead=/head/i.test(region.name);
    const targetWidth=pass===0?(isTail?22:isHead?31:48):(isTail?14:isHead?23:31);
    const count=Math.max(4,Math.min(pass===0?18:24,Math.ceil(across/(targetWidth*(pass===0?.39:.35)))));
    const nominal=Math.min(targetWidth*1.1,across/count*2.65),ribbons=[];
    const safe=(x,y)=>inside(x,y,poly)&&(!birdPoly||inside(x,y,birdPoly));
    for(let row=0;row<count;row++){
      const q=(row+.5)/count,ac=b[1]+q*across,pts=[];
      const alongSpan=b[2]-b[0],steps=Math.max(12,Math.ceil(alongSpan/7));
      for(let k=0;k<=steps;k++){
        const t=k/steps,a=b[0]+alongSpan*t;
        const curve=Math.sin(t*Math.PI)*Math.min(13,across*.085)*(q<.5?1:-1);
        const x=center[0]+u[0]*a+v[0]*(ac+curve),y=center[1]+u[1]*a+v[1]*(ac+curve);
        if(safe(x,y))pts.push([x,y]);else if(pts.length>2)break;
      }
      if(pts.length<4)continue;
      const trim=Math.max(1,Math.ceil(nominal*.14/7)),path=pts.slice(trim,-trim||undefined);
      if(path.length<5)continue;
      // Feather engraving is intentionally deferred to the dry finishing
      // passes. A broad brush sees the local mass, rather than stopping at each
      // tiny pale hatch in the reference image.
      const rawColors=path.map(p=>sample(...p,6));
      const colors=rawColors.map((_,i)=>{
        const neighbors=rawColors.slice(Math.max(0,i-4),Math.min(path.length,i+5));
        return [0,1,2].map(k=>{
          const values=neighbors.map(c=>c[k]).sort((a,b)=>a-b);
          return values[Math.floor(values.length*.46)];
        });
      });
      let chunk=[],chunkColors=[],anchor=colors[0],cuts=0;
      function emit(){
        if(chunk.length<5){chunk=[];chunkColors=[];return;}
        const mid=chunk[(chunk.length/2)|0];
        const color=[0,1,2].map(k=>{
          const values=chunkColors.map(c=>c[k]).sort((a,b)=>a-b);
          return values[Math.floor(values.length*.48)];
        });
        const clear=Math.min(edgeDistance(mid[0],mid[1],poly),birdPoly?edgeDistance(mid[0],mid[1],birdPoly):1e4);
        let width=Math.min(nominal,clear*1.6);
        // Honour pressure-expanded bristles along the complete curve. The
        // finishing pass should never have to erase overspill outside the bird.
        chunk.forEach((p,j)=>{
          const q=j/(chunk.length-1),lift=.14+.9*Math.pow(Math.max(.001,Math.sin(q*Math.PI)),1.15);
          const room=Math.min(edgeDistance(p[0],p[1],poly),birdPoly?edgeDistance(p[0],p[1],birdPoly):1e4);
          width=Math.min(width,room/(.66*lift));
        });
        const length=chunk.slice(1).reduce((s,p,i)=>s+Math.hypot(p[0]-chunk[i][0],p[1]-chunk[i][1]),0);
        if(width>3&&length>28)ribbons.push({points:chunk.map(p=>[...p]),color,width,region:region.name,length});
        chunk=[];chunkColors=[];
      }
      for(let i=0;i<path.length;i++){
        const p=path[i],c=colors[i];
        const changesMass=cuts<2&&chunk.length>8&&i<path.length-6&&dist(c,anchor)>91&&colors.slice(i,i+3).every(z=>dist(z,anchor)>81);
        if(changesMass){
          const prior=chunk[chunk.length-1],priorColor=chunkColors[chunkColors.length-1];
          emit();chunk=[prior];chunkColors=[priorColor];anchor=c;cuts++;
        }
        chunk.push(p);chunkColors.push(c);
      }
      emit();
    }
    return ribbons;
  }
  window.buildSpeciesOpening=function({pixels,width,height,config}) {
    const sample=pixelReader(pixels,width,height),out=[],regions=getRegions(config),poly=config.birdPoly;
    const paths=(config.sketchPaths||[]).flatMap(d=>{
      if(typeof d==='string')return(d.match(/M[^M]+/gi)||[d]).map(p=>pointsFromPath(p));
      if(d.path)return (d.path.match(/M[^M]+/gi)||[d.path]).map(p=>pointsFromPath(p));
      return [d.points||d];
    }).filter(p=>p?.length>1);
    let cursor=.6;
    const lengths=paths.map(p=>p.slice(1).reduce((s,v,i)=>s+Math.hypot(v[0]-p[i][0],v[1]-p[i][1]),0));
    const total=lengths.reduce((s,v)=>s+Math.sqrt(v),0)||1;
    paths.forEach((points,i)=>{
      const duration=Math.max(.40,Math.sqrt(lengths[i])/total*9.9);
      out.push({points,start:cursor,duration,width:i<3?1.65:1.35,opacity:i<3?.28:.38,kind:'graphite',color:[73,72,67]});
      cursor+=duration+.08;
    });
    // A limited number of wet shapes deliberately leave untouched dry paper.
    const wetRegions=[regions.find(r=>/breast|body/i.test(r.name)),regions.find(r=>/wing/i.test(r.name)),regions.find(r=>/head/i.test(r.name))].filter(Boolean);
    wetRegions.forEach((r,i)=>{
      const center=r.center||r.polygon.reduce((a,p)=>[a[0]+p[0]/r.polygon.length,a[1]+p[1]/r.polygon.length],[0,0]);
      const factor=i===2?.58:.69;
      const shape=r.polygon.map(p=>[center[0]+(p[0]-center[0])*factor,center[1]+(p[1]-center[1])*factor]);
      const b=bounds(shape),box=[b[0]-3,b[1]-3,b[2]-b[0]+6,b[3]-b[1]+6];
      const dv=r.direction||[.5,.85],dl=Math.hypot(...dv)||1,direction=dv.map(v=>v/dl);
      const spread=Math.min(box[2],box[3])*.18;
      let origin=[center[0]-direction[0]*spread,center[1]-direction[1]*spread];
      if(!inside(...origin,shape))origin=center;
      const color=sample(...origin,7),rim=color.map(v=>Math.max(0,Math.round(v*.80)));
      const def={id:r.name,box,path:pathFor(shape),sources:[origin,[origin[0]+direction[0]*5,origin[1]+direction[1]*5]],direction,color,rim,granulation:i===1?.25:.14,seed:5.7+i*7.2};
      const patch=buildWetPatch(def);
      out.push({kind:'wet',id:'water-'+r.name,start:12+i*1.35,duration:8.4,width:0,opacity:1,points:def.sources,color:[229,230,217],wetPatch:patch});
      out.push({kind:'bloom',id:'pigment-'+r.name,start:18+i*1.55,duration:17.6-i*1.2,width:0,opacity:1,points:def.sources,color,wetPatch:patch});
    });
    // Passes revisit the same anatomy with increasingly loaded, narrower paint.
    // Regional phrases interleave so the bird develops as a whole.
    [0,1].forEach(pass=>{
      const groups=regions.map(r=>makeRibbons(r,poly,sample,pass));
      const queue=[];
      let remaining=true;
      while(remaining){remaining=false;for(const g of groups){for(let k=0;k<2&&g.length;k++){queue.push(g.shift());remaining=true;}}}
      queue.forEach((s,i)=>{
        const start=(pass===0?19.5:30)+i/Math.max(1,queue.length)*(pass===0?9.3:10.25);
        const duration=clamp(s.length/(pass===0?145:180),.62,1.65);
        out.push({...s,start,duration,width:s.width*(pass===0?1.03:1),opacity:pass===0?.31:.90,kind:pass===0?'wash':'paint',pressAt:.31+(i%5)*.035,pigmentLoad:pass===0?.8:1.07});
      });
    });
    return out.sort((a,b)=>a.start-b.start);
  };
  window.restoreSpeciesWet=buildWetPatch;
  window.drawSpeciesWet=function(ctx,s,progress) {
    const p=clamp(progress),patch=s.wetPatch;if(!patch||p<=0)return;
    ctx.save();
    if(s.kind==='wet'){
      const shine=Math.sin(Math.PI*p)*.085;
      if(shine>0){
        ctx.clip(patch.path);const b=patch.box,g=ctx.createLinearGradient(b[0],b[1],b[0]+b[2],b[1]+b[3]);
        g.addColorStop(0,'rgba(137,158,149,'+(shine*.28)+')');
        g.addColorStop(clamp(p*.8+.08,.01,.95),'rgba(255,255,246,'+(shine*1.8)+')');
        g.addColorStop(1,'rgba(141,158,150,'+(shine*.45)+')');
        ctx.fillStyle=g;ctx.fillRect(...b);
        ctx.lineWidth=.65;ctx.strokeStyle='rgba(250,253,240,'+(shine*.8)+')';ctx.stroke(patch.path);
      }
    }else{
      const at=p*(patch.frames.length-1),lo=Math.floor(at),mix=at-lo,b=patch.box;
      ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';
      if(mix>0){
        const blend=patch.blend,bg=blend.getContext('2d');
        bg.clearRect(0,0,blend.width,blend.height);bg.globalCompositeOperation='source-over';
        bg.globalAlpha=1-mix;bg.drawImage(patch.frames[lo],0,0);
        bg.globalCompositeOperation='lighter';bg.globalAlpha=mix;bg.drawImage(patch.frames[Math.min(lo+1,patch.frames.length-1)],0,0);
        bg.globalAlpha=1;bg.globalCompositeOperation='source-over';ctx.drawImage(blend,...b);
      }else ctx.drawImage(patch.frames[lo],...b);
    }
    ctx.restore();
  };
})();
