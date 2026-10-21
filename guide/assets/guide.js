/* Navigation describes the install journey; only observed evidence marks checks healthy. */
const $ = id => document.getElementById(id);
const project = window.SONGSKETCH_PROJECT || {};
const repo = project.repository_url || 'https://github.com/katkinkead/songsketch';
const stages=['parts','prepare','details','install','progress'];
let context=null, setup=null, unlocked=false, busy=false, currentStep='parts', populatedId=null, observedJob=null, refreshInFlight=false;
const activeStates=new Set(['probing','running','cancelling']);
const terminalStates=new Set(['failed','needs_input','interrupted','cancelled']);
function storedGet(key){try{return JSON.parse(localStorage.getItem(key));}catch{return null;}}
function storedSet(key,value){try{localStorage.setItem(key,JSON.stringify(value));}catch{/* Browser storage may be disabled. Fields still work this visit. */}}
function showStep(step,focus=true){
  if(!stages.includes(step))return;
  currentStep=step;
  document.querySelectorAll('[data-page]').forEach(page=>page.hidden=page.dataset.page!==step);
  document.querySelectorAll('[data-step]').forEach(button=>{if(button.dataset.step===step)button.setAttribute('aria-current','step');else button.removeAttribute('aria-current');});
  if(!location.hash.includes('ticket='))history.replaceState(null,'',location.pathname+location.search+'#'+step);
  if(focus){const heading=document.querySelector(`[data-page="${step}"] h2`);heading.focus({preventScroll:true});$('setup').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});}
}
function detailValues(){
  const values={};for(const [key,value] of new FormData($('pi-form'))){if(String(value).trim())values[key]=['latitude','longitude'].includes(key)?Number(value):String(value).trim();}return values;
}
function populateDetails(values){if(!values)return;for(const [key,value] of Object.entries(values)){const field=$('pi-form').elements.namedItem(key);if(field)field.value=value;}}
async function api(path,data){
  const response=await fetch(path,{cache:'no-store',credentials:'same-origin',headers:data===undefined?{}:{'Content-Type':'application/json'},method:data===undefined?'GET':'POST',body:data===undefined?undefined:JSON.stringify(data)});
  const result=await response.json();if(!response.ok){const error=new Error(result.error||'The helper could not finish that request.');error.status=response.status;throw error;}return result;
}
function textElement(tag,text,className){const element=document.createElement(tag);element.textContent=text;if(className)element.className=className;return element;}
function message(value){$('action-message').textContent=value;}
const componentDefaults=[['server','Mac server','On this Mac','Starts the local app and saves bird history.'],['garden_pi','Garden Pi','In the garden','Checks its address and secure connection.'],['microphone','Microphone','On the Pi','Checks that audio is actually arriving.'],['birdnet','BirdNET','On the Pi','Checks that the recogniser is processing audio.'],['delivery','Bird delivery','Pi → Mac','Checks that reports reach the server.'],['display','Painting page','In your browser','Your turn: open and try a painting.'],['power','Pi power','On the Pi','Checks for voltage and supply warnings.'],['thermal','Pi temperature','On the Pi','Checks temperature and thermal warnings.']];
function renderHealth(){
  const items=unlocked && context?.health?.components || componentDefaults.map(([id,label,location,message])=>({id,label,location,message,status:'not_started'}));
  const fragment=document.createDocumentFragment();
  const labels={healthy:'Checked',attention:'Needs attention',working:'In progress',unverified:'Not verified',not_started:'Waiting'};
  for(const item of items){const card=textElement('article','', 'component-card '+item.status);const top=textElement('div','', 'component-top');top.append(textElement('span',item.location,'component-location'),textElement('span',labels[item.status]||'Not verified','check-state'));card.append(top,textElement('h3',item.label),textElement('p',item.message));if(item.stage && item.status==='working')card.append(textElement('small',item.stage));fragment.append(card);}
  $('component-grid').replaceChildren(fragment);
  const problems=document.createDocumentFragment();
  if(unlocked)for(const item of context?.health?.problems||[]){const card=textElement('article','', 'problem-card');card.append(textElement('span',item.location,'eyebrow'),textElement('h3',item.message));if(item.stage||item.code)card.append(textElement('p',[item.stage,item.code].filter(Boolean).join(' · '),'problem-code'));if(item.next_action)card.append(textElement('p',item.next_action));problems.append(card);}
  $('problem-list').replaceChildren(problems);
}
function render(){
  const job=setup?.job, state=job?.state, running=activeStates.has(state), actions=job?.next_actions||[];
  $('pi-fields').disabled=busy||running;
  $('helper-state').textContent=unlocked?'Local helper connected':'Waiting for the local helper';
  $('helper-state').classList.toggle('connected',unlocked);
  $('legacy-unlock').hidden=unlocked;
  $('launch-assistant').disabled=busy;
  $('launch-explanation').textContent=unlocked?'Opens your installed assistant in Terminal. GitHub sign-in and AI permissions appear there if needed.':'On first use, unzip the download and open the Mac launcher once. A browser can’t start local programs by itself.';
  const descriptions={probing:['Finding your garden Pi.','Checking its address and SSH identity.'],awaiting_trust:['A quick introduction.','Confirm the Pi’s identity below so the assistant can connect.'],ready:['Ready to connect.','The Pi’s SSH identity is recorded. Your assistant can start the installation.'],running:['The little team is getting to work.','These checks follow the real installation. Any problem appears beside the part that needs attention.'],cancelling:['Stopping this attempt.','Existing settings and history are kept.'],completed:['The software check is complete.','Check the live listening results below, then try a painting.'],failed:['A hiccup. We’ve kept the notes.','The location and failed check are below. Your AI can diagnose and resume from here.'],needs_input:['One thing needs your attention.','The helper has saved what it found. Follow the specific request below.'],interrupted:['Ready to pick up again.','The server restarted during setup. Your AI can read the saved checkpoint before resuming.'],cancelled:['Paused, with notes intact.','Your AI can inspect the checkpoint and continue.']};
  let description=descriptions[state]||['Waiting for your AI.','Once the assistant starts setup, each part here shows its current check.'];
  if(!unlocked)description=['Waiting for the local helper.','Open the installer to connect this guide. Previous checks are not current health.'];
  else if(state==='completed'&&job.operation==='diagnose')description=['The diagnostic check is back.','Its evidence is below. A diagnostic check does not itself install or commission the Pi.'];
  $('live-heading').textContent=description[0];$('live-description').textContent=description[1];
  const amount=unlocked?Math.max(0,Math.min(100,Number(job?.progress)||0)):0;
  $('setup-fill').style.width=amount+'%';document.querySelector('.setup-meter').setAttribute('aria-valuenow',amount);
  renderHealth();
  $('human-request').hidden=!unlocked||!job?.human_action;$('human-request').textContent=job?.human_action||'';
  $('trust-card').hidden=!unlocked||state!=='awaiting_trust';$('fingerprint').textContent=job?.challenge?.fingerprint||'';
  for(const [id,action] of [['install-pi','install'],['retry-pi','retry'],['diagnose-pi','diagnose'],['cancel-job','cancel']]){$(id).hidden=!unlocked||!actions.includes(action);$(id).disabled=busy;}
  $('trust-pi').disabled=busy;$('resume-assistant').disabled=busy;
  $('repair-card').hidden=!unlocked||!(terminalStates.has(state)||context?.health?.problems?.length);
  $('auth-fields').hidden=!unlocked||!actions.some(x=>['install','retry','diagnose'].includes(x));
  const sources=job?.result?.capture_sources||[], select=$('capture-device'), signature=JSON.stringify(sources);
  $('capture-label').hidden=!sources.length;
  if(select.dataset.signature!==signature){select.replaceChildren(new Option('Choose the microphone',''));for(const source of sources)select.add(new Option(source.name||source.label||source.id,source.id));select.dataset.signature=signature;}
  $('job-log').textContent=job?JSON.stringify({state:job.state,stage:job.stage,progress:job.progress,logs:job.logs,error:job.error,result:job.result},null,2):'No setup job has run yet.';
  if(job?.inputs&&job.id!==populatedId&&currentStep!=='details'){populateDetails(job.inputs);populatedId=job.id;}
  if(unlocked&&job?.id&&job.id!==observedJob){observedJob=job.id;if(currentStep==='install')showStep('progress');}
  const healthy=context?.health?.components?.filter(c=>['microphone','birdnet','delivery'].includes(c.id)).every(c=>c.status==='healthy');
  $('aftercare').hidden=!(unlocked&&job?.commissioned&&healthy);
  $('test-panel').hidden=!unlocked;
  const launcher=unlocked&&context?.launcher;
  $('launch-status').hidden=!launcher?.phase;
  if(launcher?.phase)$('launch-status').textContent=launcher.message||({fetching:'Getting the project from GitHub…',source_ready:'Project downloaded from GitHub.',assistant_started:'Assistant opened. Installation checks will appear below.',failed:'The installer needs attention. Open its Terminal window for the reported problem.'}[launcher.phase]||launcher.phase);
}
async function refresh(){
  if(location.protocol==='file:'||refreshInFlight){render();return;}
  refreshInFlight=true;
  try{context=await api('/api/admin/setup-context');setup=context.setup;unlocked=true;if(!populatedId&&!Object.keys(detailValues()).length&&context.details)populateDetails(context.details);render();}
  catch(error){unlocked=false;render();}
  finally{refreshInFlight=false;}
}
async function action(name,fields={}){
  if(busy)return;busy=true;render();message('');
  const password=$('ssh-password').value;$('ssh-password').value='';
  const data={...(setup?.job?{job_id:setup.job.id}:{}),...fields};
  if(['install','retry','diagnose'].includes(name)){if(password)data.password=password;if(name!=='diagnose'&&$('capture-device').value)data.capture_device=$('capture-device').value;}
  try{await api('/api/admin/setup/'+name,data);await refresh();}catch(error){message(error.message);}finally{delete data.password;busy=false;render();}
}
function base64Utf8(value){const bytes=new TextEncoder().encode(value);let binary='';for(const byte of bytes)binary+=String.fromCharCode(byte);return btoa(binary);}
function download(text,name,type='text/plain'){const url=URL.createObjectURL(new Blob([text],{type}));const anchor=document.createElement('a');anchor.href=url;anchor.download=name;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
// A stored ZIP keeps the command executable when macOS extracts a browser download.
function launcherZip(command){
  const encoder=new TextEncoder(), name=encoder.encode('Install Songsketch.command'), data=encoder.encode(command);
  let crc=0xffffffff;for(const byte of data){crc^=byte;for(let bit=0;bit<8;bit++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}crc=(crc^0xffffffff)>>>0;
  const localSize=30+name.length+data.length, centralSize=46+name.length;
  const bytes=new Uint8Array(localSize+centralSize+22), view=new DataView(bytes.buffer);
  const u16=(at,value)=>view.setUint16(at,value,true),u32=(at,value)=>view.setUint32(at,value>>>0,true);
  u32(0,0x04034b50);u16(4,20);u16(12,33);u32(14,crc);u32(18,data.length);u32(22,data.length);u16(26,name.length);bytes.set(name,30);bytes.set(data,30+name.length);
  const c=localSize;u32(c,0x02014b50);u16(c+4,788);u16(c+6,20);u16(c+14,33);u32(c+16,crc);u32(c+20,data.length);u32(c+24,data.length);u16(c+28,name.length);u32(c+38,0x81c00000);bytes.set(name,c+46);
  const e=localSize+centralSize;u32(e,0x06054b50);u16(e+8,1);u16(e+10,1);u32(e+12,centralSize);u32(e+16,localSize);return bytes;
}
async function launchAssistant(){
  if(busy)return;
  if(!$('pi-form').checkValidity()){showStep('details');$('pi-form').reportValidity();return;}
  const details=detailValues(), assistant=$('assistant-choice').value;
  storedSet('songsketch-setup-details',details);busy=true;render();
  try{
    if(unlocked){const result=await api('/api/admin/launch-assistant',{details,assistant});if(!result.launched)throw new Error(result.message||'The assistant could not be opened.');$('launch-feedback').textContent=result.message||'Terminal opened. Follow any sign-in or permission request there.';showStep('progress');message('Terminal has opened the GitHub installer. This does not yet mean the Pi is configured.');}
    else{
      if(!window.SONGSKETCH_INSTALLER_TEMPLATE)throw new Error('The launcher file is missing. Download the complete Songsketch release from GitHub.');
      const command=window.SONGSKETCH_INSTALLER_TEMPLATE.replace('__SONGSKETCH_DETAILS_B64__',base64Utf8(JSON.stringify(details))).replace('__SONGSKETCH_ASSISTANT__',assistant).replace('__SONGSKETCH_DATA_DIR_B64__','');
      download(launcherZip(command),'Install Songsketch.zip','application/zip');
      $('launch-feedback').textContent='Downloaded. Unzip “Install Songsketch.zip”, then open the launcher inside on your Mac. It fetches GitHub, then opens your AI. If macOS blocks the file, keep the warning and use the signed local tools described in the project instructions.';
    }
  }catch(error){$('launch-feedback').textContent=error.message;message(error.message);}finally{busy=false;render();}
}
for(const button of document.querySelectorAll('[data-step]'))button.onclick=()=>showStep(button.dataset.step);
for(const button of document.querySelectorAll('[data-go]'))button.onclick=()=>showStep(button.dataset.go);
$('begin').onclick=()=>showStep('parts');
$('pi-form').onsubmit=async event=>{event.preventDefault();const details=detailValues();storedSet('songsketch-setup-details',details);try{if(unlocked)await api('/api/admin/setup-details',{details});showStep('install');}catch(error){$('details-feedback').textContent=error.message;}};
$('clear-details').onclick=async()=>{try{if(unlocked)await api('/api/admin/setup-details',{details:{}});storedSet('songsketch-setup-details',{});$('pi-form').reset();$('details-feedback').textContent='Saved setup details cleared. Existing Pi configuration is unchanged.';}catch(error){$('details-feedback').textContent=error.message;}};
$('pi-form').addEventListener('invalid',()=>{$('network-details').open=true;},true);
$('launch-assistant').onclick=launchAssistant;$('resume-assistant').onclick=launchAssistant;
$('trust-pi').onclick=()=>action('trust',{challenge_id:setup.job.challenge.challenge_id,fingerprint:setup.job.challenge.fingerprint,confirmed:true});
$('install-pi').onclick=()=>action('install');$('retry-pi').onclick=()=>action('retry');$('diagnose-pi').onclick=()=>action('diagnose');$('cancel-job').onclick=()=>action('cancel');
$('unlock-form').onsubmit=async event=>{event.preventDefault();const token=$('setup-token').value;$('setup-token').value='';try{await api('/api/session',{token});await refresh();}catch(error){message(error.message);}};
$('download-diagnostics').onclick=async()=>{try{const packet=await api('/api/admin/setup-context');download(JSON.stringify(packet,null,2),'songsketch-setup-diagnostics.json','application/json');}catch(error){message(error.message);}};
$('test-painting').onclick=async()=>{try{await api('/api/admin/test-detection',{scientific_name:'Erithacus rubecula'});$('test-result').textContent='A test robin is ready on the painting page. It does not count as a real detection.';}catch(error){$('test-result').textContent=error.message;}};
$('repository-link').href=repo;$('release-link').href=project.release_url||repo+'/releases';$('install-repo').href=repo;
populateDetails(storedGet('songsketch-setup-details'));
showStep(stages.includes(location.hash.slice(1))?location.hash.slice(1):'parts',false);
async function consumeOpeningTicket(){const fragment=new URLSearchParams(location.hash.slice(1)),ticket=fragment.get('ticket');if(ticket){history.replaceState(null,'',location.pathname+location.search);try{await api('/api/setup/session',{ticket});showStep('progress',false);}catch(error){message(error.message);}}await refresh();}
window.addEventListener('hashchange',()=>{if(location.hash.includes('ticket='))consumeOpeningTicket();else if(stages.includes(location.hash.slice(1)))showStep(location.hash.slice(1),false);});
consumeOpeningTicket();setInterval(refresh,3500);
