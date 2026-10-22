/* Canvas painting engine. The source is sampled offscreen; only authored and
   source-guided marks reach the output. The transparent subject uses the exact
   same clock and strokes as the portrait, clipped to its registered silhouette. */
(function(){
  const W=1000,H=750,D=75;
  const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
  const makeCanvas=()=>Object.assign(document.createElement('canvas'),{width:W,height:H});
  const pending=new Map();
  const scorePending=new Map();
  window.BirdsongScores={receive(id,key,gzip){scorePending.get(id)?.resolve({key,gzip});}};
  async function compiledScore(config){
    if(!config.scoreFile||!window.DecompressionStream)return null;
    let promise=scorePending.get(config.id)?.promise;
    if(!promise){let resolve,reject;promise=new Promise((a,b)=>{resolve=a;reject=b;});scorePending.set(config.id,{promise,resolve,reject});
      const script=document.createElement('script');script.src=config.scoreFile;script.onerror=()=>reject(Error('Prepared score unavailable'));script.onload=()=>script.remove();document.head.append(script);}
    try{const packet=await promise;if(packet.key!==config.scoreKey)return null;const binary=atob(packet.gzip),bytes=new Uint8Array(binary.length);for(let i=0;i<bytes.length;i++)bytes[i]=binary.charCodeAt(i);
      return await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).json();
    }catch{return null;}finally{scorePending.delete(config.id);}
  }
  window.BirdsongAssets={receive(packet){pending.get(packet.config.id)?.resolve(packet);}};
  window.loadBirdsongAsset=async function(id){
    if(pending.has(id))return pending.get(id).promise;
    let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});
    pending.set(id,{promise,resolve,reject});
    const script=document.createElement('script');script.src='species/'+id+'.js';
    script.onerror=()=>{pending.delete(id);reject(Error('Could not load '+id));};
    script.onload=()=>script.remove();document.head.append(script);
    return promise;
  };
  window.decodeBirdsongImage=src=>new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>resolve(image);image.onerror=reject;image.src=src;});
  let livePromise,materialCache;
  async function liveMarks(){
    if(!livePromise)livePromise=(async()=>{
      const asset=await loadBirdsongAsset('robin'),im=await decodeBirdsongImage(asset.source),c=makeCanvas(),g=c.getContext('2d',{willReadFrequently:true});g.drawImage(im,0,0,W,H);
      return buildSpeciesFinish({pixels:g.getImageData(0,0,W,H).data,width:W,height:H,config:{birdPoly:[],extrasBoxes:[],backgroundBoxes:[],focalBoxes:[],textBoxes:[{box:[905,695,991,720],limit:158,start:88.2,end:89.7,label:'Singing now'},{box:[925,675,972,697],limit:189,start:87.8,end:88.8,label:'Live ripple'}]}});
    })();
    return (await livePromise).map(s=>({...s,points:s.points.map(p=>[...p])}));
  }
  window.createBirdsongPainter=async function(packet){
    const config=packet.config;
    const canvas=makeCanvas(),ctx=canvas.getContext('2d'),birdCanvas=makeCanvas(),birdCtx=birdCanvas.getContext('2d');
    const paper=makeCanvas(),grain=makeCanvas(),reference=makeCanvas(),painting=makeCanvas(),sketch=makeCanvas(),subjectPaint=makeCanvas(),subjectSketch=makeCanvas(),mask=makeCanvas();
    const paperCtx=paper.getContext('2d'),grainCtx=grain.getContext('2d'),refCtx=reference.getContext('2d',{willReadFrequently:true}),paintCtx=painting.getContext('2d'),sketchCtx=sketch.getContext('2d'),subjectCtx=subjectPaint.getContext('2d'),subjectSketchCtx=subjectSketch.getContext('2d'),maskCtx=mask.getContext('2d');
    if(materialCache){paperCtx.drawImage(materialCache.paper,0,0);grainCtx.drawImage(materialCache.grain,0,0);}else{
    let seeded=91371;const random=()=>{seeded=(1664525*seeded+1013904223)>>>0;return seeded/4294967296;};
    paperCtx.fillStyle='#f3eee5';paperCtx.fillRect(0,0,W,H);
    for(let i=0;i<65000;i++){const x=random()*W,y=random()*H,r=.25+random()*1.3;paperCtx.fillStyle=`rgba(${random()>.5?'255,253,247':'110,96,73'},${.018+random()*.06})`;paperCtx.beginPath();paperCtx.ellipse(x,y,r,r*.48,random()*Math.PI,0,Math.PI*2);paperCtx.fill();}
    for(let i=0;i<105000;i++){const x=random()*W,y=random()*H,r=.2+random()*.8;grainCtx.fillStyle=`rgba(${random()>.22?'250,242,222':'57,54,43'},${.025+random()*.11})`;grainCtx.fillRect(x,y,r,r*.6);}
      materialCache={paper,grain};
    }
    const img=await decodeBirdsongImage(packet.source);
    refCtx.fillStyle='#f3eee5';refCtx.fillRect(0,0,W,H);refCtx.drawImage(img,...config.sourceCrop,...config.destRect);
    const pixels=refCtx.getImageData(0,0,W,H).data;
    let strokes;const compiled=await compiledScore(config);
    if(compiled){
      const patches=new Map();
      strokes=compiled.strokes.map(s=>{if(s.wetDefinition){const key=s.wetDefinition.id;if(!patches.has(key))patches.set(key,config.goldfinchOriginal?buildWetPass().find(m=>m.wetPatch.definition.id===key).wetPatch:restoreSpeciesWet(s.wetDefinition));s.wetPatch=patches.get(key);delete s.wetDefinition;}return s;});
    }
    else if(config.goldfinchOriginal){strokes=buildApprovedGoldfinch(pixels);}
    else{
      const opening=buildSpeciesOpening({pixels,width:W,height:H,config});
      let sketchIndex=0;
      for(const s of opening)if(s.kind==='graphite')s.layer=config.sketchRoles?.[sketchIndex++]||'bird';
      strokes=[...opening,...buildSpeciesFinish({pixels,width:W,height:H,config})];
      if(config.approvedOriginal)strokes.push(...await liveMarks());
      const adapters={robin:retimeRobin,wren:retimeWren,blackbird:retimeBlackbird,'blue-tit':retimeBlueTit};
      (config.approvedOriginal?adapters[config.id]:retimeCollectionBird)(strokes,config);
    }
    let fluidity=.78;
        function resample(stroke){
      if(stroke.kind==='wet'||stroke.kind==='bloom'){stroke.end=stroke.start+stroke.duration;return;}
      if(stroke.finishStyle==='reference'){
        let length=0;stroke.prepared=stroke.points.map((p,i)=>{if(i)length+=Math.hypot(p[0]-stroke.points[i-1][0],p[1]-stroke.points[i-1][1]);return{x:p[0],y:p[1],distance:length};});
        stroke.length=length;for(const p of stroke.prepared)p.q=p.distance/(length||1);
        stroke.end=stroke.start+stroke.duration;stroke.cssColor=`rgb(${stroke.color.map(Math.round).join(',')})`;return;
      }
      const source=stroke.points,points=[];
      for(let j=0;j<source.length-1;j++){
        const a=source[Math.max(0,j-1)],b=source[j],c=source[j+1],d=source[Math.min(source.length-1,j+2)];
        const steps=Math.max(2,Math.ceil(Math.hypot(c[0]-b[0],c[1]-b[1])/2));
        for(let k=0;k<steps;k++){
          const t=k/steps,t2=t*t,t3=t2*t;
          points.push([0,1].map(axis=>.5*((2*b[axis])+(-a[axis]+c[axis])*t+(2*a[axis]-5*b[axis]+4*c[axis]-d[axis])*t2+(-a[axis]+3*b[axis]-3*c[axis]+d[axis])*t3)));
        }
      }
      points.push(source[source.length-1]);
      let dist=0;const prepared=[];
      for(let i=0;i<points.length;i++){
        const p=points[i],a=points[Math.max(0,i-1)],b=points[Math.min(points.length-1,i+1)];
        if(i)dist+=Math.hypot(p[0]-points[i-1][0],p[1]-points[i-1][1]);
        prepared.push({x:p[0],y:p[1],distance:dist,angle:Math.atan2(b[1]-a[1],b[0]-a[0])});
      }
      stroke.length=dist;stroke.prepared=prepared;
      for(const p of prepared)p.q=p.distance/(dist||1);
      stroke.end=stroke.start+stroke.duration;
      stroke.seed=(stroke.points[0][0]*.738+stroke.points[0][1]*.393+(stroke.blueTitOriginalStart??stroke.goldfinchOriginalStart??stroke.start)*17)%100;
      if(stroke.kind==='wash'||stroke.kind==='paint'){
        const costs=[0];let total=0;
        for(let j=1;j<=80;j++){const q=j/80;total+=1+.95*Math.exp(-Math.pow((q-(stroke.pressAt||.38))/.12,2));costs.push(total);}
        stroke.pressureTiming=costs.map(v=>v/total);
      }
    }
    function smoothAt(points,index){
      const p=points[index];if(index===0||index===points.length-1)return p;
      const a=points[index-1],b=points[index+1];
      return {x:p.x*(1-fluidity*.46)+(a.x+b.x)*fluidity*.23,y:p.y*(1-fluidity*.46)+(a.y+b.y)*fluidity*.23,angle:p.angle,q:p.q};
    }
    const pigmentTiles=new Map();
    function pigmentTexture(color){
      const rgb=color.map(v=>Math.round(v/8)*8),feel=Math.round(fluidity*5),key=rgb.join(',')+':'+feel;
      if(pigmentTiles.has(key))return pigmentTiles.get(key);
      const tile=document.createElement('canvas');tile.width=96;tile.height=96;
      const tc=tile.getContext('2d'),d=tc.createImageData(96,96);
      for(let y=0;y<96;y++)for(let x=0;x<96;x++){
        const i=(y*96+x)*4,v=Math.sin(x*12.9898+y*78.233)*43758.5453,n=v-Math.floor(v);
        d.data[i]=rgb[0];d.data[i+1]=rgb[1];d.data[i+2]=rgb[2];
        d.data[i+3]=n<.09-feel*.016?28:Math.round(180+n*75);
      }
      tc.putImageData(d,0,0);const pattern=ctx.createPattern(tile,'repeat');pigmentTiles.set(key,pattern);return pattern;
    }
    function drawMark(context,stroke,progress){
      if(progress<=0)return;
      if(stroke.kind==='wet'||stroke.kind==='bloom'){(config.goldfinchOriginal?drawWetMark:drawSpeciesWet)(context,stroke,progress);return;}
      if(stroke.finishStyle==='reference'){
        const ps=stroke.prepared;context.strokeStyle=stroke.cssColor;context.lineWidth=stroke.width;context.lineCap='round';context.lineJoin='round';context.globalAlpha=stroke.opacity;
        context.beginPath();context.moveTo(ps[0].x,ps[0].y);
        for(let i=1;i<ps.length;i++){const a=ps[i-1],b=ps[i];if(b.q<=progress)context.lineTo(b.x,b.y);else{const u=clamp((progress-a.q)/(b.q-a.q||1));context.lineTo(a.x+(b.x-a.x)*u,a.y+(b.y-a.y)*u);break;}}
        context.stroke();context.globalAlpha=1;return;
      }
      const p=stroke.prepared,n=p.length;
      let motion=progress*(1-fluidity*.85)+progress*progress*(3-2*progress)*fluidity*.85;
      if(stroke.pressureTiming){const v=stroke.pressureTiming;let k=1;while(k<v.length-1&&v[k]<motion)k++;motion=((k-1)+(motion-v[k-1])/(v[k]-v[k-1]||1))/80;}
      let count=1;while(count<n&&p[count].q<=motion)count++;
      const pts=[];
      for(let i=0;i<count;i++)pts.push(smoothAt(p,i));
      if(count<n){const a=p[count-1],b=p[count],u=(motion-a.q)/(b.q-a.q||1);let da=b.angle-a.angle;while(da>Math.PI)da-=Math.PI*2;while(da<-Math.PI)da+=Math.PI*2;pts.push({x:a.x+(b.x-a.x)*u,y:a.y+(b.y-a.y)*u,angle:a.angle+da*u,q:motion});}
      if(pts.length<2)return;
      const graphite=stroke.kind==='graphite',wash=stroke.kind==='wash',pencil=stroke.kind==='pencil',ink=stroke.kind==='ink'||pencil;
      const pigment=stroke.opacity*(graphite?1:(.87+fluidity*.13));
      const color=stroke.color.map(v=>Math.round(v));
      context.fillStyle=graphite||ink?`rgba(${color.join(',')},${pigment})`:pigmentTexture(color);
      const widths=[];
      for(let i=0;i<pts.length;i++){
        const q=pts[i].q;
        const press=Math.exp(-Math.pow((q-(stroke.pressAt||.38))/.105,2));
        const lift=stroke.profile==='flat'?(.95+.05*Math.sin(q*12)):
          graphite||ink?Math.pow(Math.max(.001,Math.sin(Math.PI*q)),.45):
          (.10+.76*Math.pow(Math.max(.001,Math.sin(Math.PI*q)),1.15)+.32*press)*(.12+.88*Math.min(1,(1-q)/.10));
        const breath=.83+.13*Math.sin(q*6.2+stroke.seed)+.04*Math.cos(q*15.7+stroke.seed);
        const tooth=(.025+(1-fluidity)*.15)*Math.sin(q*stroke.length*.65+stroke.seed);
        widths.push(stroke.width*(.04+.96*lift)*breath*(1+tooth)*(graphite||ink?1:.88+fluidity*.18));
      }
      context.beginPath();
      for(let i=0;i<pts.length;i++){
        const z=pts[i],w=widths[i]/2;
        const jitter=(1-fluidity)*Math.sin(z.q*stroke.length*.35+stroke.seed)*(graphite?.38:.18);
        const x=z.x-Math.sin(z.angle)*(w+jitter),y=z.y+Math.cos(z.angle)*(w+jitter);
        if(!i)context.moveTo(x,y);else context.lineTo(x,y);
      }
      for(let i=pts.length-1;i>=0;i--){const z=pts[i],w=widths[i]/2;context.lineTo(z.x+Math.sin(z.angle)*w,z.y-Math.cos(z.angle)*w);}
      context.closePath();
      if(!graphite&&!ink&&stroke.profile!=='flat'){
        const a=p[0],b=p[p.length-1],g=context.createLinearGradient(a.x,a.y,b.x,b.y);
        const load=stroke.pigmentLoad||1;
        const peak=stroke.pressAt||.38;
        for(const [q,amount] of [[0,.22],[peak-.15,.46],[peak,.98],[peak+.18,.73],[.86,.39],[1,.14]])g.addColorStop(q,`rgba(${color.join(',')},${pigment*amount*load})`);
        context.fillStyle=g;context.fill();
        context.fillStyle=pigmentTexture(color);context.globalAlpha=pigment*.18;context.fill();context.globalAlpha=1;
      }else{context.globalAlpha=graphite||ink?1:pigment;context.fill();context.globalAlpha=1;}
      if(graphite||wash||(!ink&&stroke.width>4)){
        const hairs=graphite?3:(wash?9:7);
        context.strokeStyle=`rgba(${color.join(',')},${pigment*(graphite?.20:.13)*(1-fluidity*.6)})`;
        context.lineWidth=graphite?.4:.55;
        for(let h=0;h<hairs;h++){
          const offset=((h/(hairs-1))-.5)*1.16;
          context.beginPath();
          for(let i=0;i<pts.length;i++){
            const z=pts[i],w=widths[i]*offset;
            const x=z.x-Math.sin(z.angle)*w,y=z.y+Math.cos(z.angle)*w;
            if(!i)context.moveTo(x,y);else context.lineTo(x,y);
          }
          context.stroke();
        }
      }
    }

    const inBox=(x,y,b)=>x>=b[0]&&x<=b[2]&&y>=b[1]&&y<=b[3];
    const centre=s=>{const ps=s.points||[];return ps.reduce((a,p)=>[a[0]+p[0]/ps.length,a[1]+p[1]/ps.length],[0,0]);};
    function role(s){
      const phrase=s.pacingPhrase||s.robinPacingPhrase||s.wrenPacingPhrase||s.blackbirdPacingPhrase||s.blueTitPacingPhrase||s.goldfinchPacingPhrase||'';
      if(s.contextSection){
        if(/background|geometry|tooth/.test(s.contextSection))return 'background';
        if(/Singing|ripple|Live/.test(s.contextSection))return 'status';
        return 'name';
      }
      if(phrase==='background')return 'background';
      if(phrase==='name'||phrase==='status')return phrase;
      if(phrase==='perch')return 'perch';
      if(s.layer==='perch')return 'perch';
      return 'bird';
    }
    for(const s of strokes){s.layer=role(s);resample(s);}
    const graphite=strokes.filter(s=>s.kind==='graphite'),sorted=strokes.filter(s=>s.kind!=='graphite').sort((a,b)=>a.start-b.start||a.end-b.end);
    // This mask contains only deposited paint, never pixels from the reference.
    const polyPath=poly=>{const p=new Path2D();poly.forEach(([x,y],i)=>i?p.lineTo(x,y):p.moveTo(x,y));p.closePath();return p;};
    maskCtx.fillStyle='#fff';
    for(const p of config.branchCutoutPolys||config.birdPolys||[config.birdPoly])if(p?.length)maskCtx.fill(polyPath(p));
    const bodyAlpha=maskCtx.getImageData(0,0,W,H).data;
    if(config.feetPolys?.length){for(const p of config.feetPolys)maskCtx.fill(polyPath(p));}
    else{
      // Old approved profiles did not include cutout polygons. Use their authored
      // foot gestures as narrow masks, avoiding the rectangular perch sampling areas.
      maskCtx.strokeStyle='#fff';maskCtx.lineWidth=10;maskCtx.lineCap='round';maskCtx.lineJoin='round';
      for(const s of graphite){const [x,y]=centre(s);if((config.feetBoxes||[]).some(b=>inBox(x,y,b))){maskCtx.beginPath();s.points.forEach((p,i)=>i?maskCtx.lineTo(...p):maskCtx.moveTo(...p));maskCtx.stroke();}}
    }
    // Foot polygons include the lift of a claw, but may enclose tiny slivers of
    // ivory source paper. Reject those neutral paper samples outside the body.
    // Pale feathered owl tarsi retain a higher threshold.
    const footMask=maskCtx.getImageData(0,0,W,H),paperMin=config.footPaperMin??(/owl/i.test(config.name)?239:205);
    for(let i=0;i<footMask.data.length;i+=4){if(bodyAlpha[i+3]||!footMask.data[i+3])continue;const lo=Math.min(pixels[i],pixels[i+1],pixels[i+2]),hi=Math.max(pixels[i],pixels[i+1],pixels[i+2]);if(lo>paperMin&&hi-lo<32)footMask.data[i+3]=0;}
    maskCtx.putImageData(footMask,0,0);
    let previous=-1,complete=-1,sketchTime=-1,time=75;
    function renderAt(t,reset=false){
      time=clamp(t,0,D);
      if(reset||time<previous){
        // Reset drawing state as well as pixels. Reference-pencil marks set
        // round line caps; those must not leak into an earlier wash on replay.
        painting.width=W;subjectPaint.width=W;sketch.width=W;subjectSketch.width=W;
        complete=-1;sketchTime=-1;
      }
      for(let i=complete+1;i<sorted.length;i++){const s=sorted[i];if(s.end>time)break;drawMark(paintCtx,s,1);if(s.layer==='bird')drawMark(subjectCtx,s,1);complete=i;}
      if(reset||sketchTime<20||time<20){
        sketchCtx.clearRect(0,0,W,H);subjectSketchCtx.clearRect(0,0,W,H);
        for(const s of graphite)if(s.start<time){const p=clamp((time-s.start)/s.duration);drawMark(sketchCtx,s,p);if(s.layer==='bird')drawMark(subjectSketchCtx,s,p);}
        sketchTime=time;
      }
      ctx.clearRect(0,0,W,H);ctx.drawImage(paper,0,0);ctx.save();ctx.globalAlpha=1-.96*clamp((time-28)/27);ctx.drawImage(sketch,0,0);ctx.restore();ctx.drawImage(painting,0,0);
      birdCtx.clearRect(0,0,W,H);birdCtx.save();birdCtx.globalAlpha=1-.96*clamp((time-28)/27);birdCtx.drawImage(subjectSketch,0,0);birdCtx.restore();birdCtx.drawImage(subjectPaint,0,0);
      for(let i=complete+1;i<sorted.length;i++){const s=sorted[i];if(s.start>time)break;const p=clamp((time-s.start)/s.duration);drawMark(ctx,s,p);if(s.layer==='bird')drawMark(birdCtx,s,p);}
      ctx.save();ctx.globalAlpha=1-.65*clamp((time-30)/25);ctx.drawImage(grain,0,0);ctx.restore();
      birdCtx.save();birdCtx.globalCompositeOperation='destination-in';birdCtx.drawImage(mask,0,0);birdCtx.restore();
      previous=time;return canvas;
    }
    renderAt(75,true);
    return {config,canvas,birdCanvas,paper,reference,renderAt,
      setFluidity(f){const next=clamp(f);if(next===fluidity)return;fluidity=next;pigmentTiles.clear();renderAt(time,true);},
      getState(){return {id:config.id,time,fluidity,duration:75,preparedScore:!!compiled,strokeCount:strokes.length,completed:strokes.filter(s=>s.end<=time).length};},
      exportScore(){return JSON.stringify({key:config.scoreKey,strokes:strokes.map(s=>{const m={...s};for(const k of ['prepared','length','cssColor','end','seed','pressureTiming'])delete m[k];if(m.wetPatch){m.wetDefinition=m.wetPatch.definition;delete m.wetPatch;}return m;})});},
      schedule(){return strokes.map(s=>({kind:s.kind,layer:s.layer,pass:s.pass,phrase:s.pacingPhrase||s.robinPacingPhrase||s.wrenPacingPhrase||s.blackbirdPacingPhrase||s.blueTitPacingPhrase||s.goldfinchPacingPhrase,start:s.start,end:s.end}));},
      integrity(){return {finishedImageReveals:false,birdLayerReusesPortraitStrokes:true,waterPatches:strokes.filter(s=>s.kind==='wet').length,pigmentPatches:strokes.filter(s=>s.kind==='bloom').length,layers:[...new Set(strokes.map(s=>s.layer))]};}
    };
  };
})();
