/* Local, seeded painted wood. The advancing edge deposits geometry; no bitmap
   or opacity mask is revealed. World units are the screen's 1600 x 900 units. */
(function () {
  'use strict';
  function random(seed) {
    let state = (Number(seed) || 1) >>> 0;
    return function () {
      state += 0x6D2B79F5;
      let t = Math.imul(state ^ (state >>> 15), 1 | state);
      t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
  const mix = (a, b, t) => a + (b - a) * t;
  const distance = (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1]);
  function makePath(inputPoints, widthStart, widthEnd, seed) {
    const points = (inputPoints || []).map(p => [+p[0], +p[1]])
      .filter((p, i, all) => p.every(Number.isFinite) && (!i || distance(p, all[i - 1]) > .01));
    if (points.length < 2) return { length: 0, draw() {} };
    widthStart = Math.max(.3, +widthStart || 1);
    widthEnd = Math.max(.2, +widthEnd || .2);
    const rand = random(seed), spine = [points[0]];
    const appendLine = point => {
      const from = spine[spine.length - 1], count = Math.max(1, Math.ceil(distance(from, point) / 2.1));
      for (let j = 1; j <= count; j++) spine.push([mix(from[0], point[0], j / count), mix(from[1], point[1], j / count)]);
    };
    // Round only a small neighbourhood of a joint. The overall angular anatomy
    // stays intact; this is not a spline through all the branch control points.
    for (let i = 1; i < points.length - 1; i++) {
      const previous = points[i - 1], joint = points[i], next = points[i + 1];
      const before = distance(previous, joint), after = distance(joint, next);
      const radius = Math.min(12, widthStart * .55, before * .12, after * .12);
      const a = [mix(joint[0], previous[0], radius / before), mix(joint[1], previous[1], radius / before)];
      const b = [mix(joint[0], next[0], radius / after), mix(joint[1], next[1], radius / after)];
      appendLine(a);
      for (let k = 1; k <= 8; k++) {
        const t = k / 8, u = 1 - t;
        spine.push([u*u*a[0] + 2*u*t*joint[0] + t*t*b[0], u*u*a[1] + 2*u*t*joint[1] + t*t*b[1]]);
      }
    }
    appendLine(points[points.length - 1]);
    const lengths = [0];
    for (let i = 1; i < spine.length; i++) lengths.push(lengths[i-1] + distance(spine[i-1], spine[i]));
    const length = lengths[lengths.length - 1];
    const phases = Array.from({length: 6}, () => rand() * Math.PI * 2);
    function at(s) {
      s = clamp(s, 0, length);
      let lo = 0, hi = lengths.length - 1;
      while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (lengths[mid] < s) lo = mid; else hi = mid; }
      const a = spine[lo], b = spine[hi], t = (s - lengths[lo]) / Math.max(.0001, lengths[hi] - lengths[lo]);
      const angle = Math.atan2(b[1] - a[1], b[0] - a[0]);
      // Slow asymmetric pressure gives substantial connected wood, while the
      // restrained high-frequency term breaks the otherwise perfect silhouette.
      const pressure = 1 + .055*Math.sin(s*.043+phases[0]) + .035*Math.sin(s*.19+phases[1]);
      const width = mix(widthStart, widthEnd, Math.pow(s / length, .88)) * pressure;
      return { x: mix(a[0],b[0],t), y: mix(a[1],b[1],t), nx: -Math.sin(angle), ny: Math.cos(angle), angle, width, s };
    }
    function edgeOffset(s, side) {
      return 1 + .045*Math.sin(s*.7+phases[side>0?2:3]) + .025*Math.sin(s*1.77+phases[side>0?4:5]);
    }
    function tipScale(s,tip) {
      if(tip>=length-.001)return 1;
      const lift=clamp(at(tip).width*.72,9,18);
      return Math.pow(clamp((tip-s)/lift,0,1),.72);
    }
    function offsetPoint(s, fraction, tip, factor) {
      const p = at(s);
      // The short travelling brush tip has a soft lift, not a rectangular cutoff.
      const tipPressure = tipScale(s,tip);
      const off = fraction * p.width * .5 * factor * edgeOffset(s, fraction) * tipPressure;
      return [p.x+p.nx*off, p.y+p.ny*off];
    }
    // Broken washes establish uneven planes of bark. Sparse chips cross those
    // planes; there is deliberately no uniform blanket of parallel hatching.
    const washes=[], chips=[], flecks=[];
    function patch(s,span,f,half,tone,alpha) {
      return {s,end:Math.min(length,s+span),span,f,half,tone,alpha,
        drift:(rand()-.5)*.48,phase:rand()*6.283,
        rough:.07+rand()*.2};
    }
    for(let i=0,n=Math.ceil(length*.061);i<n;i++){
      const s=rand()*length,p=at(s),span=7+rand()*Math.max(10,p.width*1.8);
      washes.push(patch(s,span,(rand()-.5)*1.25,.24+rand()*.47,
        rand()<.42?'#e6c68c':rand()<.6?'#b27d42':'#6b7370',.28+rand()*.48));
    }
    for(let i=0,n=Math.ceil(length*(.14+Math.min(.1,widthStart/300)));i<n;i++){
      const s=rand()*length,p=at(s),kind=rand();
      const span=kind<.72?1.5+rand()*Math.min(11,p.width*.65):7+rand()*18;
      chips.push(patch(s,span,(rand()-.5)*1.58,
        kind<.72?.05+rand()*.20:.035+rand()*.085,
        kind<.64?'#263e44':kind<.87?'#6e543a':'#ecce94',
        .54+rand()*.35));
    }
    // A few broader scars around a bend give the wood its own anatomy. They
    // remain irregular open chips rather than decorative repeated knot rings.
    for(let i=1;i<points.length-1;i++){
      const a=points[i-1],b=points[i],d=points[i+1];
      const turn=Math.abs(Math.atan2(Math.sin(Math.atan2(d[1]-b[1],d[0]-b[0])-Math.atan2(b[1]-a[1],b[0]-a[0])),Math.cos(Math.atan2(d[1]-b[1],d[0]-b[0])-Math.atan2(b[1]-a[1],b[0]-a[0]))));
      if(turn<.20)continue;
      let nearest=0,best=Infinity;
      for(let j=0;j<spine.length;j++){const ds=distance(spine[j],b);if(ds<best){best=ds;nearest=lengths[j];}}
      const p=at(nearest),side=rand()<.5?-1:1;
      washes.push(patch(Math.max(0,nearest-p.width*.55),p.width*1.1,side*.3,.49,'#e2b976',.68));
      chips.push(patch(Math.max(0,nearest-p.width*.25),p.width*.65,side*.45,.16,'#354346',.76));
      chips.push(patch(Math.max(0,nearest+p.width*.06),p.width*.31,-side*.24,.13,'#775337',.76));
    }
    for(let i=0,n=Math.ceil(length*.11);i<n;i++){
      const s=rand()*length;
      flecks.push(patch(s,.4+rand()*1.9,(rand()-.5)*1.7,.012+rand()*.035,
        rand()<.62?'#f2ddad':'#344649',.45+rand()*.33));
    }
    washes.sort((a,b)=>a.s-b.s);chips.sort((a,b)=>a.s-b.s);flecks.sort((a,b)=>a.s-b.s);
    function paintedPatch(ctx,mark,tip){
      const end=Math.min(mark.end,tip-.3);
      if(end<=mark.s)return;
      const left=[],right=[],step=1.65,n=Math.ceil((end-mark.s)/step);
      for(let i=0;i<=n;i++){
        const s=Math.min(end,mark.s+i*step),t=(s-mark.s)/mark.span,p=at(s);
        const lift=.35+.65*Math.pow(Math.sin(Math.PI*Math.min(1,t)),.55);
        const rag=1+mark.rough*Math.sin(t*21+mark.phase)+mark.rough*.5*Math.sin(t*43+mark.phase*2);
        const center=mark.f+mark.drift*(t-.5)+.035*Math.sin(t*8+mark.phase);
        const half=mark.half*lift*rag;
        for(const [edge,list]of[[1,left],[-1,right]]){
          const fraction=clamp(center+edge*half,-.94,.94),o=fraction*p.width*.5*tipScale(s,tip);
          list.push([p.x+p.nx*o,p.y+p.ny*o]);
        }
      }
      ctx.beginPath();ctx.moveTo(left[0][0],left[0][1]);
      for(let i=1;i<left.length;i++)ctx.lineTo(left[i][0],left[i][1]);
      for(let i=right.length-1;i>=0;i--)ctx.lineTo(right[i][0],right[i][1]);
      ctx.closePath();ctx.fillStyle=mark.tone;ctx.globalAlpha=mark.alpha;ctx.fill();
    }
    function ribbon(ctx, tip, factor, color, shift) {
      const n = Math.max(1, Math.ceil(tip / 2)), left = [], right = [];
      for (let i = 0; i <= n; i++) {
        const s = Math.min(tip, i * 2);
        left.push(offsetPoint(s, 1 + shift, tip, factor));
        right.push(offsetPoint(s, -1 + shift, tip, factor));
      }
      ctx.beginPath(); ctx.moveTo(left[0][0],left[0][1]);
      for (let i=1;i<left.length;i++)ctx.lineTo(left[i][0],left[i][1]);
      for (let i=right.length-1;i>=0;i--)ctx.lineTo(right[i][0],right[i][1]);
      ctx.closePath();ctx.fillStyle=color;ctx.fill();
    }
    function draw(ctx, progress) {
      const tip = length * clamp(Number(progress) || 0, 0, 1);
      if (tip <= .001) return;
      ctx.save();
      ribbon(ctx,tip,1,'#344749',0);
      ribbon(ctx,tip,.95,'#bd925a',-.018);
      for(const marks of[washes,chips,flecks])for(const mark of marks){
        if(mark.s>=tip)break;
        paintedPatch(ctx,mark,tip);
      }
      ctx.restore();
    }
    return { length, draw };
  }
  window.BranchInk = Object.freeze({ makePath });
})();
