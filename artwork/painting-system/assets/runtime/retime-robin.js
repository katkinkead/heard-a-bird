/*
 * Robin-only 75 second choreography.
 *
 * Timing changes only: every pigment mark, colour, opacity and path survives.
 * The sketch/water opening retains its own material order. Dry finishing then
 * moves through anatomy, with broad -> medium -> fine maintained within each
 * region. The patterned wing, pale belly, feet and perch have substantive work
 * left after 50 seconds, rather than spending the ending on global pixel polish.
 *
 * Call before resample(), which calculates each mark's cached .end value.
 */
function retimeRobin(strokes, config) {
  if (config && config.id && config.id !== 'robin') return strokes;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const sourceTime = s => s.robinOriginalStart ?? s.start;
  const sourceDuration = s => s.robinOriginalDuration ?? s.duration;
  const original = new Map();
  strokes.forEach((s, i) => {
    if (s.robinOriginalStart == null) s.robinOriginalStart = s.start;
    if (s.robinOriginalDuration == null) s.robinOriginalDuration = s.duration;
    original.set(s, i);
  });

  const pools = new Map();
  const put = (name, s) => {
    if (!pools.has(name)) pools.set(name, []);
    pools.get(name).push(s);
  };
  const centre = s => {
    const p = s.points || [];
    if (!p.length) return [500, 375];
    return p.reduce((a, v) => [a[0] + v[0] / p.length, a[1] + v[1] / p.length], [0, 0]);
  };
  const inEllipse = (x, y, cx, cy, rx, ry, angle) => {
    const dx = x - cx, dy = y - cy, c = Math.cos(angle), z = Math.sin(angle);
    return ((dx * c + dy * z) / rx) ** 2 + ((-dx * z + dy * c) / ry) ** 2 < 1;
  };
  const anatomicalPhrase = s => {
    const [x, y] = centre(s);
    // A rounded, slanted patch follows the decorative covert feathers; it does
    // not leave a rectangular unfinished tile in the middle of the wing.
    const patternedWing = inEllipse(x, y, 518, 313, 101, 67, -.73);
    if (s.region === 6) {
      if (y >= 535) return 'perch';
      if (y >= 465) return 'feet';
      return 'outer contour';
    }
    if (s.region === 0) return 'head';
    if (s.region === 5) return 'tail';
    if (patternedWing) return 'patterned wing';
    if (s.region === 3) return 'flight feathers';
    if (s.region === 4 || (s.region === 2 && y < 370)) return 'breast';
    return 'pale belly';
  };

  const openingKnots = [[0, 0], [11.3, 9.5], [12, 10], [18, 15], [29, 24], [36.5, 29], [42, 33]];
  const openingTime = value => {
    for (let i = 1; i < openingKnots.length; i++) {
      const a = openingKnots[i - 1], b = openingKnots[i];
      if (value <= b[0]) return a[1] + (b[1] - a[1]) * (value - a[0]) / (b[0] - a[0]);
    }
    return 33 + (value - 42) * .7;
  };

  for (const s of strokes) {
    const at = sourceTime(s), duration = sourceDuration(s);
    const [x, y] = centre(s);
    if (s.contextSection === 'geometric background' || s.region === 7) {
      put('background:' + (s.pass ?? 0), s);
    } else if (s.contextSection || s.region === 8) {
      put(x > 850 && y > 630 ? 'status' : 'name', s);
    } else if (at >= 86.5 && x > 850 && y > 630) {
      // The live ripple and its source lettering are separate shared marks.
      put('status', s);
    } else if (s.finishStyle === 'reference' && Number.isFinite(s.pass)) {
      const phrase = anatomicalPhrase(s);
      s.robinPacingPhrase = phrase;
      put(phrase + ':' + (s.focal ? 'focal' : s.pass), s);
    } else {
      s.start = Math.max(0, openingTime(at));
      s.duration = Math.max(.06, openingTime(at + duration) - s.start);
      s.robinPacingPhrase = s.kind === 'graphite' ? 'gesture'
        : s.kind === 'wet' ? 'water'
        : s.kind === 'bloom' ? 'wet pigment'
        : 'loaded brush';
      if ('end' in s) s.end = s.start + s.duration;
    }
  }

  // Starts and ends are deliberately staggered: this is a sequence of painting
  // phrases, not one whole-image coarse pass followed by whole-image fine passes.
  const windows = {
    'outer contour': [[33, 35.4], [35.6, 39.2], [39.4, 44.8]],
    'head': [[33, 36.2], [36.4, 40], [40.2, 46]],
    'breast': [[35.4, 40.2], [40.4, 45.8], [46, 53.8]],
    'pale belly': [[40.2, 45.5], [45.7, 51.8], [52, 60.8]],
    'tail': [[41, 45.7], [45.9, 50.6], [50.8, 58.6]],
    'flight feathers': [[43, 48.4], [48.6, 56.2], [56.4, 65.8]],
    'patterned wing': [[49, 54.2], [54.4, 61.2], [61.4, 70.8]],
    'feet': [[53, 57.6], [57.8, 62.6], [62.8, 70.4]],
    'perch': [[56, 60.6], [60.8, 65.2], [65.4, 71.8]]
  };
  const lengthOf = s => {
    const p = s.points || [];
    let length = 0;
    for (let i = 1; i < p.length; i++) length += Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]);
    return length;
  };
  const visualCost = s => {
    const c = s.color || [100, 100, 100];
    const contrast = Math.min(1, Math.hypot(243 - c[0], 238 - c[1], 229 - c[2]) / 240);
    // Enough time for a broad or contrasting stroke to read; faint texture
    // receives less screen time than the same count of dark feather marks.
    return clamp(Math.sqrt(Math.max(.1, s.width || 1) * Math.max(.5, lengthOf(s))) * (.38 + .62 * contrast), .25, 18);
  };
  const schedule = (name, start, end, maximumDuration = .16) => {
    const list = pools.get(name) || [];
    if (!list.length) return;
    // Retain original same-region layering, including its edge-accent ordering.
    list.sort((a, b) => sourceTime(a) - sourceTime(b) || original.get(a) - original.get(b));
    const costs = list.map(visualCost), total = costs.reduce((a, b) => a + b, 0) || 1;
    const duration = Math.min(maximumDuration, (end - start) * .16);
    const span = Math.max(0, end - start - duration);
    let soFar = 0;
    for (let i = 0; i < list.length; i++) {
      const s = list[i];
      s.start = start + span * soFar / total;
      s.duration = Math.min(duration, Math.max(.065, sourceDuration(s)));
      s.robinPacingPhrase = name.split(':')[0];
      if ('end' in s) s.end = s.start + s.duration;
      soFar += costs[i];
    }
  };

  for (const [phrase, stages] of Object.entries(windows)) {
    stages.forEach(([a, b], pass) => schedule(phrase + ':' + pass, a, b, pass === 0 ? .19 : pass === 1 ? .15 : .11));
    // Dense focal marks follow the local finish. The largest patterned area is
    // a visible late phrase; the eye is one small part of that ending.
    const focalWindow = phrase === 'patterned wing' ? [70.9, 73.1]
      : phrase === 'head' ? [71.1, 73.2]
      : phrase === 'flight feathers' ? [66, 69.4]
      : [Math.max(61, stages[2][1] + .15), Math.min(72.8, Math.max(63.5, stages[2][1] + 2.6))];
    schedule(phrase + ':focal', focalWindow[0], focalWindow[1], .09);
  }
  schedule('background:0', 12.4, 42, .24);
  schedule('background:1', 42.2, 58, .12);
  schedule('background:2', 58.2, 69.8, .10);
  schedule('name', 72.3, 74.65, .12);
  schedule('status', 73.3, 74.9, .10);

  // Normal-sized frame comparisons showed that the broad paint still carried
  // much more visible change than the long fine-pass tail. Spend more wall
  // time on those substantial marks and less on barely visible refinement.
  // A smooth, monotone clock preserves every local mark's layer order.
  const clock = [[0,0],[10,9],[20,24],[30,38],[40,50],[50,64],[60,71],[70,73.5],[75,75]];
  const slopes = clock.slice(1).map((p,i)=>(p[1]-clock[i][1])/(p[0]-clock[i][0]));
  const tangents = clock.map((p,i)=>{
    if(i===0)return slopes[0];
    if(i===clock.length-1)return slopes[slopes.length-1];
    const a=slopes[i-1],b=slopes[i];
    return 2*a*b/(a+b);
  });
  const perceptualTime = value => {
    let i=0;
    while(i<clock.length-2&&value>clock[i+1][0])i++;
    const a=clock[i],b=clock[i+1],h=b[0]-a[0],t=clamp((value-a[0])/h,0,1);
    const t2=t*t,t3=t2*t;
    return (2*t3-3*t2+1)*a[1]+(t3-2*t2+t)*h*tangents[i]
      +(-2*t3+3*t2)*b[1]+(t3-t2)*h*tangents[i+1];
  };
  for(const s of strokes){
    if(s.robinPacingPhrase==='name'||s.robinPacingPhrase==='status')continue;
    const end=perceptualTime(s.start+s.duration);
    s.start=perceptualTime(s.start);
    s.duration=Math.max(.015,end-s.start);
    if('end' in s)s.end=s.start+s.duration;
  }
  return strokes;
}
