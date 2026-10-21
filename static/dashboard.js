(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const state = {status:null,catalogue:[],birds:[],detections:[],jobs:[],view:'overview',settingsLoaded:false,pendingJob:null,authenticated:false,busy:false};
  const localHost = ['localhost','127.0.0.1','::1','[::1]'].includes(location.hostname);
  const escape = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = v => Number.isFinite(Number(v)) ? Number(v).toLocaleString() : '—';
  const nice = v => String(v || 'unknown').replaceAll('_',' ');
  function date(v,short=false){if(!v)return 'Not yet heard';try {const d=new Date(v);if(Number.isNaN(d.valueOf()))return 'Time unavailable';return new Intl.DateTimeFormat('en-GB',{timeZone:state.status?.settings?.timezone||'Europe/London',day:'numeric',month:'short',...(short?{}:{hour:'2-digit',minute:'2-digit'})}).format(d);}catch(_){return 'Time unavailable';}}
  function safeUrl(value){try {const u=new URL(value,location.origin);return ['http:','https:'].includes(u.protocol)&&u.origin===location.origin?u.href:null;}catch(_){return null;}}
  function banner(message,error=false){$('global-message').textContent=message;$('global-message').className=`message-banner${error?' error':''}`;$('global-message').hidden=false;}
  function message(id,text,error=false){$(id).textContent=text;$(id).className=`form-message${error?' error':''}`;}
  async function api(path,options={}){
    const response = await fetch(path,{credentials:'same-origin',...options,headers:{...(options.body?{'Content-Type':'application/json'}:{}),...(options.headers||{})}});
    let data;try{data=await response.json();}catch(_){data={};}
    if(response.status===401){lock();throw new Error('Unlock the dashboard with your operator token.');}
    if(!response.ok)throw new Error(data.error||data.message||`The server returned ${response.status}.`);
    return data;
  }
  function post(path,body={}){return api(path,{method:'POST',body:JSON.stringify(body)});}
  function lock(){state.authenticated=false;$('lock-dashboard').hidden=true;$('unlock').hidden=false;$('application').hidden=true;$('connection-label').className='connection-label';$('connection-label').innerHTML='<i></i> Operator access required';}
  function unlock(){state.authenticated=true;$('lock-dashboard').hidden=false;$('unlock').hidden=true;$('application').hidden=false;}
  function setView(){const requested=location.hash.slice(1)||'overview';state.view=['overview','birds','atelier','maintenance','settings'].includes(requested)?requested:'overview';document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!==`view-${state.view}`);document.querySelectorAll('[data-view]').forEach(a=>{if(a.dataset.view===state.view)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});if(state.authenticated)refreshView();}
  function badge(text,kind=''){return `<span class="soft-pill ${kind}">${escape(text)}</span>`;}
  function renderHealth(){
    const station=state.status.station||{}, listening=station.listening||'unknown';
    const summary=station.connected?(listening==='available'?'Listening is available':listening==='unavailable'?'Listening needs attention':'Pi connected. Ears unconfirmed.'):'Waiting for the garden Pi';
    $('listening-summary').textContent=summary;
    $('listening-description').textContent=!station.connected?'No recent Pi heartbeat. Listening health is unknown.':listening==='available'?'Audio capture and recognition are reporting healthy. The garden is allowed to be quiet.':listening==='unavailable'?'The Pi is reporting, but one of the listening checks needs attention.':'A heartbeat arrived; microphone and recognition health still need evidence.';
    const rows=[['Pi connection',station.connected?'Connected':'No recent heartbeat',station.connected?'good':'warn'],['Microphone',nice(station.audio_status),station.audio_status==='healthy'?'good':'warn'],['Recognition',nice(station.inference_status),station.inference_status==='healthy'?'good':'warn']];
    $('health-rows').innerHTML=rows.map(([label,value,tone])=>`<div class="health-row"><span>${label}</span><strong class="state-${tone}">${escape(value)}</strong></div>`).join('');
  }
  function renderOverview(){
    const s=state.status,c=s.current||{},counts=s.counts||{};
    renderHealth();$('month-count').textContent=num(counts.month_detections);$('species-count').textContent=num(counts.species);$('artwork-count').textContent=num(counts.artwork??state.catalogue.length);$('queue-count').textContent=num(s.queue_count??0);
    const art=state.catalogue.find(b=>b.id===c.artwork_id||b.scientific_name===c.scientific_name);
    if(art?.image_url&&safeUrl(art.image_url)){$('current-art').src=art.image_url;$('current-art').alt=`Approved ${art.common_name} painting preview`;}
    $('current-bird').textContent=c.common_name||art?.common_name||'A painting is waiting.';
    $('painting-mode').textContent=c.test?'Test bird':c.mode==='live'?'Recent detection':c.mode?nice(c.mode):'Approved collection';
    $('current-caption').textContent=c.test?'A rehearsal event; excluded from real bird history.':c.observed_at?`Detected ${date(c.observed_at)} · the preview shows the finished artwork.`:'The painting page handles the live stroke progression.';
    const issues=(s.issues||[]).filter(i=>!i.resolved),missing=(s.missing_art||[]).filter(i=>!i.has_artwork);
    $('attention-title').textContent=issues.length?`${issues.length} ${issues.length===1?'issue needs':'issues need'} a look.`:missing.length?`${missing.length} ${missing.length===1?'visitor needs':'visitors need'} a portrait.`:'The desk is clear.';
    $('attention-description').textContent=issues.length?(issues[0].message||'Open maintenance for details and recovery history.'):missing.length?'Their detections are saved. The approved collection can keep playing.':'New operational issues and missing artwork will appear here.';
    $('attention-link').href=issues.length?'#maintenance':'#atelier';$('attention-link').textContent=issues.length?'View maintenance ↗':'Visit the art table ↗';
  }
  function populateSelectors(){
    const approved=state.catalogue.filter(b=>b.animation_ready!==false&&b.approved!==false);
    const oldTest=$('test-species').value;$('test-species').innerHTML=approved.map(b=>`<option value="${escape(b.scientific_name)}">${escape(b.common_name)}</option>`).join('');if(approved.some(b=>b.scientific_name===oldTest))$('test-species').value=oldTest;
    $('test-form').querySelector('button').disabled=!approved.length;
    const all=new Map(state.catalogue.map(b=>[b.scientific_name,b]));for(const b of state.status?.missing_art||[])all.set(b.scientific_name,b);
    const old=$('job-species').value;$('job-species').innerHTML='<option value="">No species selected</option>'+[...all.values()].sort((a,b)=>a.common_name.localeCompare(b.common_name)).map(b=>`<option value="${escape(b.scientific_name)}">${escape(b.common_name)}</option>`).join('');if(all.has(old))$('job-species').value=old;
  }
  function renderBirds(){
    const search=$('bird-search').value.toLowerCase(),missing=$('missing-only').checked;
    const birds=state.birds.filter(b=>(!missing||!b.has_artwork)&&`${b.common_name} ${b.scientific_name}`.toLowerCase().includes(search));
    $('birds-body').innerHTML=birds.map(b=>`<tr><td><strong>${escape(b.common_name)}</strong><small>${escape(b.scientific_name)}</small></td><td>${num(b.count)}</td><td>${escape(date(b.last_heard))}</td><td>${b.has_animation?badge('Painting ready'):b.has_artwork?badge('Portrait approved · animation pending','warm'):badge('Needs artwork','warm')}</td></tr>`).join('');$('birds-empty').hidden=birds.length>0;
    const realEvents=state.detections.filter(d=>!d.test);
    $('recent-detections').innerHTML=realEvents.length?realEvents.slice(0,20).map(d=>`<div class="arrival"><strong>${escape(d.common_name||d.species_common||d.scientific_name)}</strong><span>${escape(date(d.detected_at||d.observed_at||d.received_at))}</span><span>${Number.isFinite(Number(d.confidence??d.confidence_score))?`${Math.round(Number(d.confidence??d.confidence_score)*100)}% confidence`:'Confidence unavailable'}${d.station_id?` · ${escape(d.station_id)}`:''}</span></div>`).join(''):'<p class="muted small">No real detections have arrived yet.</p>';
  }
  function jobKindNote(){const kind=$('job-kind').value;const notes={artwork:'Creates a draft using the style references. Approval adds a new species as a still portrait; existing approved assets remain protected.',style:'Proposes a style change for review. Existing approved portraits and the Robin benchmark stay intact.',animation:'Creates a written registration proposal for approved artwork. Prepared animations can be previewed; a new sequence still needs authoring and validation.',diagnose:'Explains selected server diagnostics and proposes next steps. It does not apply model-written repairs automatically.'};$('job-kind-note').textContent=notes[kind];$('job-species').disabled=kind==='style'||kind==='diagnose';}
  function renderAtelier(){
    $('art-gallery').innerHTML=state.catalogue.filter(b=>b.approved!==false).map(b=>`<a class="art-tile" href="${escape(safeUrl(b.image_url)||'#')}" target="_blank" rel="noopener">${safeUrl(b.image_url)?`<img src="${escape(b.image_url)}" alt="${escape(b.common_name)} approved artwork" loading="lazy">`:''}<div><strong>${escape(b.common_name)}</strong><small>${b.animation_ready?'Approved · 75-second painting':'Approved still · animation pending'}</small></div></a>`).join('');
    const missing=(state.status.missing_art||[]).filter(b=>!b.has_artwork);
    $('missing-art-list').innerHTML=missing.length?missing.map(b=>`<div class="missing-item"><div><strong>${escape(b.common_name)}</strong><p>${num(b.count)} detections · last ${escape(date(b.last_heard))}<br>Email: ${escape(nice(b.email_status||'not configured'))}</p></div><button class="secondary" data-draft="${escape(b.scientific_name)}">Start a draft ↗</button></div>`).join(''):'<p class="small muted">No unpainted visitors are waiting. New species appear here after a qualifying real detection.</p>';
    $('job-start').disabled=!state.status.settings?.ai_configured;
    if(!state.status.settings?.ai_configured)message('job-message','Add optional AI credentials in Garden settings to enable these jobs.');else if($('job-message').textContent.includes('Add optional'))message('job-message','');
    renderJobs();jobKindNote();
  }
  function renderJobs(){
    $('jobs-list').innerHTML=state.jobs.length?state.jobs.map(j=>`<article class="job-item"><div class="job-item-head"><div><h3>${escape(nice(j.kind))}${j.scientific_name?` · ${escape(state.catalogue.find(b=>b.scientific_name===j.scientific_name)?.common_name||j.scientific_name)}`:''}</h3><p>${escape(j.message||'The server will record progress here.')}</p><p>${escape(date(j.created_at))}</p></div>${badge(nice(j.status),j.status==='failed'?'alert':j.status==='review'?'warm':'')}</div><div class="job-item-actions">${safeUrl(j.result_url)?`<a class="text-link" href="${escape(safeUrl(j.result_url))}" target="_blank" rel="noopener">Open the result ↗</a>`:''}${safeUrl(j.result?.preview_url)?`<a class="text-link" href="${escape(safeUrl(j.result.preview_url))}" target="_blank" rel="noopener">Preview existing animation ↗</a>`:''}${j.status==='review'&&j.kind==='artwork'&&!state.catalogue.some(b=>b.scientific_name===j.scientific_name)?`<button class="secondary" data-approve="${escape(j.id)}">Review approval →</button>`:''}</div></article>`).join(''):'<div class="empty-state"><span aria-hidden="true">✳</span><h2>A clean sheet.</h2><p>No AI jobs have been started. The approved paintings work beautifully without one.</p></div>';
  }
  function renderMaintenance(){
    const station=state.status.station||{};const facts=[['Pi connection',station.connected?'Connected':'No recent heartbeat',station.station_id||'Station not yet identified'],['Listening',nice(station.listening),`Audio: ${nice(station.audio_status)} · recognition: ${nice(station.inference_status)}`],['Last heartbeat',station.last_heartbeat?date(station.last_heartbeat):'Not received','A heartbeat alone does not verify the microphone.']];
    $('maintenance-facts').innerHTML=facts.map(([label,value,note])=>`<div class="fact"><span>${escape(label)}</span><strong>${escape(value)}</strong><small>${escape(note)}</small></div>`).join('');
    const issues=state.status.issues||[];$('issue-count').textContent=`${issues.filter(i=>!i.resolved).length} unresolved`;
    $('issues-list').innerHTML=issues.length?issues.map(i=>`<article class="issue-item"><div class="issue-item-head"><div><h3>${escape(i.message||'Operational issue')}</h3><p>First ${escape(date(i.first_seen))} · latest ${escape(date(i.last_seen))} · ${num(i.occurrences??1)} ${(i.occurrences??1)===1?'occurrence':'occurrences'}</p></div>${badge(i.resolved?'Recovered':nice(i.severity||'Needs attention'),i.resolved?'':'warm')}</div>${!i.resolved?`<button class="text-link" data-diagnose="${escape(i.id)}" ${!state.status.settings?.ai_configured?'disabled':''}>Ask AI to explain this issue ↗</button>`:''}</article>`).join(''):'<div class="empty-state"><span aria-hidden="true">↺</span><h2>No recorded issues.</h2><p>Automatic diagnostic reports and recovery outcomes will collect here.</p></div>';
    const notifications=state.status.notifications||[];
    $('notification-list').innerHTML=notifications.length?notifications.slice(0,15).map(n=>`<article class="issue-item"><div class="issue-item-head"><div><h3>${escape(nice(n.kind))}${n.species?` · ${escape(n.species)}`:''}</h3><p>${escape(date(n.created_at))} · ${num(n.attempts)} delivery attempts${n.last_error?`<br>${escape(n.last_error)}`:''}</p></div>${badge(nice(n.status),['failed','uncertain'].includes(n.status)?'warm':'')}</div>${n.status==='uncertain'?`<button class="text-link" data-email-retry="${escape(n.id)}">Check inbox, then retry →</button>`:''}</article>`).join(''):'<p class="small muted">No notification deliveries have been recorded.</p>';
  }
  function loadSettings(){
    if(state.settingsLoaded)return;const s=state.status.settings||{};const form=$('settings-form');
    for(const field of ['profile','ai_daily_job_limit','site_name','timezone','confidence_threshold','display_cooldown_seconds','notification_email','smtp_host','smtp_port','smtp_user','smtp_from','ai_text_model','ai_image_model'])if(s[field]!==undefined&&form.elements[field])form.elements[field].value=s[field];
    if(s.smtp_tls!==undefined)form.elements.smtp_tls.checked=!!s.smtp_tls;
    state.settingsLoaded=true;
  }
  function settingsStatus(){const s=state.status.settings||{};$('email-state').textContent=s.email_configured?'Email configured':'Email not configured';$('ai-state').textContent=s.ai_configured?'AI credentials configured':'AI not configured';$('remote-settings-note').hidden=localHost;$('remove-ai-key').disabled=!localHost;if(!localHost)document.querySelectorAll('[data-secrets] input').forEach(input=>input.disabled=true);}
  async function refreshView(){
    try {
      if(state.view==='birds'){const [birds,events]=await Promise.all([api(`/api/admin/birds?period=${encodeURIComponent($('period-select').value)}`),api('/api/admin/detections')]);state.birds=birds.birds||[];state.detections=events.detections||[];renderBirds();}
      else if(state.view==='atelier'){const jobs=await api('/api/admin/jobs');state.jobs=jobs.jobs||[];renderAtelier();}
      else if(state.view==='maintenance')renderMaintenance();
      else if(state.view==='settings'){loadSettings();settingsStatus();}
    }catch(e){if(state.authenticated)banner(e.message,true);}
  }
  async function refresh(){
    if(state.busy)return;state.busy=true;
    try{
      const s=await api('/api/admin/status');state.status=s;unlock();
      if(!state.catalogue.length){const cat=await api('/api/catalogue');state.catalogue=cat.birds||[];}
      state.jobs=Array.isArray(s.jobs)?s.jobs:state.jobs;
      $('site-name').textContent=s.settings?.site_name||'The garden';$('profile-label').textContent=({'mac-mvp':'MacBook MVP','linux-production':'Dedicated Linux host'})[s.profile||s.settings?.profile]||'local installation';
      $('connection-label').className='connection-label connected';$('connection-label').innerHTML='<i></i> Server connected';
      $('last-updated').textContent=`Updated ${new Date().toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'})}`;
      renderOverview();populateSelectors();await refreshView();
    }catch(e){if(state.authenticated){$('connection-label').className='connection-label failed';$('connection-label').innerHTML='<i></i> Server unavailable';banner('The server could not be reached. This page may show older information. Check the startup window; queued Pi reports will retry after reconnection.',true);}else if(!$('unlock').hidden){/* A normal locked dashboard. */}else{lock();message('unlock-error','Cannot reach the server. Check Start Songsketch.command, then try again.',true);}}
    finally{state.busy=false;}
  }
  $('unlock-form').addEventListener('submit',async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{await post('/api/session',{token:$('operator-token').value});$('operator-token').value='';message('unlock-error','');await refresh();}catch(error){message('unlock-error',error.message,true);}finally{button.disabled=false;}});
  $('lock-dashboard').addEventListener('click',async()=>{try{await post('/api/admin/logout');}finally{$('station-token').value='';$('station-token-reveal').hidden=true;lock();}});
  $('refresh-button').addEventListener('click',refresh);window.addEventListener('hashchange',setView);
  $('test-form').addEventListener('submit',async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{await post('/api/admin/test-detection',{scientific_name:$('test-species').value});message('test-message','Test sent. Open the painting page to watch it arrive.');await refresh();}catch(error){message('test-message',error.message,true);}finally{button.disabled=false;}});
  $('period-select').addEventListener('change',refreshView);$('bird-search').addEventListener('input',renderBirds);$('missing-only').addEventListener('change',renderBirds);$('job-kind').addEventListener('change',jobKindNote);
  function confirmJob(request){
    if(!state.status?.settings?.ai_configured){banner('Configure optional AI credentials in Garden settings first.',true);return;}
    if(['artwork','animation'].includes(request.kind)&&!request.scientific_name){message('job-message','Choose a bird for this request.',true);return;}
    state.pendingJob=request;
    const descriptions={artwork:['Create a portrait draft?','The generated image will remain a draft until you approve it. A still portrait does not automatically become a finished animation.','The selected species, your direction, art prompt and project style reference images.'],style:['Propose a style update?','The result is a written proposal for review. Existing approved artwork is preserved.','The project’s style instructions and relevant reference material.'],animation:['Prepare an animation proposal?','This creates a written registration proposal for approved artwork. Existing prepared animations can be previewed; the job does not generate a new finished painting sequence.','The selected species, approved artwork and painting system instructions.'],diagnose:['Explain the diagnostics?','The result explains the selected issue and suggests next steps. It does not execute model-written repair commands.','A server-selected diagnostic summary and relevant recent logs. Credentials must be excluded by the report collector.']};
    const [title,description,shared]=descriptions[request.kind];$('job-dialog-title').textContent=title;$('job-dialog-description').textContent=description;$('job-shared-data').textContent=shared;$('job-dialog').showModal();
  }
  $('job-form').addEventListener('submit',e=>{e.preventDefault();const kind=$('job-kind').value;const species=$('job-species').value;const bird=[...state.catalogue,...(state.status.missing_art||[])].find(b=>b.scientific_name===species);confirmJob({kind,direction:$('job-direction').value.trim(),...(['artwork','animation'].includes(kind)?{scientific_name:species,common_name:bird?.common_name||species}:{})});});
  $('job-cancel').addEventListener('click',()=>{$('job-dialog').close();state.pendingJob=null;});
  $('job-confirm').addEventListener('click',async()=>{const request=state.pendingJob;if(!request)return;$('job-confirm').disabled=true;try{const result=await post('/api/admin/jobs',{...request,confirm_paid:true});$('job-dialog').close();state.pendingJob=null;banner(`Job ${result.job?.status||'started'}. Its progress will appear at the art table.`);location.hash='atelier';await refresh();}catch(error){$('job-dialog').close();banner(error.message,true);}finally{$('job-confirm').disabled=false;}});
  document.addEventListener('click',async e=>{
    const draft=e.target.closest('[data-draft]');if(draft){$('job-kind').value='artwork';$('job-species').value=draft.dataset.draft;jobKindNote();$('job-form').scrollIntoView({behavior:'smooth',block:'center'});}
    const diagnose=e.target.closest('[data-diagnose]');if(diagnose)confirmJob({kind:'diagnose',issue_id:diagnose.dataset.diagnose});
    const approve=e.target.closest('[data-approve]');if(approve){const job=state.jobs.find(j=>String(j.id)===approve.dataset.approve);if(!job)return;const detail=job.kind==='artwork'?'Approve this portrait for the live catalogue? The still image becomes available; animation remains a separate task.':'Record approval of this reviewed result? This does not execute arbitrary proposed repair commands.';if(!confirm(detail))return;approve.disabled=true;try{await post(`/api/admin/jobs/${encodeURIComponent(job.id)}/approve`);state.catalogue=[];banner('Approval recorded.');await refresh();}catch(error){banner(error.message,true);}finally{approve.disabled=false;}}
    const retry=e.target.closest('[data-email-retry]');if(retry){if(!confirm('Check the recipient inbox first. Only continue if this message did not arrive; retrying an uncertain delivery could otherwise send a duplicate.'))return;retry.disabled=true;try{await post('/api/admin/email-retry-confirmed',{id:retry.dataset.emailRetry,checked_inbox:true});banner('Confirmed email delivery queued for retry.');await refresh();}catch(error){banner(error.message,true);}finally{retry.disabled=false;}}
    const action=e.target.closest('[data-maintenance]');if(action){action.disabled=true;try{const result=await post('/api/admin/maintenance',{action:action.dataset.maintenance});banner(result.message||'Maintenance request completed.');await refresh();}catch(error){banner(error.message,true);}finally{action.disabled=false;}}
  });
  $('diagnostics-button').addEventListener('click',async()=>{$('diagnostics-button').disabled=true;try{const report=await post('/api/admin/diagnostics');const blob=new Blob([JSON.stringify(report,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`songsketch-support-${new Date().toISOString().slice(0,10)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);banner('Support report downloaded. Review it before sharing outside your installation.');}catch(error){banner(error.message,true);}finally{$('diagnostics-button').disabled=false;}});
  $('station-token-button').addEventListener('click',async()=>{$('station-token-button').disabled=true;try{const result=await post('/api/admin/station-token');$('station-token').value=result.station_token||'';$('station-token-reveal').hidden=false;$('station-token').focus();}catch(error){banner(error.message,true);}finally{$('station-token-button').disabled=false;}});
  $('hide-station-token').addEventListener('click',()=>{$('station-token').value='';$('station-token-reveal').hidden=true;});
  $('remove-ai-key').addEventListener('click',()=>{$('remove-ai-confirm').hidden=false;$('remove-ai-key').setAttribute('aria-expanded','true');$('confirm-remove-ai-key').focus();});
  $('cancel-remove-ai-key').addEventListener('click',()=>{$('remove-ai-confirm').hidden=true;$('remove-ai-key').setAttribute('aria-expanded','false');$('remove-ai-key').focus();});
  $('confirm-remove-ai-key').addEventListener('click',async()=>{$('confirm-remove-ai-key').disabled=true;try{await post('/api/admin/settings',{remove_ai_key:true});$('setting-ai-key').value='';$('remove-ai-confirm').hidden=true;$('remove-ai-key').setAttribute('aria-expanded','false');state.settingsLoaded=false;message('settings-message','Saved AI key removed. Normal playback and maintenance are unchanged.');await refresh();}catch(error){message('settings-message',error.message,true);}finally{$('confirm-remove-ai-key').disabled=false;}});
  $('settings-form').addEventListener('submit',async e=>{e.preventDefault();const form=e.currentTarget,button=e.submitter;const data={profile:form.elements.profile.value,ai_daily_job_limit:Number(form.elements.ai_daily_job_limit.value),site_name:form.elements.site_name.value.trim(),timezone:form.elements.timezone.value.trim(),confidence_threshold:Number(form.elements.confidence_threshold.value),display_cooldown_seconds:Number(form.elements.display_cooldown_seconds.value)};
    if(localHost){for(const key of ['notification_email','smtp_host','smtp_user','smtp_from','ai_text_model','ai_image_model'])data[key]=form.elements[key].value.trim();for(const key of ['smtp_password','openai_api_key'])if(form.elements[key].value)data[key]=form.elements[key].value;if(form.elements.smtp_port.value)data.smtp_port=Number(form.elements.smtp_port.value);data.smtp_tls=form.elements.smtp_tls.checked;}
    button.disabled=true;try{await post('/api/admin/settings',data);form.elements.smtp_password.value='';form.elements.openai_api_key.value='';state.settingsLoaded=false;message('settings-message','Settings saved. Saved secrets stay hidden.');await refresh();}catch(error){message('settings-message',error.message,true);}finally{button.disabled=false;}
  });
  setView();refresh();setInterval(()=>{if(!document.hidden&&state.authenticated)refresh();},5000);
})();
