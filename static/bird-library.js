(async () => {
  const el = (tag, text, parent) => {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    parent?.append(node);
    return node;
  };
  const link = (label, url, parent) => {
    try {
      const target = new URL(url);
      if (!['https:', 'http:'].includes(target.protocol)) return;
      const anchor = el('a', label, parent);
      anchor.href = target.href;
      anchor.target = '_blank';
      anchor.rel = 'noopener';
      return anchor;
    } catch {}
  };
  try {
    const response = await fetch('/artwork/branch/content.json');
    if (!response.ok) throw Error();
    const content = await response.json();
    const birds = Object.values(content.birds).sort((a, b) => a.name.localeCompare(b.name));
    const ready = birds.filter(bird => bird.audio?.available).length;
    document.getElementById('audio-coverage').textContent = `${ready} of ${birds.length} bird recordings saved locally.`;
    for (const bird of birds) {
      const article = el('article', '', document.getElementById('library'));
      article.id = bird.id || bird.name.toLowerCase().replace(/\s+/g, '-');
      article.dataset.name = bird.name.toLowerCase();
      el('h2', bird.name, article);
      for (const fact of bird.facts || []) {
        el('p', fact.text, article);
        link(`${fact.publisher} · reviewed ${fact.reviewed_at}`, fact.source, article);
      }
      if (bird.regional?.eligible) {
        el('p', bird.regional.explanation, article);
        link(`County evidence · ${bird.regional.evidence_year}`, bird.regional.source, article);
      }
      el('small', bird.season.note, article);
      const recording = bird.audio || {};
      if (recording.source) {
        el('p', `${recording.title} — ${recording.author}`, article);
        link('Original recording', recording.source, article);
        el('span', ' · ', article);
        link(recording.license, recording.license_url, article);
        if (recording.note) el('small', recording.note, article);
      }
      if (recording.available) {
        el('small', recording.changes, article);
        const audio = el('audio', '', article);
        audio.controls = true;
        audio.preload = 'none';
        audio.setAttribute('aria-label', `Listen to ${bird.name}`);
        audio.src = recording.url;
        audio.onplay = () => document.querySelectorAll('audio').forEach(other => {
          if (other !== audio) other.pause();
        });
      } else {
        el('small', recording.source ? 'Recording found; local download pending.' : 'Local recording not yet available.', article);
      }
    }
    document.getElementById('search').oninput = event => {
      document.querySelectorAll('article').forEach(article => {
        article.hidden = !article.dataset.name.includes(event.target.value.trim().toLowerCase());
      });
    };
  } catch {
    document.getElementById('load-error').textContent = 'The local library could not load. Return to the garden and try again.';
  }
})();
