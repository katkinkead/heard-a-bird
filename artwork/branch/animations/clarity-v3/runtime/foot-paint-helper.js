/* Registration-only helper for the reusable transparent bird layer.
   Does not alter portrait painting, score timing, source art, or source pixels.
   The subject canvas must still be clipped by the body + feet mask afterwards. */
(function(root){
  const inside=(x,y,poly)=>{let hit=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){
    const a=poly[i],b=poly[j];if((a[1]>y)!==(b[1]>y)&&x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])hit=!hit;
  }return hit;};
  const distance=(x,y,a,b)=>{const dx=b[0]-a[0],dy=b[1]-a[1],q=Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy||1)));return Math.hypot(x-a[0]-q*dx,y-a[1]-q*dy);};
  root.makeFootPaintClassifier=function(config,padding=1.25){
    const polys=config.feetPolys||[],boxes=polys.map(p=>[Math.min(...p.map(q=>q[0]))-padding,Math.min(...p.map(q=>q[1]))-padding,Math.max(...p.map(q=>q[0]))+padding,Math.max(...p.map(q=>q[1]))+padding]);
    return function(stroke){
      if(stroke.layer==='bird')return true;
      if(stroke.layer!=='perch')return false;
      const points=stroke.points||[],pad=Math.min(3,Math.max(padding,(stroke.width||1)/2));
      for(const [x,y] of points)for(let k=0;k<polys.length;k++){
        const b=boxes[k];if(x<b[0]-pad||x>b[2]+pad||y<b[1]-pad||y>b[3]+pad)continue;
        const p=polys[k];if(inside(x,y,p))return true;
        for(let i=0;i<p.length;i++)if(distance(x,y,p[i],p[(i+1)%p.length])<pad)return true;
      }
      return false;
    };
  };
})(typeof window==='undefined'?globalThis:window);
