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
      stroke.seed=(stroke.points[0][0]*.738+stroke.points[0][1]*.393+stroke.start*17)%100;
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
      if(stroke.kind==='wet'||stroke.kind==='bloom'){drawSpeciesWet(context,stroke,progress);return;}
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
