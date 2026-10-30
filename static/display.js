/* Connected display: approved local paintings; server-owned playback/history. */
(() => {
  'use strict';
  const stage = document.getElementById('paintings');
  const annotation = document.getElementById('annotation');
  const label = document.getElementById('status-label');
  const icon = document.querySelector('#status-icon use');
  const progress = document.getElementById('progress');
  const catalogue = new Map();
  let status = null, displayed = null, activeFrame = null, pending = null;
  let transportHealthy = false, lastStateAt = 0, events = null, retryTimer = 0;
  const relativeTime = timestamp => {
    const time = Date.parse(timestamp);
    if (!Number.isFinite(time)) return '';
    return new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/London',hour:'2-digit',minute:'2-digit',day:'numeric',month:'short'}).format(new Date(time));
  };
  function setAnnotation(mark, text) {
    icon.setAttribute('href', '#mark-'+mark);
    label.textContent = text;
    annotation.hidden = !text;
  }
  function updateAnnotation() {
    if (!status) { setAnnotation('offline', 'Connecting to the garden'); return; }
    if (!transportHealthy) { setAnnotation('offline', 'Display offline'); return; }
    const station = status.station || {};
    const testPrefix = displayed?.test ? 'Test painting · ' : '';
    if (!station.connected) {
      setAnnotation('pie', testPrefix+(station.last_heartbeat ? 'Pi disconnected' : 'Pi not connected')); return;
    }
    if (station.listening === 'unavailable') { setAnnotation('microphone', testPrefix+'Listening unavailable'); return; }
    if (!displayed) { setAnnotation('leaf', ''); return; }
    if (displayed.test) { setAnnotation('leaf', 'Test painting'); return; }
    const age = Date.now()-Date.parse(displayed.observed_at || '');
    if (displayed.mode === 'live' && Number.isFinite(age) && age >= -5000 && age < 15000) {
      setAnnotation('ripple','Heard just now');
    } else if (displayed.mode === 'monthly' && Number.isFinite(displayed.monthly_count)) {
      setAnnotation('memory', `Heard here ${displayed.monthly_count} times this month`);
    } else if (displayed.observed_at && relativeTime(displayed.observed_at)) {
      setAnnotation('memory', 'Last heard '+relativeTime(displayed.observed_at));
    } else {
      setAnnotation('leaf', 'Local bird');
    }
  }
  function elapsed(current) {
    const start = Date.parse(current.started_at);
    return Number.isFinite(start) ? Math.max(0,Math.min(75,(Date.now()-start)/1000)) : 0;
  }
  function safeAnimation(bird) {
    if (!bird?.approved || !bird.animation_ready || !bird.animation_url) return null;
    const url = new URL(bird.animation_url, location.origin);
    return url.origin === location.origin && /^\/artwork\/animations\/[a-z0-9-]+\.html$/.test(url.pathname) && !url.search ? url.href : null;
  }
  function switchPainting(current) {
    if (!current?.event_id || current.event_id === displayed?.event_id || current.event_id === pending?.current.event_id) return;
    const bird = catalogue.get(current.artwork_id);
    const url = safeAnimation(bird);
    if (!url) return; // Keep the last painting for missing/unapproved assets.
    if (pending) { clearTimeout(pending.timeout); pending.frame.remove(); }
    const frame = document.createElement('iframe');
    frame.title = `${bird.common_name} painting`;
    frame.setAttribute('sandbox','allow-scripts allow-same-origin');
    frame.src = url;
    pending = {frame, current:{...current}, timeout:setTimeout(() => {
      if (pending?.frame === frame) { window.displayReporter?.report('painting-timeout',current.artwork_id); frame.remove(); pending = null; }
    },65000)};
    stage.append(frame);
  }
  function receiveState(next) {
    if (!next || typeof next !== 'object' || !next.station) return;
    status = next; lastStateAt = Date.now(); transportHealthy = true;
    switchPainting(next.current);
    updateAnnotation();
  }
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || !event.data) return;
    const data = event.data;
    if (pending && event.source === pending.frame.contentWindow) {
      if (data.type === 'songsketch:ready') {
        pending.frame.contentWindow.postMessage({type:'songsketch:play',event_id:pending.current.event_id,elapsed_seconds:elapsed(pending.current)},location.origin);
      } else if (data.type === 'songsketch:started' && data.event_id === pending.current.event_id) {
        clearTimeout(pending.timeout);
        const previous = activeFrame;
        activeFrame = pending.frame; displayed = pending.current; pending = null;
        activeFrame.classList.add('active');
        document.getElementById('welcome').hidden = true;
        if (previous) setTimeout(() => previous.remove(),500);
        updateAnnotation();
      } else if (data.type === 'songsketch:error') {
        window.displayReporter?.report('render-failed',pending.current.artwork_id);
        clearTimeout(pending.timeout); pending.frame.remove(); pending = null;
      }
    }
    if (event.source === activeFrame?.contentWindow && data.type === 'songsketch:progress' && data.event_id === displayed?.event_id) {
      const seconds = Math.max(0,Math.min(75,Number(data.seconds)||0));
      progress.hidden = false;
      progress.setAttribute('aria-valuenow',String(Math.round(seconds)));
      progress.querySelector('span').style.width = `${seconds/75*100}%`;
      progress.classList.toggle('complete', seconds >= 75);
    }
  });
  async function fetchState() {
    try {
      const response = await fetch('/api/public/status',{cache:'no-store',signal:AbortSignal.timeout(7000)});
      if (!response.ok) throw new Error('Status unavailable');
      receiveState(await response.json());
    } catch (_) { transportHealthy = false; updateAnnotation(); }
  }
  function connectEvents() {
    if (events) events.close();
    events = new EventSource('/events');
    events.addEventListener('state', event => { try { receiveState(JSON.parse(event.data)); } catch (_) {} });
    events.onopen = () => fetchState();
    events.onerror = () => { transportHealthy = false; updateAnnotation(); };
  }
  async function initialise() {
    try {
      const response = await fetch('/api/catalogue',{cache:'no-store',signal:AbortSignal.timeout(7000)});
      if (!response.ok) throw new Error('Catalogue unavailable');
      const data = await response.json();
      for (const bird of data.birds || []) if (bird.id) catalogue.set(bird.id,bird);
      await fetchState();
      connectEvents();
    } catch (_) {
      setAnnotation('offline','Display offline');
      clearTimeout(retryTimer); retryTimer = setTimeout(initialise,5000);
    }
  }
  // Polling also detects silent/stalled streaming connections; this never
  // requests a new painting or infers equipment failure from a quiet garden.
  setInterval(() => { if (Date.now()-lastStateAt > 10000) fetchState(); updateAnnotation(); },5000);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      fetchState();
      if (activeFrame && displayed) activeFrame.contentWindow.postMessage({type:'songsketch:play',event_id:displayed.event_id,elapsed_seconds:elapsed(displayed)},location.origin);
    }
  });
  document.getElementById('fullscreen').addEventListener('click',async () => {
    try { if (!document.fullscreenElement) await document.documentElement.requestFullscreen(); else await document.exitFullscreen(); } catch (_) {}
  });
  window.addEventListener('offline', () => { transportHealthy = false; updateAnnotation(); });
  window.addEventListener('online', fetchState);
  initialise();
})();
