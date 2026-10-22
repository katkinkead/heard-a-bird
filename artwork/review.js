(() => {
  'use strict';
  const el = id => document.getElementById(id), select = el('bird'), frame = el('painting');
  let birds = [], current = null, player = null, loading = false, time = 0, serial = 0;
  function state() {
    if (!player) return;
    const s = player.getState();
    el('play').textContent = s.playing ? 'Pause' : 'Play';
    el('diagnostics').textContent = `Drawing: ${(s.time ?? time).toFixed(1)} / 75 seconds. Marks complete: ${s.completed} / ${s.strokeCount}. ` +
      (typeof s.preparing_ms === 'number' ? `Preparation: ${(s.preparing_ms / 1000).toFixed(2)} seconds; authored marks built locally.` : 'Preserved approved original player.');
  }
  function showTime(seconds) { time = seconds; el('time').value = seconds; el('clock').textContent = `${seconds.toFixed(1)} / 75 s`; state(); }
  function seek(seconds) { if (player) { player.renderAt(seconds); showTime(seconds); } }
  function enabled(value) { for (const id of ['play','compare','time']) el(id).disabled = !value; }
  function choose(id) {
    const bird = birds.find(b => b.id === id); if (!bird) return;
    current = bird; select.value = id; player = null; loading = true; enabled(false); time = 0; serial++;
    el('status').textContent = 'Preparing ' + bird.common_name + '…'; el('diagnostics').textContent = 'Building the local painting marks…';
    el('reference').src = 'references/final-art/' + id + '.png'; el('reference').alt = bird.common_name + ' accepted finished-art reference';
    el('reference-link').href = el('reference').src;
    frame.title = bird.common_name + ' painting animation'; frame.src = bird.animation_url.replace(/^\/artwork\//, '');
    history.replaceState(null, '', '#' + id); showTime(0);
  }
  frame.addEventListener('load', async () => {
    const generation = serial;
    try {
      const p = frame.contentWindow.SongsketchPainting;
      if (!p) throw Error('Painting bridge unavailable');
      await p.ready;
      if (generation !== serial) return;
      player = p; loading = false; enabled(true); seek(0);
      el('status').textContent = current.approved ? 'Approved original · live catalogue' : 'Completed · final clarity review pending';
    } catch (_) {
      if (generation === serial) { el('status').textContent = 'Painting could not load. Keep the accepted reference for comparison.'; loading = false; }
    }
  });
  window.addEventListener('message', event => {
    if (event.source !== frame.contentWindow || event.origin !== location.origin) return;
    if (event.data?.type === 'songsketch:progress' && typeof event.data.seconds === 'number') showTime(event.data.seconds);
  });
  select.addEventListener('change', () => choose(select.value));
  const step = delta => { if (!birds.length) return; const at = birds.findIndex(b => b.id === current?.id); choose(birds[(at + delta + birds.length) % birds.length].id); };
  el('previous').addEventListener('click', () => step(-1)); el('next').addEventListener('click', () => step(1));
  el('play').addEventListener('click', async () => { if (!player) return; if (player.getState().playing) player.pause(); else await player.play('review-' + current.id, time >= 75 ? 0 : time); state(); });
  el('time').addEventListener('input', event => seek(Number(event.target.value)));
  el('checkpoints').addEventListener('click', event => { const b = event.target.closest('button[data-time]'); if (b) seek(Number(b.dataset.time)); });
  el('compare').addEventListener('click', () => { seek(75); el('comparison').classList.add('split'); el('reference-panel').hidden = false; });
  fetch('review-catalogue.json', {cache:'no-store'}).then(r => { if (!r.ok) throw Error('Catalogue unavailable'); return r.json(); }).then(data => {
    birds = data.birds; select.replaceChildren(...birds.map(b => Object.assign(document.createElement('option'), {value:b.id, textContent:b.common_name})));
    const id = decodeURIComponent(location.hash.slice(1)); choose(birds.some(b => b.id === id) ? id : 'great-tit');
  }).catch(() => { el('status').textContent = 'Open this library through the local Songsketch server to review the animations.'; });
})();
