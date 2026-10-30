/* Candidate v2: native-reference dry pigment and pencil reconstruction.
 * This produces coloured polylines only. It never draws the source raster.
 * Input pixels must be a registered 4:3 source at its native resolution;
 * output points use the collection's 1000 x 750 logical coordinates.
 * Timing is deliberately left to the caller. Approved originals remain immutable; revised copies also receive the finish.
 */
function buildClarityRefinement({pixels, width, height, config}) {

  const src = pixels.data || pixels, W = 1000, H = 750;
  const sx = width / W, sy = height / H, pixel = 1 / Math.max(sx, sy);
  const count = width * height, marks = [];
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const distance2 = (a, b) => (a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2;
  const bodyMask = new Uint8Array(count), mask = new Uint8Array(count);
  const regionMask = new Uint8Array(count), perchMask = new Uint8Array(count), painted = new Uint8Array(count);
  const edgeMask = new Uint8Array(count), flourishMask = new Uint8Array(count);
  const paintedR = new Uint8Array(count), paintedG = new Uint8Array(count), paintedB = new Uint8Array(count);
  const polygons = config.branchCutoutPolys || config.birdPolys || (config.birdPoly ? [config.birdPoly] : []);

  function fillPolygon(poly, target) {
    if (!poly || poly.length < 3) return;
    const lo = clamp(Math.floor(Math.min(...poly.map(p=>p[1]))*sy), 0, height-1);
    const hi = clamp(Math.ceil(Math.max(...poly.map(p=>p[1]))*sy), 0, height-1);
    for (let iy=lo; iy<=hi; iy++) {
      const y=(iy+.5)/sy, crosses=[];
      for(let i=0,j=poly.length-1;i<poly.length;j=i++) {
        const a=poly[j],b=poly[i];
        if((a[1]>y)!==(b[1]>y)) crosses.push((a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))*sx);
      }
      crosses.sort((a,b)=>a-b);
      for(let i=0;i+1<crosses.length;i+=2) {
        const x0=clamp(Math.ceil(crosses[i]-.5),0,width-1),x1=clamp(Math.floor(crosses[i+1]-.5),0,width-1);
        for(let x=x0;x<=x1;x++) target[iy*width+x]=1;
      }
    }
  }
  polygons.forEach(p=>fillPolygon(p,bodyMask));
  mask.set(bodyMask);
  (config.feetPolys||[]).forEach(p=>fillPolygon(p,mask));
  const footMask=mask.slice();
  for(let q=0;q<count;q++)if(bodyMask[q])footMask[q]=0;
  const boxOf=b=>Array.isArray(b)?b:b.box;
  const inBox=(x,y,b)=>b&&x>=b[0]&&x<=b[2]&&y>=b[1]&&y<=b[3];
  const inside=(x,y,e)=>{
    if(!e)return false;
    if(Array.isArray(e))e={cx:e[0],cy:e[1],rx:e[2],ry:e[3],angle:e[4]||0};
    const dx=x-e.cx,dy=y-e.cy,c=Math.cos(e.angle||0),s=Math.sin(e.angle||0);
    return ((dx*c+dy*s)/e.rx)**2+((-dx*s+dy*c)/e.ry)**2<1;
  };
  // Cover a narrow band of legacy coarse paint outside the registered body.
  // These are source-coloured correction strokes (paper/backdrop included),
  // explicitly portrait-only; they do not become part of a transparent bird.
  const authorMask=new Uint8Array(count);
  (config.birdPolys||(config.birdPoly?[config.birdPoly]:polygons)).forEach(p=>fillPolygon(p,authorMask));
  const boundaryDistance=new Float32Array(count),wx=1/sx,wy=1/sy,wd=Math.hypot(wx,wy);
  for(let q=0;q<count;q++)boundaryDistance[q]=authorMask[q]?0:1e5;
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
    const q=y*width+x;let d=boundaryDistance[q];
    if(x)d=Math.min(d,boundaryDistance[q-1]+wx);
    if(y)d=Math.min(d,boundaryDistance[q-width]+wy);
    if(x&&y)d=Math.min(d,boundaryDistance[q-width-1]+wd);
    if(x<width-1&&y)d=Math.min(d,boundaryDistance[q-width+1]+wd);
    boundaryDistance[q]=d;
  }
  for(let y=height-1;y>=0;y--)for(let x=width-1;x>=0;x--){
    const q=y*width+x;let d=boundaryDistance[q];
    if(x<width-1)d=Math.min(d,boundaryDistance[q+1]+wx);
    if(y<height-1)d=Math.min(d,boundaryDistance[q+width]+wy);
    if(x<width-1&&y<height-1)d=Math.min(d,boundaryDistance[q+width+1]+wd);
    if(x&&y<height-1)d=Math.min(d,boundaryDistance[q+width-1]+wd);
    boundaryDistance[q]=d;
    if(!mask[q]&&d<=(config.clarityEdgeHalo??8)){mask[q]=1;edgeMask[q]=1;}
  }
  // Authored extras boxes also contain the intentional loose ink contours.
  // Their dark core, plus one native-pixel antialiased edge, is eligible even
  // when it sits farther from the filled silhouette than the correction band.
  const inkSeeds=[];
  for(const item of config.extrasBoxes||[]){
    const b=boxOf(item);if(!b)continue;
    for(let y=clamp(Math.floor(b[1]*sy),0,height-1);y<=Math.min(height-1,Math.ceil(b[3]*sy));y++)
      for(let x=clamp(Math.floor(b[0]*sx),0,width-1);x<=Math.min(width-1,Math.ceil(b[2]*sx));x++){
        const q=y*width+x,i=q*4;
        if(!bodyMask[q]&&.213*src[i]+.715*src[i+1]+.072*src[i+2]<140)inkSeeds.push(q);
      }
  }
  for(const q of inkSeeds){
    const x=q%width,y=(q/width)|0;
    for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
      const nx=x+dx,ny=y+dy;if(nx<0||nx>=width||ny<0||ny>=height)continue;
      const n=ny*width+nx,i=n*4;
      if(!bodyMask[n]&&.213*src[i]+.715*src[i+1]+.072*src[i+2]<210){mask[n]=1;flourishMask[n]=1;edgeMask[n]=0;}
    }
  }
  // The reference perch is a narrow deposited ink line, never its whole box.
  // Trace only actual dark source samples inside explicitly registered boxes.
  for(const boxItem of config.perchBoxes||[]){
    const b=boxOf(boxItem);if(!b)continue;
    const xa=clamp(Math.floor(b[0]*sx),0,width-1),xb=clamp(Math.ceil(b[2]*sx),0,width-1);
    const ya=clamp(Math.floor(b[1]*sy),0,height-1),yb=clamp(Math.ceil(b[3]*sy),0,height-1);
    for(let y=ya;y<=yb;y++)for(let x=xa;x<=xb;x++){
      const q=y*width+x,i=q*4;
      if(!bodyMask[q]&&!footMask[q]&&.213*src[i]+.715*src[i+1]+.072*src[i+2]<175){mask[q]=1;perchMask[q]=1;flourishMask[q]=0;edgeMask[q]=0;}
    }
  }
  function anatomicalRegion(x,y,q) {
    if(perchMask[q]||footMask[q])return 6;
    if(!bodyMask[q]&&!edgeMask[q]&&!flourishMask[q])return 6;
    if(inside(x,y,config.head))return 0;
    if(inside(x,y,config.tail))return 5;
    if(inside(x,y,config.wing))return 3;
    if(y<config.body.cy-config.body.ry*.32)return 4;
    if(y>config.body.cy+config.body.ry*.23)return 2;
    return 1;
  }
  let x0=width,y0=height,x1=0,y1=0,insideCount=0;
  const excluded=[...(config.excludeBoxes||[]),...(config.textBoxes||[])].map(boxOf);
  for(let iy=0;iy<height;iy++)for(let ix=0;ix<width;ix++) {
    const q=iy*width+ix;if(!mask[q])continue;
    const x=(ix+.5)/sx,y=(iy+.5)/sy,i=q*4;
    if(excluded.some(b=>inBox(x,y,b))){mask[q]=0;continue;}
    if(!bodyMask[q]&&!perchMask[q]&&!edgeMask[q]&&!flourishMask[q]){
      const lo=Math.min(src[i],src[i+1],src[i+2]),hi=Math.max(src[i],src[i+1],src[i+2]);
      const paperMin=config.footPaperMin??(/owl/i.test(config.name||'')?239:205);
      if(lo>paperMin&&hi-lo<32){
        // Keep tiny ivory scales inside an otherwise dark/red leg. Detached
        // paper enclosed by a loose toe polygon has no such foreground support.
        let supported=false;
        const step=Math.max(1,Math.round(sx));
        for(const [dx,dy] of [[-step,0],[step,0],[0,-step],[0,step]]){
          const nx=ix+dx,ny=iy+dy;if(nx<0||nx>=width||ny<0||ny>=height)continue;
          const n=(ny*width+nx)*4;
          if(Math.min(src[n],src[n+1],src[n+2])<150){supported=true;break;}
        }
        if(!supported){mask[q]=0;continue;}
      }
    }
    regionMask[q]=anatomicalRegion(x,y,q);insideCount++;
    x0=Math.min(x0,ix);x1=Math.max(x1,ix);y0=Math.min(y0,iy);y1=Math.max(y1,iy);
  }
  if(!insideCount)return marks;
  const indexAt=(x,y)=>{
    const ix=Math.floor(x*sx),iy=Math.floor(y*sy);
    return ix>=0&&ix<width&&iy>=0&&iy<height?iy*width+ix:-1;
  };
  const allowed=(x,y)=>{const q=indexAt(x,y);return q>=0&&mask[q]===1;};
  function sample(x,y) {
    const fx=clamp(x*sx-.5,0,width-1.001),fy=clamp(y*sy-.5,0,height-1.001);
    const ix=fx|0,iy=fy|0,dx=fx-ix,dy=fy-iy,i=(iy*width+ix)*4,j=i+width*4;
    return [0,1,2].map(k=>src[i+k]*(1-dx)*(1-dy)+src[i+4+k]*dx*(1-dy)+src[j+k]*(1-dx)*dy+src[j+4+k]*dx*dy);
  }

  // RGB structure tensor, averaged over a 5x5 native-pixel neighborhood.
  // It follows continuous feather boundaries rather than the direction of an
  // isolated grain pixel. Luminance alone misses some coloured feather edges.
  const xx=new Float32Array(count),xy=new Float32Array(count),yy=new Float32Array(count);
  const contrast=new Float32Array(count),angle=new Float32Array(count),coherence=new Float32Array(count);
  for(let y=Math.max(1,y0-3);y<=Math.min(height-2,y1+3);y++)for(let x=Math.max(1,x0-3);x<=Math.min(width-2,x1+3);x++) {
    const q=y*width+x;let ax=0,ay=0,largest=-1;
    for(let k=0;k<3;k++){
      const gx=(src[(q+1)*4+k]-src[(q-1)*4+k])*.5,gy=(src[(q+width)*4+k]-src[(q-width)*4+k])*.5;
      if(gx*gx+gy*gy>largest){largest=gx*gx+gy*gy;ax=gx;ay=gy;}
    }
    xx[q]=ax*ax;xy[q]=ax*ay;yy[q]=ay*ay;contrast[q]=Math.sqrt(largest);
  }
  function boxMean(input) {
    const horizontal=new Float32Array(count),result=new Float32Array(count);
    const xa=Math.max(0,x0-3),xb=Math.min(width-1,x1+3),ya=Math.max(0,y0-3),yb=Math.min(height-1,y1+3);
    for(let y=ya;y<=yb;y++) {
      let sum=0;for(let k=-2;k<=2;k++)sum+=input[y*width+clamp(xa+k,0,width-1)];
      for(let x=xa;x<=xb;x++){
        horizontal[y*width+x]=sum/5;
        sum+=input[y*width+clamp(x+3,0,width-1)]-input[y*width+clamp(x-2,0,width-1)];
      }
    }
    for(let x=xa;x<=xb;x++){
      let sum=0;for(let k=-2;k<=2;k++)sum+=horizontal[clamp(ya+k,0,height-1)*width+x];
      for(let y=ya;y<=yb;y++){
        result[y*width+x]=sum/5;
        sum+=horizontal[clamp(y+3,0,height-1)*width+x]-horizontal[clamp(y-2,0,height-1)*width+x];
      }
    }
    return result;
  }
  const axx=boxMean(xx),axy=boxMean(xy),ayy=boxMean(yy);
  for(let q=0;q<count;q++)if(mask[q]){
    const difference=Math.hypot(axx[q]-ayy[q],2*axy[q]);
    coherence[q]=difference/(axx[q]+ayy[q]+.0001);
    angle[q]=.5*Math.atan2(2*axy[q],axx[q]-ayy[q])+Math.PI/2;
  }
  function anatomyDirection(x,y,q) {
    const r=regionMask[q];
    let a=(r===5?config.tail:r===3?config.wing:config.body)?.angle||0;
    if(r===0){const h=config.head;a=Math.atan2((y-h.cy)/h.ry,(x-h.cx)/h.rx)+Math.PI/2;}
    for(const r of config.directionRegions||[])if(inBox(x,y,r.box)){a=r.angle;break;}
    return a;
  }
  function tangent(x,y,previous) {
    const q=indexAt(x,y);if(q<0)return previous||0;
    let a=coherence[q]>.18?angle[q]:anatomyDirection(x,y,q);
    if(Number.isFinite(previous)){
      while(a-previous>Math.PI/2)a-=Math.PI;
      while(a-previous< -Math.PI/2)a+=Math.PI;
      // Limit sudden changes in direction so paper grain cannot kink a feather.
      a=previous+clamp(a-previous,-.32,.32);
    }
    return a;
  }
  function acceptable(x,y,colour,tolerance2) {
    return allowed(x,y)&&distance2(sample(x,y),colour)<=tolerance2;
  }
  function footprint(x,y,a,breadth,colour,tolerance2) {
    if(!acceptable(x,y,colour,tolerance2))return false;
    const nx=-Math.sin(a),ny=Math.cos(a);
    for(const f of [-.47,-.24,.24,.47])if(!acceptable(x+nx*breadth*f,y+ny*breadth*f,colour,tolerance2))return false;
    return true;
  }
  function makeStroke(x,y,stage) {
    const q=indexAt(x,y);if(q<0||!mask[q])return null;
    const colour=sample(x,y),a=tangent(x,y),edge=contrast[q];
    const tolerance=stage==='coverage'?27:17,tolerance2=tolerance*tolerance;
    const widths=stage==='coverage'?[2.6,1.8,1.2,.82,.58]:[1.08,.78,.56,.40];
    let breadth=widths[widths.length-1];
    for(const w of widths)if(footprint(x,y,a,w,colour,tolerance2)){breadth=w;break;}
    const maxLength=stage==='coverage'?(edge<9?9:5.5):9.5;
    const step=Math.min(.43,pixel*.65),sides=[];
    for(const sign of [-1,1]){
      const side=[];let px=x,py=y,pa=a;
      for(let distance=step;distance<=maxLength*.5;distance+=step){
        const nextA=tangent(px,py,pa),nx=px+Math.cos(nextA)*step*sign,ny=py+Math.sin(nextA)*step*sign;
        if(!footprint(nx,ny,nextA,breadth,colour,tolerance2))break;
        // Test beyond the endpoint for the round cap as well as across its width.
        if(!acceptable(nx+Math.cos(nextA)*breadth*.43*sign,ny+Math.sin(nextA)*breadth*.43*sign,colour,tolerance2))break;
        side.push([nx,ny]);px=nx;py=ny;pa=nextA;
      }
      sides.push(side);
    }
    const points=[...sides[0].reverse(),[x,y],...sides[1]];
    if(points.length===1){
      // A single subpixel colour accent is still a short deposited stroke.
      const d=Math.min(.12,breadth*.22);
      points.unshift([x-Math.cos(a)*d,y-Math.sin(a)*d]);
      points.push([x+Math.cos(a)*d,y+Math.sin(a)*d]);
    }
    // Preserve curvature but omit redundant collinear intermediate vertices.
    const simplified=[points[0]];
    for(let i=1;i<points.length-1;i++){
      const p=simplified[simplified.length-1],z=points[i],n=points[i+1];
      const area=Math.abs((z[0]-p[0])*(n[1]-p[1])-(z[1]-p[1])*(n[0]-p[0]));
      const length=Math.hypot(n[0]-p[0],n[1]-p[1]);
      if(area/Math.max(.01,length)>.035||Math.hypot(z[0]-p[0],z[1]-p[1])>1.7)simplified.push(z);
    }
    simplified.push(points[points.length-1]);
    return {points:simplified,color:colour.map(Math.round),width:breadth,opacity:1,
      kind:'pencil',profile:'flat',finishStyle:'reference',clarityStage:stage,
      region:regionMask[q],pass:stage==='coverage'?1:2,clarityVersion:2,
      clarityRole:perchMask[q]?'perch':edgeMask[q]?'edge-correction':'bird',
      clarityRegion:['head','breast','lower breast','patterned wing','shoulder','tail','feet'][regionMask[q]],
      ...(edgeMask[q]?{clarityAfter:67}:{} )};
  }
  // Coverage is evaluated at native pixel centres. Use only the inner 82% of
  // the footprint for bookkeeping, so adjacent strokes overlap their antialiased
  // edges instead of leaving the gaps that existed in the old jittered grid.
  function deposit(stroke) {
    const ps=stroke.points,radius=stroke.width*.41,r2=radius*radius,c=stroke.color;
    for(let j=1;j<ps.length;j++){
      const a=ps[j-1],b=ps[j],dx=b[0]-a[0],dy=b[1]-a[1],d2=dx*dx+dy*dy;
      const xa=clamp(Math.floor((Math.min(a[0],b[0])-radius)*sx),x0,x1),xb=clamp(Math.ceil((Math.max(a[0],b[0])+radius)*sx),x0,x1);
      const ya=clamp(Math.floor((Math.min(a[1],b[1])-radius)*sy),y0,y1),yb=clamp(Math.ceil((Math.max(a[1],b[1])+radius)*sy),y0,y1);
      for(let iy=ya;iy<=yb;iy++)for(let ix=xa;ix<=xb;ix++){
        const q=iy*width+ix;if(!mask[q])continue;
        const x=(ix+.5)/sx,y=(iy+.5)/sy,t=clamp(((x-a[0])*dx+(y-a[1])*dy)/(d2||1),0,1);
        if((x-a[0]-t*dx)**2+(y-a[1]-t*dy)**2>r2)continue;
        painted[q]=1;paintedR[q]=c[0];paintedG[q]=c[1];paintedB[q]=c[2];
      }
    }
  }
  function needsPaint(q,tolerance) {
    if(!painted[q])return true;
    const i=q*4;return (src[i]-paintedR[q])**2+(src[i+1]-paintedG[q])**2+(src[i+2]-paintedB[q])**2>tolerance*tolerance;
  }
  function add(x,y,stage){const m=makeStroke(x,y,stage);if(m){marks.push(m);deposit(m);}}

  // Broad, accurate pigment first. Offset alternate rows to avoid grid seams;
  // positions and every later decision are deterministic (no random omissions).
  const coarseStep=2.15;
  for(let row=0,y=(y0+.5)/sy;y<=(y1+.5)/sy;y+=coarseStep,row++){
    for(let x=(x0+.5)/sx+(row%2)*coarseStep*.5;x<=(x1+.5)/sx;x+=coarseStep){
      const q=indexAt(x,y);if(q>=0&&mask[q]&&needsPaint(q,20))add(x,y,'coverage');
    }
  }
  // Fill remaining low/medium-contrast gaps at native resolution. Fine edges
  // intentionally wait for the pencil stage, rather than being glazed away.
  for(let iy=y0;iy<=y1;iy++)for(let ix=x0;ix<=x1;ix++){
    const q=iy*width+ix;
    if(mask[q]&&contrast[q]<19&&needsPaint(q,23))add((ix+.5)/sx,(iy+.5)/sy,'coverage');
  }
  // Deterministic detail visits: strongest source edges first, then intermediate
  // feather lines, then any still-uncovered sample. Residual colour checks stop
  // this from becoming an indiscriminate stroke at every source pixel.
  for(const [lo,hi,tolerance] of [[38,Infinity,9],[17,38,11],[0,17,14]]){
    for(let iy=y0;iy<=y1;iy++)for(let ix=x0;ix<=x1;ix++){
      const q=iy*width+ix;
      if(mask[q]&&contrast[q]>=lo&&contrast[q]<hi&&needsPaint(q,tolerance))add((ix+.5)/sx,(iy+.5)/sy,'detail');
    }
  }
  return marks;
}

if (typeof module!=='undefined' && module.exports) module.exports={buildClarityRefinement};
