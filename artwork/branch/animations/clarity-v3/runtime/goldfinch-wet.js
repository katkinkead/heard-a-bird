(function () {
  const clamp = (x,a=0,b=1)=>Math.max(a,Math.min(b,x));
  const ease = x=>{x=clamp(x);return x*x*(3-2*x);};
  function noise(x,y,seed) {
    function h(a,b) {const z=Math.sin(a*127.1+b*311.7+seed*73.9)*43758.5453;return (z-Math.floor(z))*2-1;}
    function v(a,b) {const ix=Math.floor(a),iy=Math.floor(b),fx=ease(a-ix),fy=ease(b-iy);return (h(ix,iy)*(1-fx)+h(ix+1,iy)*fx)*(1-fy)+(h(ix,iy+1)*(1-fx)+h(ix+1,iy+1)*fx)*fy;}
    return .64*v(x*.075,y*.075)+.26*v(x*.173+11.7,y*.173-8.4)+.10*v(x*.411-3.1,y*.411+5.9);
  }
  const defs=[
    {id:'chest',box:[294,234,192,241],seed:3.7,
      path:'M331 244 C307 264 299 302 311 340 C326 385 372 429 449 456 C470 459 475 447 459 433 C411 410 394 383 376 354 C361 323 368 283 355 256 C348 243 340 237 331 244 Z',
      sources:[[333,265],[332,279],[336,290]],direction:[.36,.93],
      color:[176,105,46],rim:[153,99,52],granulation:.19,start:18,duration:20,
      waterStart:12,waterDuration:9},
    {id:'shoulder',box:[425,196,176,146],seed:9.1,
      path:'M458 209 C438 207 437 224 452 239 C478 261 492 280 516 296 C539 310 561 326 584 330 C589 317 571 291 555 276 C525 247 494 223 477 214 C470 210 463 208 458 209 Z',
      sources:[[458,220],[470,227],[480,232]],direction:[.83,.56],
      color:[204,135,47],rim:[181,108,39],granulation:.10,start:19.5,duration:18.5,
      waterStart:14,waterDuration:8},
    {id:'wing',box:[405,254,144,132],seed:17.3,
      path:'M425 266 C410 272 414 292 432 316 C455 344 495 370 535 377 C543 371 531 351 515 336 C492 311 479 289 453 274 C441 267 431 263 425 266 Z',
      sources:[[430,282],[438,293]],direction:[.72,.70],
      color:[41,91,103],rim:[30,61,80],granulation:.29,start:22,duration:16,
      waterStart:15.5,waterDuration:8}
  ];
  const step=2.2, frameCount=55;
  let passes=null;
  function canvas(w,h) {const c=document.createElement('canvas');c.width=w;c.height=h;return c;}

  // A weighted arrival field follows wet paper, local permeability, and the
  // directional sweep. It is deliberately not an expanding radial gradient.
  function arrival(mask,wet,w,h,sources,direction,box) {
    const n=w*h,dist=new Float32Array(n);dist.fill(1e9);
    const heap=[];
    function push(i,d) {let p=heap.length;heap.push([i,d]);while(p){const q=(p-1)>>1;if(heap[q][1]<=d)break;heap[p]=heap[q];p=q;}heap[p]=[i,d];}
    function pop() {const a=heap[0],z=heap.pop();if(heap.length){let p=0;while(p*2+1<heap.length){let q=p*2+1;if(q+1<heap.length&&heap[q+1][1]<heap[q][1])q++;if(heap[q][1]>=z[1])break;heap[p]=heap[q];p=q;}heap[p]=z;}return a;}
    sources.forEach(s=>{const x=Math.round((s[0]-box[0])/step),y=Math.round((s[1]-box[1])/step),i=y*w+x;if(mask[i]){dist[i]=0;push(i,0);}});
    const dirs=[[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[1,-1],[-1,1]];
    while(heap.length){const [i,d]=pop();if(d>dist[i]+.0001)continue;const x=i%w,y=(i/w)|0;
      for(const [dx,dy] of dirs){const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=w||yy>=h)continue;const j=yy*w+xx;if(mask[j]<.02)continue;
        const l=Math.hypot(dx,dy),along=(dx*direction[0]+dy*direction[1])/l;
        const cost=l*(1.23-.40*along)/(.22+.78*(wet[i]+wet[j])*.5);
        const dd=d+cost;if(dd<dist[j]){dist[j]=dd;push(j,dd);}
      }
    }
    const vals=Array.from(dist).filter((v,i)=>mask[i]>.08&&v<1e8).sort((a,b)=>a-b);
    const scale=vals[Math.floor(vals.length*.98)]||1;
    for(let i=0;i<n;i++)dist[i]/=scale;
    return dist;
  }
  function buildPatch(d) {
    const [ox,oy,bw,bh]=d.box,w=Math.ceil(bw/step),h=Math.ceil(bh/step),n=w*h;
    const mc=canvas(w,h),mg=mc.getContext('2d');
    mg.scale(1/step,1/step);mg.translate(-ox,-oy);mg.fill(new Path2D(d.path));
    const mp=mg.getImageData(0,0,w,h).data,mask=new Float32Array(n),wet=new Float32Array(n),grain=new Float32Array(n),pools=new Float32Array(n),edge=new Float32Array(n);
    for(let i=0;i<n;i++){const x=ox+(i%w)*step,y=oy+((i/w)|0)*step;
      mask[i]=mp[i*4+3]/255;
      wet[i]=clamp(.72+noise(x*.60,y*.60,d.seed)*.25,.25,1);
      grain[i]=noise(x*3.7,y*3.7,d.seed+13);
      pools[i]=1+noise(x*.8,y*.8,d.seed)*.32;
    }
    // Interior water gradient: a soft, irregular rim rather than a cookie cutter.
    for(let i=0;i<n;i++){if(!mask[i])continue;const x=i%w,y=(i/w)|0;let near=0;
      for(let k=1;k<=4;k++){const v=Math.min(mask[y*w+Math.max(0,x-k)],mask[y*w+Math.min(w-1,x+k)],mask[Math.max(0,y-k)*w+x],mask[Math.min(h-1,y+k)*w+x]);if(v<.5){near=1-k/5;break;}}
      edge[i]=near;mask[i]*=1-near*.42;
    }
    const dist=arrival(mask,wet,w,h,d.sources,d.direction,d.box),frames=[];
    for(let f=0;f<frameCount;f++){
      const p=f/(frameCount-1),c=canvas(w,h),g=c.getContext('2d'),im=g.createImageData(w,h),out=im.data;
      const reach=1.15*Math.pow(ease(p/.61),.65),settle=ease((p-.43)/.57);
      for(let i=0;i<n;i++){if(!mask[i]||dist[i]>1e7)continue;
        const x=ox+(i%w)*step,y=oy+((i/w)|0)*step;
        const a=dist[i],front=ease((reach-a+.075)/.17),charge=ease(p/.075);
        // Concentrated touch thins as it feeds the mobile wash; translucent
        // interior remains varied after the travel has stopped.
        const concentration=.24+.48*Math.exp(-a*2.5)*(1-.40*ease(p/.47));
        const gran=1+grain[i]*d.granulation*settle;
        const rim=settle*edge[i]*.16*(.58+.42*wet[i]);
        const alpha=clamp((concentration*pools[i]*gran+rim)*front*mask[i]*charge,0,.70);
        const tint=clamp((a*.21)+(.5-grain[i])*.035+edge[i]*settle*.21);
        out[i*4]=d.color[0]*(1-tint)+d.rim[0]*tint;
        out[i*4+1]=d.color[1]*(1-tint)+d.rim[1]*tint;
        out[i*4+2]=d.color[2]*(1-tint)+d.rim[2]*tint;
        out[i*4+3]=alpha*255;
      }
      g.putImageData(im,0,0);frames.push(c);
    }
    return {frames,blend:canvas(w,h),box:d.box,path:new Path2D(d.path),definition:d};
  }
  window.buildWetPass=function () {
    if(passes)return passes;
    passes=[];
    defs.forEach(d=>{const patch=buildPatch(d);
      passes.push({kind:'wet',id:'water-'+d.id,start:d.waterStart,duration:d.waterDuration,width:0,opacity:1,points:d.sources,color:[228,229,214],wetPatch:patch});
      passes.push({kind:'bloom',id:'pigment-'+d.id,start:d.start,duration:d.duration,width:0,opacity:1,points:d.sources,color:d.color,wetPatch:patch});
    });
    return passes;
  };
  window.drawWetMark=function (ctx,s,progress) {
    const p=clamp(progress),patch=s.wetPatch;if(!patch||p<=0)return;
    ctx.save();
    if(s.kind==='wet') {
      // Nearly invisible water precedes colour, then loses its sheen entirely.
      const shine=Math.sin(Math.PI*p)*.085;
      if(shine>0){ctx.clip(patch.path);const d=patch.definition,b=patch.box;
        const g=ctx.createLinearGradient(b[0],b[1],b[0]+b[2],b[1]+b[3]);
        g.addColorStop(0,'rgba(137,158,149,'+(shine*.28)+')');
        g.addColorStop(clamp(p*.8+.08,.01,.95),'rgba(255,255,246,'+(shine*1.8)+')');
        g.addColorStop(1,'rgba(141,158,150,'+(shine*.45)+')');
        ctx.fillStyle=g;ctx.fillRect(b[0],b[1],b[2],b[3]);
        ctx.lineWidth=.65;ctx.strokeStyle='rgba(250,253,240,'+(shine*.8)+')';ctx.stroke(patch.path);
      }
    } else {
      const at=p*(patch.frames.length-1),lo=Math.floor(at),mix=at-lo,b=patch.box;
      ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';
      if(mix>0){const blend=patch.blend,bg=blend.getContext('2d');
        bg.clearRect(0,0,blend.width,blend.height);bg.globalCompositeOperation='source-over';
        bg.globalAlpha=1-mix;bg.drawImage(patch.frames[lo],0,0);
        bg.globalCompositeOperation='lighter';bg.globalAlpha=mix;
        bg.drawImage(patch.frames[Math.min(lo+1,patch.frames.length-1)],0,0);
        bg.globalAlpha=1;bg.globalCompositeOperation='source-over';
        ctx.drawImage(blend,b[0],b[1],b[2],b[3]);
      } else ctx.drawImage(patch.frames[lo],b[0],b[1],b[2],b[3]);
    }
    ctx.restore();
  };
})();

/* Reference-guided dry-pigment reconstruction. The source is read only to choose
   each mark's colour and direction. Every returned item deposits a flat colour
   along a real polyline; no image, mask, raster reveal or final-image swap is used. */
