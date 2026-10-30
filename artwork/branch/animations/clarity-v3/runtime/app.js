(function(){
  const $=id=>document.getElementById(id),catalog=BirdsongCatalog.species,canvas=$('art');
  let index=0,painter=null,mode='portrait',playing=false,time=75,frame=0,last=0,token=0,companions=[],companionPromise,first=true;
  const phases=[[0,'Sketch · finding the form'],[9,'Water · selected passages'],[16,'Pigment · flowing into water'],[28,'Brush · pressure and colour'],[42,'Form · the head and body'],[53,'Feathers · wing and tail'],[64,'Pencil · pattern and definition'],[72,'Finishing · detail and lettering'],[75,'Rest.']];
  function update(){
    $('timeline').value=time;$('clock').textContent=`${Math.floor(time)} / 75 s`;
    $('phase').textContent=phases.filter(p=>time>=p[0]).at(-1)[1];
    $('play').textContent=playing?'Pause':first?'Paint from the beginning':time>=75?'Paint again':'Continue';
    $('play').disabled=!painter;$('timeline').disabled=!painter;
  }
  function draw(reset=false){
    if(!painter)return;painter.renderAt(time,reset);
    if(mode==='branch'){drawBirdsongBranch(canvas,painter,companions,time,$('activity').checked);}
    else{if(canvas.width!==1448||canvas.height!==1086){canvas.width=1448;canvas.height=1086;}const c=canvas.getContext('2d');c.clearRect(0,0,1448,1086);c.drawImage(painter.canvas,0,0,1448,1086);}
    update();
  }
  function pause(){playing=false;cancelAnimationFrame(frame);update();}
  function tick(now){if(!playing)return;time=Math.min(75,time+Math.max(0,(now-last)/1000));last=now;draw();if(time===75)pause();else frame=requestAnimationFrame(tick);}
  function play(){if(!painter)return;if(playing){pause();return;}if(first||time===75){time=0;draw(true);}first=false;playing=true;last=performance.now();update();frame=requestAnimationFrame(tick);}
  async function getCompanions(){
    const selected=catalog[index].id;
    const ids=['robin','woodpigeon','great-tit'].filter(id=>id!==selected).slice(0,2);
    companions=await Promise.all(ids.map(async id=>({config:ClarityPlacements[id],birdCanvas:await decodeBirdsongImage('subjects/'+id+'.png')})));
  }
  async function setMode(next){pause();mode=next;$('activity').closest('label').hidden=mode!=='branch';$('portrait-mode').setAttribute('aria-pressed',mode==='portrait');$('branch-mode').setAttribute('aria-pressed',mode==='branch');if(mode==='branch'&&!companions.length){$('loading').hidden=false;$('loading').textContent='Preparing the branch companions…';await getCompanions();$('loading').hidden=true;}describe();draw();}
  function describe(){if(!painter)return;const c=painter.config;$('description').textContent=mode==='portrait'?(c.approvedOriginal?'Revised clarity · original artwork · 75-second painting':'75-second painting · '+(c.lateFeature||'individual drawing score')):c.placementMode==='waterline'?'Shared scene study · this swimming pose stays at the waterline.':'Shared branch study · the same bird strokes and timing, with a separate perch.';}
  async function selectBird(id){
    const next=catalog.findIndex(s=>s.id===id);if(next<0)return;pause();const mine=++token;index=next;painter=null;time=75;first=true;update();$('failure').hidden=true;$('loading').hidden=false;$('loading').textContent='Preparing '+catalog[index].name.toLowerCase()+'…';$('bird-select').value=id;$('position').textContent=`${index+1} / ${catalog.length}`;
    document.querySelectorAll('.card').forEach(c=>c.setAttribute('aria-current',c.dataset.id===id));
    try{await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));const p=await createBirdsongPainter(await loadBirdsongAsset(id));if(mine!==token)return;painter=p;painter.setFluidity(Number($('feel').value)/100);$('source').href=catalog[index].source;canvas.setAttribute('aria-label',p.config.name+' developing from sketch through watercolour to fine feather detail');if(mode==='branch'){await getCompanions();if(mine!==token)return;}describe();draw();$('loading').hidden=true;history.replaceState(null,'','#'+id);}
    catch(error){if(mine!==token)return;$('loading').hidden=true;$('failure').textContent='Could not prepare this painting: '+error.message;$('failure').hidden=false;console.error(error);}
  }
  catalog.forEach(entry=>{const o=document.createElement('option');o.value=entry.id;o.textContent=entry.name;$('bird-select').append(o);const card=document.createElement('button');card.className='card';card.dataset.id=entry.id;card.setAttribute('aria-label','Open '+entry.name+' animation');const thumb=document.createElement('div');thumb.className='thumb';const img=document.createElement('img');img.src=entry.thumbnail||entry.source;img.loading='lazy';img.alt='';thumb.append(img);card.append(thumb);const label=document.createElement('span');label.textContent=entry.name;const small=document.createElement('small');small.textContent='75s';label.append(small);card.append(label);card.onclick=()=>{selectBird(entry.id);$('stage').scrollIntoView({behavior:'smooth',block:'start'});};$('gallery').append(card);});
  $('collection-title').textContent=`All ${catalog.length} birds`;
  [0,10,20,30,40,50,60,65,70,75].forEach(t=>{const b=document.createElement('button');b.textContent=t+'s';b.onclick=()=>{pause();first=false;time=t;draw();};$('milestones').append(b);});
  $('bird-select').onchange=e=>selectBird(e.target.value);$('previous').onclick=()=>selectBird(catalog[(index-1+catalog.length)%catalog.length].id);$('next').onclick=()=>selectBird(catalog[(index+1)%catalog.length].id);$('play').onclick=play;
  $('timeline').oninput=e=>{const nextTime=Number(e.target.value);pause();first=false;time=nextTime;draw();};
  $('feel').oninput=e=>{const f=Number(e.target.value)/100;$('feel-label').textContent=f<.33?'Dry':f<.67?'Balanced':'Fluid';painter?.setFluidity(f);draw(true);};
  $('portrait-mode').onclick=()=>setMode('portrait');$('branch-mode').onclick=()=>setMode('branch');$('activity').onchange=()=>draw();
  $('search').oninput=e=>{const term=e.target.value.toLowerCase();document.querySelectorAll('.card').forEach(c=>c.hidden=!c.textContent.toLowerCase().includes(term));};
  $('fullscreen').onclick=()=>document.fullscreenElement?document.exitFullscreen():$('stage').requestFullscreen();
  $('layer-download').onclick=e=>{e.preventDefault();if(!painter)return;const a=document.createElement('a');a.download=painter.config.id+'-'+Math.round(time)+'s-transparent.png';a.href=painter.birdCanvas.toDataURL();a.click();};
  document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});
  document.addEventListener('keydown',e=>{if(e.altKey||e.metaKey||e.ctrlKey||/INPUT|SELECT|TEXTAREA/.test(e.target.tagName))return;if(e.code==='Space'){e.preventDefault();play();}if(e.key==='ArrowRight')$('next').click();if(e.key==='ArrowLeft')$('previous').click();});
  window.birdsongGallery={selectBird,setMode,renderAt(t){pause();first=false;time=t;draw();},getState(){return{...painter?.getState(),loaded:!!painter,playing,mode,selected:catalog[index].id};},schedule(){return painter?.schedule();},integrity(){return painter?.integrity();},getPainter(){return painter;},play,pause};
  $('activity').closest('label').hidden=true;
  selectBird(catalog.some(s=>s.id===location.hash.slice(1))?location.hash.slice(1):'house-sparrow');
})();
