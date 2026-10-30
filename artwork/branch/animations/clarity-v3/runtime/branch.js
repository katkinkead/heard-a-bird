/* A local, material-textured placement preview. Bird strokes and clock are
   independent of this scene; integration can reuse drawBirdAt() unchanged. */
(function(){
  let paper=null,ink=null;
  function canvas(){return Object.assign(document.createElement('canvas'),{width:1600,height:900});}
  function rng(seed){return()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};}
  function drawBough(ctx,pts,width,seed){
    const random=rng(seed),lengths=[0];for(let i=1;i<pts.length;i++)lengths.push(lengths.at(-1)+Math.hypot(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1]));
    const total=lengths.at(-1),at=t=>{let i=1;while(i<pts.length-1&&lengths[i]<t*total)i++;const q=(t*total-lengths[i-1])/(lengths[i]-lengths[i-1]);return [pts[i-1][0]+(pts[i][0]-pts[i-1][0])*q,pts[i-1][1]+(pts[i][1]-pts[i-1][1])*q,Math.atan2(pts[i][1]-pts[i-1][1],pts[i][0]-pts[i-1][0])];};
    // Short loaded strokes, broken warm edges and irregular fibre marks.
    for(let j=0;j<5;j++){ctx.strokeStyle=['#aa885b','#8c7654','#314346','#26383b','#bd9b65'][j];ctx.globalAlpha=[.35,.48,.7,.9,.32][j];ctx.lineCap='round';ctx.lineJoin='round';
      for(let t=0;t<1;t+=.014+random()*.018){const end=Math.min(1,t+.018+random()*.052),a=at(t),b=at(end),offset=(random()-.5)*width*.65;ctx.lineWidth=Math.max(.5,width*(1-t*.86)*(j===0?1.25:j===1?.92:j===2?.68:j===3?.28:.1));ctx.beginPath();ctx.moveTo(a[0]-Math.sin(a[2])*offset,a[1]+Math.cos(a[2])*offset);ctx.lineTo(b[0]-Math.sin(b[2])*offset*.85,b[1]+Math.cos(b[2])*offset*.85);ctx.stroke();}}
    ctx.globalAlpha=1;
  }
  function prepare(){
    if(paper)return;paper=canvas();const g=paper.getContext('2d'),r=rng(8291);g.fillStyle='#f3eee5';g.fillRect(0,0,1600,900);
    for(let i=0;i<110000;i++){g.fillStyle=r()>.4?'rgba(255,253,245,.12)':'rgba(100,89,68,.065)';g.fillRect(r()*1600,r()*900,.3+r()*1.8,.3+r());}
    ink=canvas();const c=ink.getContext('2d');
    drawBough(c,[[-10,446],[230,429],[490,445],[795,416],[1030,437],[1280,414],[1610,432]],15,6);
    drawBough(c,[[150,434],[185,389],[232,329]],8,16);
    drawBough(c,[[441,441],[506,518],[604,662],[668,746]],9,27);
    drawBough(c,[[1040,437],[1101,392],[1150,351]],9,42);
    drawBough(c,[[604,662],[627,698],[609,721]],3,53);
    drawBough(c,[[232,329],[246,297],[240,281]],2.4,65);
    drawBough(c,[[1150,351],[1162,319],[1182,307]],2.7,74);
  }
  function bounds(config){return config.birdBounds||[80,70,920,610];}
  function placement(bird,anchor,boxWidth,boxHeight){
    const b=bounds(bird.config),foot=bird.config.perchAnchor||[(b[0]+b[2])/2,b[3]],s=Math.min(boxWidth/(b[2]-b[0]),boxHeight/(foot[1]-b[1]));
    const x=anchor[0]-foot[0]*s,y=anchor[1]-foot[1]*s;
    return {x,y,scale:s,bounds:[x+b[0]*s,y+b[1]*s,x+b[2]*s,y+b[3]*s]};
  }
  window.drawBirdAt=function(ctx,bird,anchor,boxWidth,boxHeight){
    const p=placement(bird,anchor,boxWidth,boxHeight);ctx.drawImage(bird.birdCanvas,p.x,p.y,1000*p.scale,750*p.scale);return p;
  };
  window.drawBirdsongBranch=function(out,current,companions,time,activity){
    prepare();if(out.width!==1600||out.height!==900){out.width=1600;out.height=900;}const c=out.getContext('2d');c.clearRect(0,0,1600,900);c.drawImage(paper,0,0);c.drawImage(ink,0,0);
    const slots=[{anchor:[286,305],w:340,h:244},{anchor:[756,754],w:385,h:250},{anchor:[1272,335],w:390,h:260}];
    const birds=[...companions,current];
    birds.forEach((bird,i)=>{if(!bird)return;const slot=slots[i],mode=bird.config.placementMode||'perched';let point=slot.anchor;
      if(mode==='waterline'){
        point=[1272,780];c.save();c.strokeStyle='#769598';c.globalAlpha=.5;c.lineWidth=1.4;for(let k=0;k<3;k++){c.beginPath();c.ellipse(point[0],point[1]+k*5,110+k*17,5+k*3,0,0,Math.PI*2);c.stroke();}c.restore();
      }else if(mode==='clinging'){
        drawBough(c,[[1150,351],[point[0]-22,point[1]+56],[point[0]+4,point[1]+70]],5.5,84);
        drawBough(c,[[point[0]+4,point[1]+70],[point[0]-8,point[1]-120],[point[0]+3,point[1]-182]],10,85);
      }
      if(mode!=='waterline'&&mode!=='clinging'){
        const p=placement(bird,point,slot.w,slot.h),contacts=bird.config.footContacts;
        let a=[point[0]-29,point[1]],b=[point[0]+29,point[1]];
        if(contacts?.length>=2){const world=contacts.map(v=>[p.x+v[0]*p.scale,p.y+v[1]*p.scale]).sort((x,y)=>x[0]-y[0]);a=world[0];b=world.at(-1);}
        const dx=b[0]-a[0],slope=dx?Math.max(-.8,Math.min(.8,(b[1]-a[1])/dx)):0,left=[a[0]-24,a[1]-24*slope],right=[b[0]+40,b[1]+40*slope];
        const junction=[[232,329],[668,746],[1150,351]][i];
        drawBough(c,[junction,left,right],5.4,108+i*17);
      }
      drawBirdAt(c,bird,point,slot.w,slot.h);
      if(i<2||time>70){c.save();c.globalAlpha=i<2?1:Math.min(1,(time-70)/3);c.fillStyle='#263f44';c.textAlign='center';c.font='italic 27px Georgia,serif';c.fillText(bird.config.name,point[0],point[1]+48);
        if(i===2&&activity){c.strokeStyle='#397b83';c.lineWidth=1.4;for(const [rx,ry] of [[14,4.8],[23,8]]){c.beginPath();c.ellipse(point[0],point[1]+72,rx,ry,0,0,Math.PI*2);c.stroke();}c.beginPath();c.arc(point[0],point[1]+69,3,0,Math.PI*2);c.fill();c.font='italic 19px Georgia,serif';c.fillText('Singing now',point[0],point[1]+101);}
        c.restore();}
    });
  };
})();
