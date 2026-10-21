/* The guide presents observed setup state. It never marks hardware complete by navigation. */
const $ = id => document.getElementById(id);
const project = window.SONGSKETCH_PROJECT || {};
const repo = project.repository_url || 'https://github.com/katkinkead/songsketch';
const baseBrief = `Help me set up Songsketch from ${repo} or the release I have provided. Work on this computer using your local terminal and file tools. Read AGENTS.md, README.md and docs/ai-setup.md before doing anything. Inspect the existing installation first; Saber Lily has already built the server, Pi relay, dashboard, guide, artwork and animations. Do not rebuild them.
Own the software work: obtain the project using my existing GitHub access, run scripts/ai-bootstrap.py, open its guide, collect missing settings once, and use scripts/setup-assistant.py to connect and commission the Pi. Read --help for exact options. Use headless setup. If Pi OS or SSH is missing, help configure Imager and request approval for the exact card before erasing it. Keep passwords and tokens out of chat, prompts, logs and Git; use the local guide or a secure terminal.
Explain what is happening while you work. For a failure, read the saved checkpoint and diagnostic packet, identify the cause, try a narrowly scoped safe repair, verify it, then resume. Stop after two repair cycles without new evidence. Preserve existing installs, history, artwork, authentication and networking. Ask me only for missing credentials, SSH identity confirmation, necessary permissions or physical actions. Do not invent success: verify capture, inference, delivery and playback separately. Synthetic birds do not prove real hearing. No paid AI key is required for normal playback or the bundled BirdNET-Go model.`;
let setup = null, admin = null, unlocked = false, populatedId = null, busy = false;
const activeStates = new Set(['probing','running','cancelling']);
const terminalStates = new Set(['failed','needs_input','interrupted','cancelled']);
async function api(path, data) {
  const response = await fetch(path,{cache:'no-store',credentials:'same-origin',headers: data===undefined?{}:{'Content-Type':'application/json'},method:data===undefined?'GET':'POST',body:data===undefined?undefined:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) {const error=new Error(result.error || 'The helper could not finish that request.');error.status=response.status;throw error;}
  return result;
}
function message(value) {$('action-message').textContent=value;}
function evidence(id, good, detail) {const item=$(id);item.classList.toggle('verified',good);if(detail)item.querySelector('span').textContent=detail;}
function render() {
  const job=setup?.job; const state=job?.state; const running=activeStates.has(state);
  $('pi-fields').disabled=!unlocked || running || busy;
  $('legacy-unlock').hidden=unlocked;
  $('helper-explanation').textContent=unlocked?'The local helper is connected. Your AI can operate these same controls.':'Your AI starts the local helper first, then reopens this guide with a private session.';
  $('helper-state').textContent=unlocked?'Helper connected':'AI handoff ready';
  $('helper-state').classList.toggle('connected',unlocked);
  evidence('evidence-helper',unlocked,unlocked?'Local session connected; the helper can perform guarded setup actions.':'Waiting for a current connection to the local helper.');
  const descriptions={
    probing:['Knocking on the Pi’s door.','Checking the address and its SSH identity. No installation has started.'],
    awaiting_trust:['A quick introduction.','The Pi’s identity needs confirmation before the helper can connect.'],
    ready:['We’ve met the Pi.','Its SSH identity is recorded. The helper is ready to connect and set up listening.'],
    running:['A little wiring behind the scenes.','The helper is working on the Pi. Progress below comes from the setup job.'],
    cancelling:['Stopping this attempt.','The helper is ending its connection. Saved state and existing history are kept.'],
    completed:['The software checks passed.','Now check the painting and watch for real listening reports. The hardware still needs its own test.'],
    failed:['A hiccup. Finchley has notes.','The failed checkpoint is saved. Your AI can inspect it and continue from the evidence.'],
    needs_input:['One thing needs a closer look.','The helper has saved what it found and the next action it needs.'],
    interrupted:['Picking up the thread.','The server restarted during setup. Your AI should diagnose the saved checkpoint before resuming.'],
    cancelled:['Parked, with notes intact.','Your AI can inspect the checkpoint before deciding how to continue.']
  };
  let description=descriptions[state] || (unlocked?['The Mac is ready.','Your AI can now connect to the Pi. It handles the setup; this page shows its progress.']:['Your AI takes it from here.','Give your local assistant the brief above. It will start the helper and reopen this guide, ready to connect.']);
  if(!unlocked) description=['Your AI takes it from here.','The helper is not connected to this guide. Give your local assistant the brief above to start or reconnect it. Saved notes below are historical, not current health.'];
  else if(state==='completed' && job?.operation==='diagnose') description=['The Pi check is back.','The diagnostic report is saved below. This check does not install software or prove the garden is hearing.'];
  $('live-heading').textContent=description[0];$('live-description').textContent=description[1];
  const amount=Math.max(0,Math.min(100,Number(job?.progress)||0));
  $('setup-fill').style.width=amount+'%';document.querySelector('.setup-meter').setAttribute('aria-valuenow',amount);
  evidence('evidence-pi',unlocked && Boolean(job?.trusted),state==='awaiting_trust'?'Waiting for you to confirm this Pi’s identity.':job?.trusted?'This Pi’s SSH identity has been explicitly trusted.':'Checks the address and the Pi’s SSH identity.');
  evidence('evidence-install',unlocked && Boolean(job?.commissioned),job?.commissioned?'The remote installer completed its checks.':running && job?.operation?job?.remote_progress?.message || 'The helper is checking the connection before working on BirdNET.':'Waiting for the installer’s verification.');
  const station=admin?.station; const healthy=unlocked && station?.connected && station?.listening==='available';
  evidence('evidence-hearing',healthy,healthy?'Recent Pi heartbeat reports healthy capture and recognition.':station?.ever_connected && !station?.connected?'No recent Pi report. The AI can check the connection.':'Waiting for real capture and recognition health from the Pi.');
  $('aftercare').hidden=!(job?.commissioned && healthy);
  $('test-panel').hidden=!unlocked;
  $('human-request').hidden=!job?.human_action;$('human-request').textContent=job?.human_action || '';
  $('trust-card').hidden=state!=='awaiting_trust';$('fingerprint').textContent=job?.challenge?.fingerprint || '';
  const actions=job?.next_actions||[];
  for(const [id,action] of [['install-pi','install'],['retry-pi','retry'],['diagnose-pi','diagnose'],['cancel-job','cancel']]) {$(id).hidden=!unlocked || !actions.includes(action);$(id).disabled=busy;}
  $('trust-pi').disabled=busy;
  $('repair-card').hidden=!terminalStates.has(state);
  $('auth-fields').hidden=!unlocked || !actions.some(x=>['install','retry','diagnose'].includes(x));
  const sources=job?.result?.capture_sources||[];
  $('capture-label').hidden=!sources.length;
  const select=$('capture-device');const signature=JSON.stringify(sources);
  if(select.dataset.signature!==signature){select.replaceChildren(new Option('Choose the microphone',''));for(const source of sources)select.add(new Option(source.name||source.label||source.id,source.id));select.dataset.signature=signature;}
  $('job-log').textContent=job?JSON.stringify({state:job.state,stage:job.stage,progress:job.progress,logs:job.logs,error:job.error,result:job.result},null,2):'No setup job has run yet.';
  if(job?.inputs && job.id!==populatedId){for(const [key,value] of Object.entries(job.inputs)){const field=$('pi-form').elements.namedItem(key);if(field)field.value=value;}populatedId=job.id;}
}
async function refresh(){
  if(location.protocol==='file:'){render();return;}
  try {const [state,status]=await Promise.all([api('/api/admin/setup'),api('/api/admin/status')]);setup=state;admin=status;unlocked=true;render();}
  catch(error){unlocked=false;render();if(error.status!==401 && error.status!==403){$('helper-state').textContent='Helper not connected';}}
}
async function action(name,fields={}){
  if(busy)return;busy=true;render();message('');
  const password=$('ssh-password').value;$('ssh-password').value='';
  const data={...(name!=='probe' && setup?.job?{job_id:setup.job.id}:{}),...fields};
  if(['install','retry','diagnose'].includes(name)){if(password)data.password=password;if(name!=='diagnose' && $('capture-device').value)data.capture_device=$('capture-device').value;}
  try {await api('/api/admin/setup/'+name,data);await refresh();}
  catch(error){message(error.message+' Your AI can read the saved diagnostics.');}
  finally{delete data.password;busy=false;render();}
}
async function copyText(text,button){
  try{await navigator.clipboard.writeText(text);const original=button.textContent;button.textContent='Copied — ready for your AI';setTimeout(()=>button.textContent=original,4000);}
  catch{const blob=new Blob([text],{type:'text/plain'});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='songsketch-ai-brief.txt';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),2000);$('copy-feedback').textContent='Saved a text brief to give your local AI.';}
}
$('begin').onclick=()=>$('setup').scrollIntoView({behavior:'smooth'});
$('copy-handoff').onclick=()=>copyText(baseBrief,$('copy-handoff'));
$('copy-recovery').onclick=()=>copyText(baseBrief+'\n\nResume recovery now. Run the installed scripts/setup-assistant.py diagnose to read the current local diagnostic packet. The last observed setup state was '+(setup?.job?.state||'unknown')+', checkpoint '+(setup?.job?.stage||'unknown')+'. Re-read live state; this brief may be older than the job. Do not ask me to troubleshoot routine software faults.',$('copy-recovery'));
$('pi-form').addEventListener('submit',async event=>{event.preventDefault();const form=$('pi-form');const fields=Object.fromEntries(new FormData(form));fields.latitude=Number(fields.latitude);fields.longitude=Number(fields.longitude);await action('probe',fields);});
$('pi-form').addEventListener('invalid',()=>{$('network-details').open=true;},true);
$('trust-pi').onclick=()=>action('trust',{challenge_id:setup.job.challenge.challenge_id,fingerprint:setup.job.challenge.fingerprint,confirmed:true});
$('install-pi').onclick=()=>action('install');$('retry-pi').onclick=()=>action('retry');$('diagnose-pi').onclick=()=>action('diagnose');$('cancel-job').onclick=()=>action('cancel');
$('unlock-form').onsubmit=async event=>{event.preventDefault();const token=$('setup-token').value;$('setup-token').value='';try{await api('/api/session',{token});await refresh();}catch(error){message(error.message);}};
$('download-diagnostics').onclick=async()=>{try{const packet=await api('/api/admin/setup-context');const url=URL.createObjectURL(new Blob([JSON.stringify(packet,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='songsketch-setup-diagnostics.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}catch(error){message(error.message);}};
$('test-painting').onclick=async()=>{try{await api('/api/admin/test-detection',{scientific_name:'Erithacus rubecula'});$('test-result').textContent='A test robin is ready on the painting page. It will not count as a real bird detection.';}catch(error){$('test-result').textContent=error.message;}};
for(const [id,url] of [['repository-link',repo],['release-link',project.release_url]]){if(url){$(id).href=url;$(id).hidden=false;}}
async function consumeOpeningTicket(){
  const fragment=new URLSearchParams(location.hash.slice(1));const ticket=fragment.get('ticket');
  if(ticket){history.replaceState(null,'',location.pathname+location.search);try{await api('/api/setup/session',{ticket});}catch(error){message(error.message);}}
  await refresh();
}
window.addEventListener('hashchange',()=>{if(new URLSearchParams(location.hash.slice(1)).has('ticket'))consumeOpeningTicket();});
consumeOpeningTicket();
setInterval(refresh,3500);
