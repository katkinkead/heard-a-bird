(function(){
const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
    const svgNS='http://www.w3.org/2000/svg';
    function pointsFromPath(d){
      const path=document.createElementNS(svgNS,'path');path.setAttribute('d',d);
      const length=path.getTotalLength(),steps=Math.max(14,Math.ceil(length/3));
      return Array.from({length:steps+1},(_,i)=>{const p=path.getPointAtLength(length*i/steps);return[p.x,p.y];});
    }
    function line(d,start,duration,width,opacity,kind='graphite',color=[77,76,69]){
      const segments=(d.match(/M[^M]+/g)||[d]).map(pointsFromPath);
      return {points:segments[0],segments,start,duration,width,opacity,kind,color};
    }
    const gesture=[
      line('M 302 235 C 285 342 351 455 468 493 C 516 508 560 510 606 499',.8,2.0,1.6,.27),
      line('M 310 160 C 300 110 338 85 382 92 C 437 99 469 155 480 205',3.0,1.7,1.5,.30),
      line('M 475 204 C 554 255 626 368 711 453 C 756 494 802 522 855 550',4.9,1.8,1.7,.28),
      line('M 375 252 C 415 268 482 340 548 392 C 590 425 647 448 696 458',6.9,1.5,1.1,.22),
      line('M 279 118 C 304 119 323 124 342 135 C 336 146 330 157 324 166 C 310 145 294 131 279 118',8.6,1.2,1.6,.48),
      line('M 326 170 C 319 192 309 217 309 251 C 296 348 329 421 402 466',9.9,1.4,1.8,.42),
      line('M 408 264 C 431 246 467 253 504 276 C 567 319 633 405 711 458 C 636 445 534 417 464 366 C 423 336 404 301 408 264',11.3,1.8,1.6,.42),
      line('M 408 468 C 452 490 503 500 564 500 C 654 506 743 546 854 565',13.2,1.5,1.3,.37),
      line('M 673 453 C 735 490 793 521 853 548 L 825 552 L 858 567',14.7,1.1,1.8,.42),
      line('M 469 497 C 458 518 440 542 432 550 L 412 559 M 432 550 L 420 565 M 432 550 L 450 555',15.9,1.1,1.5,.40),
      line('M 529 497 C 508 525 489 549 478 562 L 459 573 M 478 562 L 486 576 M 478 562 L 503 567',17.1,1.1,1.5,.40),
      line('M 157 588 C 299 538 449 533 571 552 C 654 561 730 610 785 651',18.4,1.8,2.0,.42)
    ];
    const ink=[
      line('M 337 104 C 370 89 407 101 429 118 C 450 133 466 165 478 201',45.7,1.2,2.6,.88,'ink',[23,40,44]),
      line('M 280 119 C 304 119 325 126 342 135',47.1,.6,2.3,.95,'ink',[25,37,42]),
      line('M 281 120 C 301 135 315 150 324 166',47.8,.6,2.1,.87,'ink',[25,37,42]),
      line('M 410 265 C 441 245 471 265 506 286',48.6,.7,1.7,.80,'ink',[31,43,43]),
      line('M 524 399 C 602 438 656 452 712 459',49.4,.7,1.8,.76,'ink',[29,44,47]),
      line('M 159 589 C 302 539 450 535 571 553 C 655 563 728 611 785 652',50.2,1.2,3.4,.90,'ink',[27,41,47]),
      line('M 469 497 C 459 519 441 543 432 552 L 413 560 M 432 552 L 422 566 M 432 552 L 451 556',51.4,.7,2.7,.88,'ink',[155,60,69]),
      line('M 529 497 C 509 526 490 549 478 563 L 459 574 M 478 563 L 486 576 M 478 563 L 503 568',52.1,.7,2.7,.88,'ink',[155,60,69]),
      line('M 367 154 C 367 148 377 147 380 153 C 383 161 371 166 367 159 C 366 157 366 155 367 154',52.9,.65,10,.98,'ink',[14,27,29]),
      line('M 371 151 L 374 150',53.6,.2,2.8,.98,'ink',[250,244,228])
    ];
    const ornamentPaths=[
      'M 432 279 Q 447 255 469 281 Q 454 300 432 279',
      'M 433 278 L 466 282',
      'M 443 278 L 445 268 M 451 280 L 454 269 M 459 281 L 463 275',
      'M 443 280 L 448 289 M 452 281 L 456 289',
      'M 453 296 Q 481 282 499 319 Q 476 333 453 296',
      'M 454 297 L 495 318',
      'M 465 303 L 469 293 M 475 308 L 479 299 M 485 314 L 488 306',
      'M 465 304 L 466 316 M 475 309 L 479 323',
      'M 419 276 Q 421 284 430 280 M 424 287 Q 429 295 437 290',
      'M 434 300 Q 438 309 446 303 M 443 311 Q 447 320 455 314',
      'M 458 330 Q 466 341 474 333 M 470 342 Q 477 351 484 344'
    ];
    const ornaments=ornamentPaths.map((d,i)=>line(d,44.3+i*.29,.32,1.05,.80,'ink',[227,188,109]));
    ornaments.push(line('M 646 411 Q 654 420 664 420',48.3,.35,7,.90,'ink',[247,237,211]));
    ornaments.push(line('M 674 436 Q 684 445 694 445',48.7,.35,7,.90,'ink',[247,237,211]));
    ornaments.push(line('M 706 460 Q 713 468 722 469',49.1,.35,6,.90,'ink',[247,237,211]));
/* Actual pigment paths. Authored anatomy supplies connected masses; the source
   supplies a palette and a sparse final feather study, never a bitmap reveal. */
function buildPigmentPlan({pixels,width,height}) {
  const data=pixels.data||pixels, out=[];
  let seed=392147;
  const rand=()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t^=t+Math.imul(t^t>>>7,61|t);return((t^t>>>14)>>>0)/4294967296;};
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const lerp=(a,b,t)=>a+(b-a)*t;
  const pixel=(x,y)=>{const i=(clamp(Math.round(y*height/750),0,height-1)*width+clamp(Math.round(x*width/1000),0,width-1))*4;return[data[i],data[i+1],data[i+2]];};
  const luminance=c=>c[0]*.213+c[1]*.715+c[2]*.072;
  const distance=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2]);
  const average=(x,y,r=3)=>{const base=pixel(x,y),sum=[...base];let n=1;for(let k=0;k<8;k++){const a=k*Math.PI/4,c=pixel(x+Math.cos(a)*r,y+Math.sin(a)*r);if(distance(base,c)<68){for(let j=0;j<3;j++)sum[j]+=c[j];n++;}}return sum.map(v=>Math.round(v/n));};
  // Representative material, not the lightest photographic paper pixels.
  const C={cream:[247,231,199], light:[251,242,219], warm:[231,191,128],
    ochre:average(340,309,4), shoulder:average(487,266,4), yellow:[250,186,19],
    red:[221,40,25], coral:[238,76,43], ink:[15,35,49], blue:[29,49,61],
    pink:[192,69,88], beak:[243,195,161], geometry:[241,196,107]};
  function add(points,color,breadth,opacity,start,duration,kind,profile){out.push({points:points.map(p=>[...p]),color:[...color],width:breadth,opacity,start,duration:Math.min(duration,46-start),kind,...(profile?{profile}:{})});}
  function offset(points,amount){return points.map((p,i)=>{const a=points[Math.max(0,i-1)],b=points[Math.min(points.length-1,i+1)],dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy)||1;return[p[0]-dy/len*amount,p[1]+dx/len*amount];});}
  // The backdrop is painted first: eight continuous, overlapping vertical pulls.
  // Later opaque cream and coloured bird marks cover the underlying ochre.
  for(let i=0;i<8;i++){
    const x=265+i*20.3;
    add([[x,59],[x-1,162],[x+1,281],[x,406],[x+.8,527]],C.geometry,32,.42,12+i*.24,1.4,'wash','flat');
  }
  const anatomical=[
    // Long cream gestures connect neck, breast and belly into a single volume.
    {p:[[337,212],[319,246],[316,284],[326,332],[348,376],[382,424],[430,459],[484,480],[545,482],[606,480],[663,480]],c:'cream',w:53},
    {p:[[369,215],[350,264],[356,310],[384,355],[429,392],[487,425],[548,447],[609,463]],c:'cream',w:56},
    {p:[[406,223],[394,268],[414,309],[452,349],[504,387],[559,421],[620,451]],c:'cream',w:49},
    // The head is built in curved strokes, with ivory visible under the mask.
    {p:[[342,130],[366,119],[391,124],[416,140],[434,164],[438,190],[416,213],[385,228],[354,231]],c:'light',w:40},
    {p:[[357,144],[375,158],[383,181],[374,207]],c:'light',w:44},
    // Ochre shoulders and flank, following the turned body.
    {p:[[443,201],[455,225],[482,247],[507,266],[534,286],[557,310],[580,334]],c:'shoulder',w:42},
    {p:[[331,252],[321,283],[329,316],[345,346]],c:'ochre',w:33},
    {p:[[351,258],[344,291],[352,325],[374,358]],c:'ochre',w:34},
    {p:[[453,392],[482,415],[519,434],[557,447],[595,457]],c:'warm',w:31},
    // Coherent dark feather masses extend into the tail.
    {p:[[414,278],[444,286],[474,301],[508,325],[546,354],[585,386],[625,415],[673,449]],c:'ink',w:58},
    {p:[[448,282],[482,291],[516,319],[552,349],[590,380],[629,413],[678,450]],c:'ink',w:58},
    {p:[[430,304],[458,333],[494,361],[534,388],[574,413],[619,436]],c:'ink',w:45},
    {p:[[624,424],[669,455],[715,488],[759,520],[806,551]],c:'ink',w:30},
    {p:[[650,424],[695,455],[747,488],[802,519],[839,521]],c:'ink',w:22},
    // The gold wingbar is a continuous diagonal ribbon, not scattered dots.
    {p:[[495,302],[519,329],[550,359],[583,387],[616,414],[652,443]],c:'yellow',w:22},
    // Crown and cheek mask.
    {p:[[345,111],[370,109],[395,116],[416,131],[434,151],[445,172]],c:'ink',w:20},
    {p:[[435,166],[441,188],[433,209],[414,225],[389,234]],c:'ink',w:23},
    {p:[[339,126],[354,116],[372,123],[384,137],[389,151]],c:'red',w:38},
    {p:[[328,161],[322,183],[322,203],[337,211],[355,201],[371,182],[377,166]],c:'red',w:40},
    {p:[[332,155],[350,153],[370,159],[389,165]],c:'ink',w:12},
    {p:[[292,123],[312,134],[332,147]],c:'beak',w:17}
  ];
  // First lay thin, translucent connected masses; the hand revisits them with
  // denser colour and narrower, overlapping strokes after the initial sketch.
  anatomical.forEach((a,i)=>{
    const start=14.2+i*.28;
    add(a.p,C[a.c],a.w*1.02,.32,start,1.08,'wash');
    if(i<18)add(offset(a.p,a.w*.12),C[a.c],a.w*.74,.30,start+.23,.96,'wash');
  });
  anatomical.forEach((a,i)=>{
    const start=22+i*.43;
    add(a.p,C[a.c],a.w,.87,start,1.16,'paint');
    // Parallel ribbons overlap to create breadth while showing hand movement.
    // Lighter body deposits remain visible as real cream pigment on the paper.
    for(let j=0;j<2;j++){
      const d=(j-.5)*a.w*.26;
      const col=C[a.c].map(v=>clamp(v+(j===0?4:j===2?-3:0),0,255));
      add(offset(a.p,d),col,a.w*.47,.66,start+.18+j*.12,.83,'paint');
    }
  });
  // Continuous ivory feather groups cross the dark tail at deliberate places.
  const accents=[
    {p:[[610,342],[615,347],[622,350]],w:8,c:'light'},
    {p:[[642,382],[648,388],[656,392]],w:8,c:'light'},
    {p:[[669,414],[677,420],[684,423]],w:8,c:'light'},
    {p:[[692,438],[699,443],[707,448]],w:7,c:'light'},
    {p:[[728,471],[738,478],[748,483]],w:8,c:'light'},
    {p:[[771,502],[783,510],[795,517]],w:7,c:'light'},
    {p:[[321,244],[316,271],[319,297],[329,322]],w:7,c:'light'},
    {p:[[348,364],[373,394],[405,419],[442,437]],w:9,c:'light'}
  ];
  accents.forEach((a,i)=>add(a.p,C[a.c],a.w,.83,34+i*.19,.68,'detail'));
  // A few long, fine cream filaments break the shoulder's broad colour.
  const shoulderFeathers=[
    [[451,218],[461,231],[473,241]],
    [[458,228],[472,242],[486,252]],
    [[470,236],[485,249],[499,262]],
    [[483,245],[497,259],[511,271]],
    [[492,259],[508,272],[523,284]],
    [[506,266],[521,280],[535,294]],
    [[520,280],[533,293],[548,306]],
    [[533,292],[547,306],[560,319]],
    [[547,305],[559,316],[571,330]],
    [[476,253],[489,267],[501,280]]
  ];
  shoulderFeathers.forEach((p,i)=>add(p,C.light,.85+(i%3)*.18,.66,34.4+i*.19,.64,'detail'));
  // The final sampled strokes are selective feather hatching. They do not
  // construct the silhouette, and are not shortened by source paper texture.
  const detailRegions=[
    {n:8,b:[306,241,395,370],dir:(x,y)=>1.22-(y-270)*.0035,allow:(x,y,c)=>x>300+(y-270)*.10&&luminance(c)<239},
    {n:6,b:[387,377,612,477],dir:()=>.46,allow:(x,y,c)=>luminance(c)>125&&luminance(c)<241},
    {n:10,b:[447,227,586,337],dir:(x,y)=>.51+(y-270)*.002,allow:(x,y,c)=>c[0]>c[2]*1.3&&luminance(c)<231},
    {n:10,b:[399,278,625,435],dir:()=>.64,allow:(x,y,c)=>luminance(c)<117},
    {n:6,b:[680,467,820,548],dir:()=>.59,allow:(x,y,c)=>luminance(c)<112},
    {n:8,b:[319,116,389,211],dir:(x,y)=>y<150?.3:1.7,allow:(x,y,c)=>c[0]>c[1]*1.6&&c[0]>c[2]*1.5},
    {n:5,b:[352,107,451,229],dir:(x,y)=>.38+(y-117)*.011,allow:(x,y,c)=>luminance(c)<100}
  ];
  const candidates=[];
  detailRegions.forEach((r,ri)=>{
    let attempts=0,count=0;
    while(count<r.n&&attempts++<r.n*80){
      const x=lerp(r.b[0],r.b[2],rand()),y=lerp(r.b[1],r.b[3],rand()),source=average(x,y,2.1);
      if(!r.allow(x,y,source))continue;
      let color=source;
      // Pale feather lines are actual deposited warm ivory, not punched holes.
      if((ri===0||ri===1||ri===2)&&rand()<.43)color=C.light;
      if(ri===3)color=rand()<.33?C.warm:C.blue;
      if(ri===4)color=rand()<.22?C.cream:C.blue;
      if(ri===5)color=rand()<.32?C.coral:C.red;
      if(ri===6)color=C.blue;
      const angle=r.dir(x,y)+(rand()-.5)*.15,len=lerp(21,43,rand()),dx=Math.cos(angle)*len,dy=Math.sin(angle)*len;
      const points=[[x-dx*.5,y-dy*.5],[x-dx*.21-1,y-dy*.21],[x+dx*.14-1,y+dy*.14+1],[x+dx*.5,y+dy*.5]];
      candidates.push({points,color,width:lerp(.8,2.7,rand()),opacity:lerp(.5,.83,rand()),region:ri});count++;
    }
  });
  // Alternate regional phrases. Close strokes arrive together, then the hand
  // moves elsewhere, avoiding both a scanline and a frame of isolated flecks.
  let cursor=0, index=0;
  const detailCount=candidates.length;
  while(candidates.length){
    const region=cursor++%detailRegions.length;
    const first=candidates.findIndex(c=>c.region===region);if(first<0)continue;
    const anchor=candidates[first].points[1];
    const matching=candidates.filter(c=>c.region===region).sort((a,b)=>Math.hypot(a.points[1][0]-anchor[0],a.points[1][1]-anchor[1])-Math.hypot(b.points[1][0]-anchor[0],b.points[1][1]-anchor[1])).slice(0,3);
    for(const c of matching){const at=candidates.indexOf(c);candidates.splice(at,1);const start=35.5+index++/Math.max(1,detailCount)*9.6;add(c.points,c.color,c.width,c.opacity,start,.55,'detail');}
  }
  return out.sort((a,b)=>a.start-b.start);
}

/*
 * Coloured-pencil finish for a dry watercolour goldfinch.
 * The reference is consulted only for local colour. Every visible line is an
 * authored curve or a feather-directed hatch, deposited as a separate mark.
 * Coordinates are logical 1000 x 750; no raster, mask or canvas is returned.
 */
function buildPencilPlan({pixels,width,height}) {
  const data=pixels.data||pixels, out=[], groups=[];
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const mix=(a,b,t)=>a.map((v,i)=>Math.round(v+(b[i]-v)*t));
  const pix=(x,y)=>{const i=(clamp(Math.round(y*height/750),0,height-1)*width+clamp(Math.round(x*width/1000),0,width-1))*4;return[data[i],data[i+1],data[i+2]];};
  const C={ink:[18,35,48], petrol:[32,57,68], blue:[68,92,108], cream:[248,232,197], ivory:[251,242,219], ochre:[190,126,56], gold:[234,184,84], scarlet:[201,31,30], coral:[242,82,54], pink:[195,66,91], pinkLight:[244,145,152], warm:[208,162,103]};
  const poly=(p,vs)=>{let yes=false;for(let i=0,j=vs.length-1;i<vs.length;j=i++){const a=vs[i],b=vs[j];if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])yes=!yes;}return yes;};
  const dist=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
  function curve(a,b,c,d,n=9){return Array.from({length:n+1},(_,i)=>{const t=i/n,u=1-t;return[0,1].map(k=>u*u*u*a[k]+3*u*u*t*b[k]+3*u*t*t*c[k]+t*t*t*d[k]);});}
  function quad(a,b,c,n=7){return Array.from({length:n+1},(_,i)=>{const t=i/n,u=1-t;return[0,1].map(k=>u*u*a[k]+2*u*t*b[k]+t*t*c[k]);});}
  function group(name,start,end){const marks=[];groups.push({name,start,end,marks});return marks;}
  function add(g,points,color,breadth=1,opacity=.76){g.push({points,color:[...color],width:breadth,opacity,kind:'pencil',pencilGroup:groups.find(z=>z.marks===g)?.name});}
  // A coherent grid of slightly staggered feather tufts. Every short line
  // follows the same anatomical flow locally; spacing is regular, not confetti.
  function field(g,polygon,bounds,spacing,angle,length,color,opacity=.7){
    let row=0;
    for(let y=bounds[1];y<=bounds[3];y+=spacing[1],row++){
      for(let x=bounds[0]+(row%2)*spacing[0]*.5;x<=bounds[2];x+=spacing[0]){
        const s=Math.sin(x*.39+y*.17),a=typeof angle==='function'?angle(x,y):angle;
        const L=(typeof length==='function'?length(x,y):length)*(1+.12*s),dx=Math.cos(a)*L,dy=Math.sin(a)*L;
        const p0=[x,y],p1=[x+dx,y+dy];
        if(!poly(p0,polygon)||!poly(p1,polygon))continue;
        const p=quad(p0,[x+dx*.53-Math.sin(a)*1.2,y+dy*.53+Math.cos(a)*1.2],p1);
        const source=pix(x+dx*.4,y+dy*.4),col=typeof color==='function'?color(source,x,y,s):color;
        add(g,p,col,.75+.32*(.5+.5*Math.sin(x*.73+y*.21)),opacity+.06*s);
      }
    }
  }
  function parallel(g,points,offset,color,breadth,opacity){
    const shifted=points.map((p,i)=>{const a=points[Math.max(0,i-1)],b=points[Math.min(points.length-1,i+1)],L=dist(a,b)||1;return[p[0]-(b[1]-a[1])/L*offset,p[1]+(b[0]-a[0])/L*offset];});add(g,shifted,color,breadth,opacity);
  }
  const beak=group('Beak facets',44,45.25);
  // Pencil follows the planes of the bill, with a crisp lower seam.
  const top=[282,120],base=[339,137],lower=[324,163];
  add(beak,quad(top,[315,120],base),C.ink,1.45,.93);
  add(beak,quad(top,[310,138],lower),C.ink,1.30,.90);
  add(beak,quad([284,121],[314,133],[334,147]),C.warm,1.20,.85);
  add(beak,quad([289,121],[318,127],[335,137]),C.ivory,1.30,.94);
  for(let k=0;k<12;k++){
    const u=(k+1)/14;
    add(beak,quad([287+43*u,123+13*u],[296+35*u,129+13*u],[302+27*u,135+18*u]),k%3===0?C.cream:mix([227,147,126],C.ivory,u*.45),.75,.69);
  }
  const face=group('Face and crown feathers',45.3,50.5);
  const red=[[341,111],[368,106],[395,124],[398,149],[383,162],[367,180],[355,206],[331,216],[308,216],[314,179],[331,160],[337,139]];
  field(face,red,[309,112,398,214],[4.8,7.3],(x,y)=>y<144?.2+(x-355)*.012:1.55+(x-346)*-.018,(x,y)=>y<145?8:12,(c,x,y,s)=>s>.2?C.coral:mix(c,C.scarlet,.37),.80);
  const cheek=[[401,130],[418,137],[432,158],[435,174],[419,180],[415,202],[397,217],[369,229],[348,228],[353,213],[371,190],[382,172],[393,169],[393,148]];
  field(face,cheek,[350,132,432,229],[5.2,8],(x,y)=>1.2+(x-392)*-.008,8,(c,x,y,s)=>s>.1?C.ivory:mix(C.warm,C.ivory,.60),.77);
  // Feathered boundary: curved teeth lie inside the red chin and cream bib.
  for(let i=0;i<23;i++){
    const x=310+i*2.6,y=214+7*Math.sin(i/22*Math.PI);
    add(face,quad([x,y-8],[x-1,y-3],[x-2.2,y+2]),i%3===0?C.ivory:C.coral,.90,.83);
  }
  const crown=[[369,103],[393,111],[420,127],[440,152],[458,186],[460,204],[443,220],[416,232],[398,236],[398,224],[431,204],[438,179],[429,153],[414,136],[390,122]];
  field(face,crown,[372,108,460,236],[6.1,8],(x,y)=>.36+(y-116)*.012,10,(c,x,y,s)=>s>.2?C.blue:mix(c,C.petrol,.4),.72);
  const shoulder=group('Shoulder feather layers',50.6,54.5);
  const shoulderPoly=[[451,202],[474,224],[498,244],[531,276],[563,315],[585,338],[569,340],[541,316],[506,290],[470,268],[441,254],[426,250],[430,230]];
  field(shoulder,shoulderPoly,[429,207,585,338],[6.4,8.1],(x,y)=>.48+(y-215)*.0022,13,(c,x,y,s)=>s>.08?C.ivory:mix(c,C.ochre,.46),.82);
  // Longer paired contours divide the small shoulder feathers into rows.
  for(let i=0;i<9;i++){
    const p=curve([447+i*7,224+i*8],[461+i*8,235+i*9],[478+i*8,245+i*9],[495+i*8,263+i*9]);
    add(shoulder,p,C.cream,.9,.78);
  }
  const breast=group('Breast and belly pencil',54.6,58.8);
  const breastPoly=[[323,235],[347,238],[371,237],[384,246],[383,284],[396,321],[418,350],[433,367],[410,380],[384,383],[362,372],[341,349],[327,320],[317,287],[318,258]];
  field(breast,breastPoly,[317,242,425,380],[5.7,8.2],(x,y)=>1.55-(y-245)*.005,15,(c,x,y,s)=>s>.1?C.ivory:mix(c,C.ochre,.35),.78);
  const bellyPoly=[[349,368],[380,396],[408,414],[449,432],[486,443],[527,451],[575,463],[620,476],[649,488],[609,484],[562,483],[514,483],[471,473],[428,459],[393,441],[366,412],[351,387]];
  field(breast,bellyPoly,[350,372,644,486],[9.1,8.4],(x,y)=>.70-(x-360)*.0014,16,(c,x,y,s)=>s>-.15?C.ivory:mix(c,C.warm,.35),.77);
  // Very light pencil contours describe the curvature rather than a dark outline.
  for(let i=0;i<9;i++)add(breast,curve([315+i*2,294+i*8],[319+i*3,327+i*9],[341+i*5,360+i*8],[367+i*6,380+i*8]),mix(C.warm,C.ivory,.45),.72,.54);
  const coverts=group('Layered wing feathers',58.9,62.7);
  // Four overlapping rows of small open feather scallops, following the wing.
  for(let r=0;r<5;r++){
    for(let k=0;k<9-r;k++){
      const x=411+r*13+k*8.6,y=264+r*18+k*6.6;
      const p=quad([x,y],[x+2,y+8],[x+12,y+7]);
      add(coverts,p,(r+k)%4===0?C.ivory:C.gold,.95,.82);
      add(coverts,quad([x+2,y+1],[x+3,y+4],[x+8,y+4.7]),(r+k)%3===0?C.ochre:C.cream,.70,.66);
    }
  }
  // The long cream edge separates the dark wing from the breast, in interrupted runs.
  for(let i=0;i<13;i++){
    const x=410+i*7.3,y=288+i*7.0;
    add(coverts,quad([x,y],[x+3,y+8],[x+12,y+10]),C.ivory,1.05,.88);
  }
  const ornament=group('Engraved wing leaves',62.8,65.45);
  function leaf(a,b,c,d){
    const edge1=curve(a,b,c,d,12),edge2=curve(d,[c[0]-7,c[1]+12],[b[0]-10,b[1]+9],a,12);
    add(ornament,edge1,C.gold,1.2,.96);add(ornament,edge2,C.gold,1.2,.96);
    add(ornament,quad(a,[(a[0]+d[0])/2-1,(a[1]+d[1])/2+1],d),C.gold,1.00,.93);
    for(let i=1;i<=10;i++){
      const t=i/11,u=1-t;
      const mid=[a[0]+(d[0]-a[0])*t,a[1]+(d[1]-a[1])*t];
      const top=edge1[Math.round(t*12)],bot=edge2[Math.round((1-t)*12)];
      add(ornament,quad([mid[0]-2,mid[1]-2],[(mid[0]+top[0])/2,(mid[1]+top[1])/2],top),C.gold,.73,.83);
      add(ornament,quad([mid[0]-2,mid[1]-2],[(mid[0]+bot[0])/2,(mid[1]+bot[1])/2],bot),C.gold,.73,.83);
    }
  }
  leaf([435,283],[451,267],[478,280],[492,311]);
  leaf([441,310],[462,302],[486,322],[503,341]);
  // Tiny scales connect leaf forms to the existing feather rows.
  for(let i=0;i<12;i++){
    const x=451+(i%4)*9,y=342+Math.floor(i/4)*8+(i%4)*2.8;
    add(ornament,quad([x,y],[x+2,y+7],[x+9,y+4]),C.gold,.87,.86);
  }
  const flights=group('Flight feathers and tail',65.5,68.55);
  // Each flight feather has a long shaft and a restrained pair of fine barbs.
  for(let i=0;i<11;i++){
    const a=[515+i*8.4,309+i*12.4],d=[677+i*5.8,435+i*4.0];
    const p=curve(a,[a[0]+34,a[1]+37],[d[0]-39,d[1]-17],d,16);
    add(flights,p,i%4===0?C.ivory:(i%2?C.gold:C.blue),.80+(i%3)*.15,i%4===0?.63:.75);
    parallel(flights,p,2.8,i%2?C.ochre:C.petrol,.65,.61);
    for(let j=1;j<4;j++){
      const t=.18+j*.19,q=p[Math.round(t*16)];
      add(flights,quad([q[0]-4,q[1]-5],[q[0]+2,q[1]],[q[0]+11,q[1]+5]),i%2?C.gold:C.blue,.70,.68);
    }
  }
  // Tail shafts stretch well beyond the body; all stop inside the fork.
  const tailPaths=[
    [[666,449],[715,479],[779,513],[840,542]],
    [[664,456],[715,489],[776,522],[828,546]],
    [[660,463],[709,496],[771,532],[839,559]],
    [[658,468],[712,506],[778,543],[850,564]],
    [[681,454],[734,481],[787,508],[833,522]]
  ];
  tailPaths.forEach((p,i)=>{
    const pts=curve(...p,20);add(flights,pts,i%2?C.blue:C.cream,.90,.72);
    parallel(flights,pts,2.5,C.petrol,.70,.72);
    for(let j=1;j<5;j++){const q=pts[j*4];add(flights,quad([q[0]-8,q[1]-6],[q[0],q[1]],[q[0]+12,q[1]+5]),i%2?C.blue:C.cream,.69,.66);}
  });
  const feet=group('Feet, facial rim and final edges',68.6,69.95);
  // Warm pink on the lit side and plum under the joints gives the feet volume.
  const legPaths=[[[469,499],[455,518],[440,539],[433,549]],[[529,498],[509,526],[488,550],[479,561]]];
  legPaths.forEach((p,i)=>{
    const pts=curve(...p,16);add(feet,pts,C.pinkLight,1.45,.93);parallel(feet,pts,2.3,C.scarlet,1.0,.82);
    for(let k=1;k<7;k++){const q=pts[k*2];add(feet,[[q[0]-1.9,q[1]-1.1],[q[0]+1.5,q[1]+1.5]],C.pinkLight,.70,.74);}
  });
  const toes=[[[433,550],[426,554],[416,556],[413,561]],[[432,552],[428,556],[424,561],[422,566]],[[434,551],[439,551],[445,554],[450,555]],[[479,562],[471,566],[463,568],[459,574]],[[480,563],[483,569],[486,572],[486,577]],[[481,562],[490,564],[497,565],[503,568]]];
  toes.forEach(p=>{add(feet,curve(...p),C.pinkLight,1.08,.91);});
  // Only the outer eye rim: root draws the pupil and catchlight afterwards.
  const eye=[];for(let i=0;i<=24;i++){const a=i/24*Math.PI*2;eye.push([374+10.4*Math.cos(a),153.7+10.0*Math.sin(a)]);}add(feet,eye,C.warm,1.05,.88);
  add(feet,curve([338,105],[360,99],[387,105],[410,119]),C.ink,1.5,.89);
  add(feet,curve([458,200],[488,225],[518,254],[541,281]),C.ink,1.30,.77);
  // Each group is played as a short pencil phrase, leaving tiny lifts between
  // strokes. A long contour draws for longer than a six-pixel feather barb.
  for(const g of groups){
    const lengths=g.marks.map(s=>s.points.reduce((sum,p,i)=>sum+(i?dist(p,s.points[i-1]):0),0));
    const weights=lengths.map(v=>.75+Math.sqrt(v)*.12),total=weights.reduce((a,b)=>a+b,0);let at=g.start;
    g.marks.forEach((s,i)=>{const slot=(g.end-g.start)*weights[i]/total;s.start=at;s.duration=Math.max(.055,Math.min(.28,slot*1.45));at+=slot;out.push(s);});
  }
  return out;
}

/*
 * Material-inspired wet passages. Fresh pigment travels through an authored
 * wetness field; its edge and paper deposits settle after the brush lifts.
 * All pixels below are generated pigment, never a revealed reference image.
 * This is an art-directed approximation, not a calibrated fluid simulation.
 */
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
function buildReferenceFinish({pixels,width,height}) {
  const data=pixels.data||pixels, out=[], W=1000,H=750;
  let seed=834715;
  const rand=()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t^=t+Math.imul(t^t>>>7,61|t);return((t^t>>>14)>>>0)/4294967296;};
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const lum=c=>.213*c[0]+.715*c[1]+.072*c[2];
  const dist=(a,b)=>Math.sqrt((a[0]-b[0])**2+(a[1]-b[1])**2+(a[2]-b[2])**2);
  const raw=(x,y)=>{const sx=clamp(x*width/W,0,width-1.001),sy=clamp(y*height/H,0,height-1.001),ix=sx|0,iy=sy|0,fx=sx-ix,fy=sy-iy,i=(iy*width+ix)*4,j=i+width*4;return [0,1,2].map(k=>data[i+k]*(1-fx)*(1-fy)+data[i+4+k]*fx*(1-fy)+data[j+k]*(1-fx)*fy+data[j+4+k]*fx*fy);};
  const sample=(x,y,r=0)=>{if(!r)return raw(x,y);const c=raw(x,y),cs=[raw(x-r,y),raw(x+r,y),raw(x,y-r),raw(x,y+r)];return c.map((v,i)=>(v*4+cs.reduce((s,z)=>s+z[i],0))/8);};
  const poly=[[279,118],[338,116],[351,104],[374,98],[401,102],[423,116],[443,143],[455,175],[475,200],[496,218],[541,258],[581,300],[620,349],[659,397],[698,441],[729,471],[774,486],[814,504],[858,526],[830,524],[826,570],[806,546],[759,516],[711,491],[675,482],[614,478],[574,476],[541,474],[526,478],[487,477],[446,469],[405,455],[375,436],[352,414],[329,386],[310,354],[297,321],[289,287],[291,259],[298,232],[306,211],[313,184],[314,157],[296,136]];
  const inside=(x,y,p=poly)=>{let c=false;for(let i=0,j=p.length-1;i<p.length;j=i++){const a=p[i],b=p[j];if((a[1]>y)!==(b[1]>y)&&x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])c=!c;}return c;};
  const bodyMask=new Uint8Array(W*H),group=new Uint8Array(W*H);
  // Pale cheek and breast remain part of the subject. Outside its silhouette,
  // only actual dark contour/perch marks and pink feet may produce strokes.
  for(let y=90;y<654;y++)for(let x=152;x<864;x++){
    const c=raw(x,y),l=lum(c),isBird=inside(x,y),isContour=!isBird&&l<118&&y<577&&x>280,
      isFoot=y>465&&y<582&&x>340&&x<558&&(l<151||(c[0]-c[1]>35&&c[2]>c[1]*.74)),
      isBranch=y>534&&y<653&&x>153&&x<785&&l<136&&!(y>596&&x>390&&x<605);
    if(isBird||isContour||isFoot||isBranch){const q=y*W+x;bodyMask[q]=1;group[q]=isFoot?6:isBranch?7:y<238?0:x<397&&y<400?1:y>405&&x<647?2:x>670?5:x>488?4:3;}
  }
  const inMask=(x,y)=>x>=0&&x<W&&y>=0&&y<H&&bodyMask[(y|0)*W+(x|0)]===1;
  function direction(x,y,scale){
    let a;
    if(y<235){const dx=x-379,dy=y-159;a=Math.atan2(dy,dx)+Math.PI*.5;if(y>170&&x<364)a=1.68;}
    else if(x<400){a=1.53-(y-255)*.0036;}
    else if(y>445&&x<565){a=-.86;}
    else if(y>535){a=(x-455)*.0012;}
    else a=.67+(x-530)*.00025;
    if(scale<=2){
      // Follow the visible feather/engraving edge when it has a clear tangent.
      const left=sample(x-1.2,y,.4),right=sample(x+1.2,y,.4),top=sample(x,y-1.2,.4),bot=sample(x,y+1.2,.4);
      let dx=0,dy=0;for(let k=0;k<3;k++){const gx=right[k]-left[k],gy=bot[k]-top[k];if(Math.hypot(gx,gy)>Math.hypot(dx,dy)){dx=gx;dy=gy;}}
      const mag=Math.hypot(dx,dy);
      if(mag>25){let tangent=Math.atan2(dy,dx)+Math.PI/2;while(tangent-a>Math.PI/2)tangent-=Math.PI;while(tangent-a< -Math.PI/2)tangent+=Math.PI;a=a*.12+tangent*.88;}
    }
    return a;
  }
  function makeMark(x,y,c,breadth,length,tolerance,blur,pass){
    const angle=direction(x,y,pass),v=[Math.cos(angle),Math.sin(angle)],n=[-v[1],v[0]];
    // Keep the pencil footprint inside the subject, and keep broad pigment off
    // white feathers or neighbouring fields of strongly contrasting colour.
    let w=breadth;
    for(let j=0;j<4;j++){
      const a=[x+n[0]*w*.48,y+n[1]*w*.48],b=[x-n[0]*w*.48,y-n[1]*w*.48];
      if(inMask(...a)&&inMask(...b)&&dist(sample(...a,blur),c)<tolerance*1.2&&dist(sample(...b,blur),c)<tolerance*1.2)break;
      w*=.66;
    }
    const ends=[];
    for(const sign of [-1,1]){
      const ps=[],limit=length*.5;let at=0;
      for(let s=.7;s<=limit;s+=.75){
        const curve=Math.sin(s/Math.max(4,length)*Math.PI)*Math.min(.35,length*.025),xx=x+v[0]*s*sign+n[0]*curve,yy=y+v[1]*s*sign+n[1]*curve;
        if(!inMask(xx,yy)||dist(sample(xx,yy,blur),c)>tolerance)break;
        at=s;if(s>limit*.38&&s<limit*.72)ps.push([xx,yy]);
      }
      // A visible dot is a very short pencil stroke; never zero-length.
      const len=Math.max(.20,at);ends.push({p:[x+v[0]*len*sign,y+v[1]*len*sign],mid:ps[Math.floor(ps.length/2)]});
    }
    const points=[ends[0].p];if(ends[0].mid)points.push(ends[0].mid);points.push([x,y]);if(ends[1].mid)points.push(ends[1].mid);points.push(ends[1].p);
    return {points,color:c.map(Math.round),width:w,opacity:1,kind:'pencil',profile:'flat',finishStyle:'reference',start:0,duration:.18,region:group[(y|0)*W+(x|0)],pass};
  }
  const batches=[[],[],[]];
  const passes=[
    // The solid but still broad colour correction arrives before engraved detail.
    {grid:6.7,width:10.0,length:19,tolerance:89,blur:2.0},
    {grid:3.45,width:5.1,length:10,tolerance:64,blur:.8},
    {grid:2.15,width:2.8,length:7.0,tolerance:40,blur:0}
  ];
  passes.forEach((p,pass)=>{
    for(let y=97;y<654;y+=p.grid)for(let x=156;x<861;x+=p.grid){
      const xx=x+(rand()-.5)*p.grid*.58,yy=y+(rand()-.5)*p.grid*.58;if(!inMask(xx,yy))continue;
      const c=sample(xx,yy,p.blur);let wid=p.width,len=p.length;
      if(group[(yy|0)*W+(xx|0)]>=6){wid*=.54;len*=.85;}
      // The final pass pays closer attention to fine printed dark/light edges.
      const m=makeMark(xx,yy,c,wid,len,p.tolerance,p.blur,pass);m.order=rand();batches[pass].push(m);
    }
  });
  // A last precise pass on high-contrast feather barbs, eye and wing engraving
  // restores marks finer than the regular pencil grid, using their own colour.
  for(let y=100;y<572;y+=1.35)for(let x=284;x<858;x+=1.35){
    const xx=x+(rand()-.5)*.5,yy=y+(rand()-.5)*.5;if(!inMask(xx,yy))continue;
    const c=raw(xx,yy),local=[raw(xx-1,yy),raw(xx+1,yy),raw(xx,yy-1),raw(xx,yy+1)],edge=Math.max(...local.map(z=>dist(c,z)));
    if(edge<35)continue;
    if(rand()>.82)continue;
    const m=makeMark(xx,yy,c,1.03,4.2,27,0,2);m.order=rand();m.accent=true;batches[2].push(m);
  }
  // The two focal regions need a genuinely finer pencil than the body hatch.
  // These short pigment touches retain the eye catchlight and the interlaced
  // gold leaf veins, rather than replacing them with an invented ornament.
  for(const box of [[358,134,398,173],[421,276,505,351]]){
    for(let y=box[1];y<box[3];y+=.92)for(let x=box[0];x<box[2];x+=.92){
      if(!inMask(x,y))continue;
      const c=raw(x,y),edge=Math.max(dist(c,raw(x-1,y)),dist(c,raw(x+1,y)),dist(c,raw(x,y-1)),dist(c,raw(x,y+1)));
      if(edge<21&&rand()>.32)continue;
      const m=makeMark(x,y,c,1.03,2.1,21,0,2);m.order=rand();m.accent=true;m.focal=true;batches[2].push(m);
    }
  }
  const focal=batches[2].filter(m=>m.focal);
  batches[2]=batches[2].filter(m=>!m.focal);
  const ranges=[[40,53.5],[53.0,68.5],[68.0,83.0]];
  // Regional phrases alternate every ~2 seconds, avoiding a stationary band.
  // All areas receive detail, with the head revisited rather than completed once.
  batches.forEach((batch,pass)=>{
    const pools=Array.from({length:8},()=>[]);for(const m of batch)pools[m.region].push(m);
    pools.forEach(p=>p.sort((a,b)=>(a.focal?-2:a.accent?-1:0)-(b.focal?-2:b.accent?-1:0)||a.order-b.order));
    const sequence=[],regionOrder=[0,1,3,4,2,5,0,4,3,2,6,7];
    let left=batch.length;
    while(left){for(const r of regionOrder){const p=pools[r];for(let k=0;k<38&&p.length;k++){sequence.push(p.pop());left--;}}}
    const [a,b]=ranges[pass];let total=0;for(const m of sequence){m.cost=.6+Math.sqrt(m.width)*.21;total+=m.cost;}
    let done=0;for(const m of sequence){m.start=a+(b-a)*done/total;m.duration=pass===0?.22:pass===1?.18:.115;done+=m.cost;delete m.cost;delete m.order;out.push(m);}
  });
  // Let the engraved wing and the eye resolve last, after the body has texture.
  // This provides a visible final reward and prevents broader marks painting
  // over the tiny reference-accurate catchlight or intersecting leaf veins.
  focal.sort((a,b)=>(a.region===0?1:0)-(b.region===0?1:0)||a.order-b.order);
  focal.forEach((m,i)=>{m.start=83.1+3.7*i/focal.length;m.duration=.10;delete m.order;out.push(m);});
  return out;
}

/* Reference-informed paper marks and handwritten labels. This builder samples
 * source colours and traces dark ink geometry; it returns only pigment strokes,
 * never an image, pixel mask, canvas or raster-reveal operation. */
function buildFinishingContext({pixels,width,height}) {
  const data=pixels.data||pixels, out=[], W=1000,H=750;
  let seed=847331;
  const rand=()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t^=t+Math.imul(t^t>>>7,61|t);return((t^t>>>14)>>>0)/4294967296;};
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const lum=c=>.213*c[0]+.715*c[1]+.072*c[2];
  const colorDist=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1],a[2]-b[2]);
  const pix=(x,y)=>{const q=(clamp(Math.round(y*height/H),0,height-1)*width+clamp(Math.round(x*width/W),0,width-1))*4;return[data[q],data[q+1],data[q+2]];};
  const avg=(x,y,r)=>{const c=pix(x,y),a=[pix(x-r,y),pix(x+r,y),pix(x,y-r),pix(x,y+r)];return c.map((v,k)=>(v*4+a.reduce((s,p)=>s+p[k],0))/8);};
  const poly=[[279,118],[338,116],[351,104],[374,98],[401,102],[423,116],[443,143],[455,175],[475,200],[496,218],[541,258],[581,300],[620,349],[659,397],[698,441],[729,471],[774,486],[814,504],[858,526],[830,524],[826,570],[806,546],[759,516],[711,491],[675,482],[614,478],[574,476],[541,474],[526,478],[487,477],[446,469],[405,455],[375,436],[352,414],[329,386],[310,354],[297,321],[289,287],[291,259],[298,232],[306,211],[313,184],[314,157],[296,136]];
  const bird=(x,y)=>{let c=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const a=poly[i],b=poly[j];if((a[1]>y)!==(b[1]>y)&&x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])c=!c;}return c;};
  const bg=(x,y)=>x>=251&&x<422&&y>=47&&y<535&&!bird(x,y);
  const mark=(points,color,breadth,start,duration,section)=>({points,color:color.map(Math.round),width:breadth,opacity:1,kind:'pencil',profile:'flat',finishStyle:'reference',start,duration,contextSection:section});
  const background=[];
  const specs=[{grid:6.1,w:8.5,len:14,r:1.6},{grid:3.4,w:4.3,len:7.6,r:.5}];
  specs.forEach((s,pass)=>{
    for(let y=47+s.grid/2;y<535;y+=s.grid)for(let x=251+s.grid/2;x<422;x+=s.grid){
      const xx=x+(rand()-.5)*s.grid*.65,yy=y+(rand()-.5)*s.grid*.65;if(!bg(xx,yy))continue;
      const c=avg(xx,yy,s.r),a=-.3+rand()*1.6,dx=Math.cos(a),dy=Math.sin(a),nx=-dy,ny=dx;
      let b=s.w;
      while(b>1&&(!bg(xx+nx*b*.55,yy+ny*b*.55)||!bg(xx-nx*b*.55,yy-ny*b*.55)))b*=.6;
      const ends=[];
      for(const sign of [-1,1]){let d=.4;for(let t=.7;t<s.len/2;t+=.7){const px=xx+sign*dx*t,py=yy+sign*dy*t;if(!bg(px,py)||colorDist(avg(px,py,s.r),c)>(pass?55:90))break;d=t;}ends.push([xx+sign*dx*d,yy+sign*dy*d]);}
      const m=mark([ends[0],[xx,yy],ends[1]],c,b,0,pass?.11:.16,'ochre geometry');m.pass=pass;m.order=rand();background.push(m);
    }
  });
  // A scattered fine dry-brush pass preserves the broken printed edges and
  // light paper flecks, instead of making parallel bars or a solid rectangle.
  for(let y=48;y<534;y+=2.15)for(let x=252;x<421;x+=2.15){
    const xx=x+(rand()-.5),yy=y+(rand()-.5);if(!bg(xx,yy))continue;
    const c=pix(xx,yy),edge=Math.max(colorDist(c,pix(xx+1.3,yy)),colorDist(c,pix(xx,yy+1.3)));
    if(edge<32||rand()>.30)continue;
    const a=rand()*Math.PI,d=.55+rand()*.7,dx=Math.cos(a)*d,dy=Math.sin(a)*d;
    if(!bg(xx-dx,yy-dy)||!bg(xx+dx,yy+dy))continue;
    const m=mark([[xx-dx,yy-dy],[xx+dx,yy+dy]],c,1.6,0,.09,'ochre paper tooth');m.pass=2;m.order=rand();background.push(m);
  }
  // Brief return visits to the geometric field; most attention remains on bird.
  const slots=[[[39.3,40.3],[44.2,45.0],[49.3,50.2]],[[55.6,56.4],[61.0,61.8],[67.0,67.8]],[[73.0,73.8],[77.0,77.8]]];
  for(let pass=0;pass<3;pass++){
    const list=background.filter(m=>m.pass===pass).sort((a,b)=>a.order-b.order),windows=slots[pass];
    list.forEach((m,i)=>{const z=i/list.length*windows.length,j=Math.min(windows.length-1,Math.floor(z)),q=z-j;const [a,b]=windows[j];m.start=a+(b-a)*q;delete m.order;out.push(m);});
  }
  function traceInk(box,limit,start,end,section){
    const [x0,y0,x1,y1]=box,scale=1.3,w=Math.ceil((x1-x0)*scale)+2,h=Math.ceil((y1-y0)*scale)+2;
    const mask=new Uint8Array(w*h),distance=new Float32Array(w*h),source=[];
    for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){
      const c=pix(x0+(x-1)/scale,y0+(y-1)/scale),q=y*w+x;
      if(lum(c)<limit&&c[2]>c[0]*.68){mask[q]=1;distance[q]=1e5;}else distance[q]=0;
    }
    // Chamfer distance records local ink width before topology is thinned.
    for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){const q=y*w+x;if(mask[q])distance[q]=Math.min(distance[q],distance[q-1]+1,distance[q-w]+1,distance[q-w-1]+1.414,distance[q-w+1]+1.414);}
    for(let y=h-2;y>0;y--)for(let x=w-2;x>0;x--){const q=y*w+x;if(mask[q])distance[q]=Math.min(distance[q],distance[q+1]+1,distance[q+w]+1,distance[q+w+1]+1.414,distance[q+w-1]+1.414);}
    const off=[-w,-w+1,1,w+1,w,w-1,-1,-w-1];
    for(let iteration=0;iteration<35;iteration++){
      let removed=0;
      for(let phase=0;phase<2;phase++){
        const remove=[];
        for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){
          const q=y*w+x;if(!mask[q])continue;const p=off.map(d=>mask[q+d]),n=p.reduce((a,b)=>a+b,0);if(n<2||n>6)continue;
          let transitions=0;for(let k=0;k<8;k++)if(!p[k]&&p[(k+1)%8])transitions++;if(transitions!==1)continue;
          if(!phase?(p[0]*p[2]*p[4]||p[2]*p[4]*p[6]):(p[0]*p[2]*p[6]||p[0]*p[4]*p[6]))continue;
          remove.push(q);
        }
        remove.forEach(q=>mask[q]=0);removed+=remove.length;
      }
      if(!removed)break;
    }
    const neighbors=q=>off.map(d=>q+d).filter(i=>mask[i]);
    const seen=new Set(),edgeKey=(a,b)=>a<b?a+':'+b:b+':'+a;
    const paths=[];
    function walk(a,b){
      const path=[a],initial=a;let prev=a,q=b;
      seen.add(edgeKey(a,b));
      for(let k=0;k<2000;k++){
        path.push(q);const ns=neighbors(q).filter(n=>n!==prev);
        if(ns.length!==1)break;const next=ns[0],key=edgeKey(q,next);if(seen.has(key))break;
        seen.add(key);prev=q;q=next;if(q===initial)break;
      }
      if(path.length>1)paths.push(path);
    }
    for(let q=w+1;q<mask.length-w-1;q++)if(mask[q]&&neighbors(q).length!==2)for(const b of neighbors(q))if(!seen.has(edgeKey(q,b)))walk(q,b);
    for(let q=w+1;q<mask.length-w-1;q++)if(mask[q])for(const b of neighbors(q))if(!seen.has(edgeKey(q,b)))walk(q,b);
    // Split when width changes materially. Every deposited ribbon follows the
    // handwriting itself, including pressure swells in the source lettering.
    const marks=[];
    for(const path of paths){
      for(let i=0;i<path.length-1;){
        const begin=i,base=distance[path[i]];let j=i+1;
        while(j<path.length-1&&j-begin<13&&Math.abs(distance[path[j]]-base)<Math.max(.9,base*.3))j++;
        const segment=path.slice(begin,j+1),points=segment.map(q=>[x0+(q%w-1)/scale,y0+((q/w|0)-1)/scale]);
        const middle=points[points.length>>1],breadth=segment.reduce((s,q)=>s+distance[q],0)/segment.length*1.86/scale;
        const m=mark(points,pix(...middle),Math.max(.7,breadth),0,.11,section);m.order=points.reduce((s,p)=>s+p[0],0)/points.length;marks.push(m);i=j;
      }
    }
    marks.sort((a,b)=>a.order-b.order);
    marks.forEach((m,i)=>{m.start=start+(end-start)*i/Math.max(1,marks.length-1);delete m.order;out.push(m);});
    return marks.length;
  }
  traceInk([392,598,606,667],155,87.0,89.75,'handwritten Goldfinch');
  traceInk([905,695,991,720],158,88.2,89.7,'handwritten Singing now');
  // The live mark consists of full circles seen in perspective, not arcs of
  // a Wi-Fi symbol. Trace source ink so its placement stays artist-sized.
  traceInk([925,675,972,697],189,87.8,88.8,'perspective live ripple');
  return out;
}


window.buildApprovedGoldfinch=function(pixels){const W=1000,H=750;
      const pigment=buildPigmentPlan({pixels,width:W,height:H}).filter(s=>s.kind!=='detail').map((s,i)=>{
        s.pressAt=.28+(i%5)*.055;s.pigmentLoad=.92+(i%3)*.04;
        if(s.kind==='wash'){
          if(s.profile==='flat'){s.start+=1;s.opacity*=.65;}
          else {s.start=16.8+(s.start-14.2)*.75;s.opacity*=.82;}
        }else{
          s.start=30+(s.start-22)*1.1;s.duration*=1.12;
          const light=s.color[0]+s.color[1]+s.color[2]>620;
          s.opacity*=light?.48:s.color[0]>s.color[2]*1.5?.62:.94;
        }
        return s;
      });
      const pencil=buildReferenceFinish({pixels,width:W,height:H});
      const contextMarks=buildFinishingContext({pixels,width:W,height:H});
      const wet=buildWetPass();
      const strokes=[...gesture,...pigment,...wet,...pencil,...contextMarks].flatMap(s=>{
        if(!s.segments||s.segments.length===1)return[s];
        const lengths=s.segments.map(p=>p.reduce((v,z,i)=>v+(i?Math.hypot(z[0]-p[i-1][0],z[1]-p[i-1][1]):0),0));
        const total=lengths.reduce((a,b)=>a+b,0);let elapsed=0;
        return s.segments.map((points,i)=>{const duration=s.duration*lengths[i]/total,part={...s,points,start:s.start+elapsed,duration:duration*.90};elapsed+=duration;return part;});
      });
retimeGoldfinch(strokes);return strokes;};
})();
