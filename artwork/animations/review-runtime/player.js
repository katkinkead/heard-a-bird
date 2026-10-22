/* Songsketch portrait bridge. The imported painting renderer remains unchanged. */
(() => {
  'use strict';
  const canvas = document.getElementById('painting'), ctx = canvas.getContext('2d');
  const loading = document.getElementById('loading'), controls = document.getElementById('review-controls');
  const slider = document.getElementById('time'), clock = document.getElementById('clock'), button = document.getElementById('play');
  const checks = document.getElementById('review-checks'), diagnostic = document.getElementById('painting-diagnostics');
  const embedded = parent !== window, duration = 75, preparedAt = performance.now();
  let painter = null, playing = false, seconds = 0, eventId = null, frame = 0, base = 0, lastReport = -1, preparingMs = null;
  function post(type, extra = {}) {
    if (embedded) parent.postMessage({type, event_id:eventId, ...extra}, location.origin);
  }
  function clamp(value) { return Math.max(0, Math.min(duration, Number.isFinite(value) ? value : 0)); }
  function draw(value, reset = false) {
    seconds = clamp(value);
    painter.renderAt(seconds, reset);
    ctx.clearRect(0, 0, 1000, 750); ctx.drawImage(painter.canvas, 0, 0);
    if (!embedded) { slider.value = seconds; clock.textContent = `${seconds.toFixed(1)} / 75 s`; }
  }
  function report(force = false) {
    if (force || seconds - lastReport >= .5 || seconds < lastReport) {
      lastReport = seconds; post('songsketch:progress', {seconds, duration});
      if (!embedded && painter) {
        const state = painter.getState();
        diagnostic.textContent = `Preparation: ${(preparingMs / 1000).toFixed(2)} seconds. Drawing: ${seconds.toFixed(1)} / 75 seconds. Marks complete: ${state.completed} / ${state.strokeCount}. Prepared cache: ${state.preparedScore ? 'yes' : 'no; authored marks built locally'}.`;
      }
    }
  }
  function pause() { playing = false; cancelAnimationFrame(frame); button.textContent = 'Play'; }
  function tick(now) {
    if (!playing || document.hidden) return;
    draw((now - base) / 1000); report();
    if (seconds >= duration) { pause(); report(true); } else frame = requestAnimationFrame(tick);
  }
  async function play(id, elapsed = 0) {
    await ready;
    pause(); eventId = String(id || 'review').slice(0, 160);
    draw(clamp(elapsed), elapsed < seconds); base = performance.now() - seconds * 1000;
    post('songsketch:started'); report(true);
    playing = seconds < duration; button.textContent = playing ? 'Pause' : 'Play';
    if (playing && !document.hidden) frame = requestAnimationFrame(tick);
  }
  function renderAt(value) { if (!painter) return; pause(); draw(value, value < seconds); report(true); }
  const ready = (async () => {
    const packet = await loadBirdsongAsset(document.body.dataset.bird);
    // The new portraits have no legacy illustrative sensor labels. Do not add
    // the original-study liveMarks; actual health/activity belongs to the parent.
    if (packet.config.approvedOriginal || packet.config.goldfinchOriginal) throw Error('Original paintings must use their preserved player');
    painter = await createBirdsongPainter(packet);
    draw(0, true); preparingMs = performance.now() - preparedAt;
    loading.hidden = true; post('songsketch:ready');
    if (!embedded) { document.body.classList.add('review'); controls.hidden = false; checks.hidden = false; report(true); }
    return true;
  })();
  ready.catch(() => { loading.textContent = 'This painting could not be prepared. The previous display is kept.'; post('songsketch:error', {code:'painting_unavailable'}); });
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || event.source !== parent || !embedded) return;
    if (event.data?.type === 'songsketch:play') {
      const elapsed = event.data.elapsed_seconds;
      if (typeof elapsed !== 'number' || !Number.isFinite(elapsed) || typeof event.data.event_id !== 'string') return;
      play(event.data.event_id, elapsed).catch(() => {});
    }
  });
  document.addEventListener('visibilitychange', () => {
    cancelAnimationFrame(frame);
    if (!document.hidden && playing) frame = requestAnimationFrame(tick);
  });
  button.addEventListener('click', () => playing ? pause() : play('review', seconds >= duration ? 0 : seconds));
  slider.addEventListener('input', () => renderAt(Number(slider.value)));
  checks.addEventListener('click', event => { const control = event.target.closest('button[data-time]'); if (control) renderAt(Number(control.dataset.time)); });
  window.SongsketchPainting = {
    ready, play, pause, renderAt,
    getState() { return {...painter?.getState(), event_id:eventId, playing, seconds, preparing_ms:preparingMs, review_status:'completed_awaiting_review'}; },
    schedule() { return painter?.schedule() || []; },
    integrity() { return painter?.integrity() || {}; }
  };
})();
