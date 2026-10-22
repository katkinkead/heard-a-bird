/* Simulator-only field notes. No provider, SSH or external delivery calls. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  let state = null, selected = null, busy = false, connected = false, polling = false;
  let viewedRun = null, previewOpened = false, connectionMessage = false;
  let reportSnapshot = null, reporting = false;
  const reports = globalThis.SongsketchQAReport;
  const noteKey = 'songsketch-simulation-notes:' + location.origin;

  function message(text) {
    $('global-notice').textContent = text || '';
    $('global-notice').hidden = !text;
  }

  function simple(value) {
    if (typeof value === 'string') return value;
    if (value === undefined || value === null) return 'Not recorded';
    return JSON.stringify(value);
  }

  function localTime(value) {
    const date = new Date(value);
    return Number.isFinite(date.getTime()) ? date.toLocaleString('en-GB', {dateStyle:'medium',timeStyle:'short'}) : '';
  }

  async function api(path, data, timeoutMs=60000) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(path, {method:data === undefined ? 'GET' : 'POST', credentials:'same-origin',
        cache:'no-store', headers:data === undefined ? {} : {'Content-Type':'application/json'},
        body:data === undefined ? undefined : JSON.stringify(data), signal:controller.signal});
      const value = await response.json().catch(() => ({}));
      if (!response.ok) {
        const error = new Error(response.status === 401 ? 'This simulator session is locked. Reopen “Open simulated garden.command” to get a fresh local opening link.' : response.status === 404 ? 'This address is not running the simulator. Open “Open simulated garden.command” in your Songsketch project folder; it opens a separate test garden at 127.0.0.1:8766.' : (value.error || value.message || 'The simulator could not finish that action.'));
        error.status = response.status; throw error;
      }
      return value;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('The simulator did not respond in time. Check its Terminal window; do not assume this scenario finished.');
      throw error;
    } finally { clearTimeout(timeout); }
  }

  function unavailable(text) {
    connected = false; $('connection-dot').classList.remove('connected');
    $('connection-status').textContent = 'Simulator unavailable';
    $('workspace').hidden = true; $('report-section').hidden = true;
    $('simulator-links').hidden = true;
    $('candidate-notice').hidden = true;
    $('unavailable').hidden = false; $('unavailable-message').textContent = text;
    $('session-label').textContent = 'No real garden has been changed';
    reportButtons();
  }

  function reportButtons() {
    $('download-report').disabled = busy || reporting || !reportSnapshot;
    $('copy-report').disabled = busy || reporting || !reportSnapshot;
  }

  function renderScenarios() {
    const scenarios = state.scenarios || [];
    const list = $('scenarios');
    const existing = new Map([...list.children].map(button => [button.dataset.scenario, button]));
    const ids = new Set(scenarios.map(scenario => scenario.id));
    existing.forEach((button, id) => { if (!ids.has(id)) button.remove(); });
    scenarios.forEach((scenario, index) => {
      const previous = (state.runs || []).find(run => run.scenario === scenario.id);
      const statusText = previous ? (previous.status === 'passed' ? 'Last checks passed · visual review open' : 'Last run needs attention') : 'Ready to try';
      if (existing.has(scenario.id)) {
        const button = existing.get(scenario.id); button.disabled = busy || !connected;
        button.setAttribute('aria-pressed', String(selected === scenario.id));
        button.querySelector('small').textContent = statusText;
        return;
      }
      const button = document.createElement('button'); button.type = 'button'; button.className = 'scenario-option';
      button.dataset.scenario = scenario.id; button.setAttribute('aria-controls','selected-title');
      button.setAttribute('aria-pressed', String(selected === scenario.id)); button.disabled = busy || !connected;
      const number = document.createElement('span'); number.className = 'scenario-number'; number.textContent = String(index + 1).padStart(2,'0');
      const text = document.createElement('span'); const title = document.createElement('span'); title.className = 'scenario-name'; title.textContent = scenario.title;
      const subtitle = document.createElement('small'); subtitle.textContent = statusText;
      text.append(title, subtitle);
      const arrow = document.createElement('span'); arrow.className = 'scenario-arrow'; arrow.setAttribute('aria-hidden','true'); arrow.textContent = '↗';
      button.append(number, text, arrow);
      button.addEventListener('click', () => { selected = scenario.id; renderSelection(); renderScenarios(); });
      list.append(button);
    });
  }

  function renderSelection() {
    const scenario = state?.scenarios?.find(item => item.id === selected);
    $('selected-title').textContent = scenario?.title || 'Choose a scenario';
    $('selected-description').textContent = scenario?.description || '';
    const expected = scenario?.expected;
    $('selected-expected').textContent = Array.isArray(expected) ? expected.join(' ') : simple(expected);
    $('run-scenario').disabled = !scenario || busy || !connected;
    $('run-scenario').textContent = busy ? 'Trying this moment…' : 'Try this moment →';
  }

  function addCheck(check, manual=false) {
    const status = manual ? 'pending' : (check.passed === true ? 'pass' : check.passed === false ? 'fail' : 'pending');
    const row = document.createElement('li'); row.className = status;
    const icon = document.createElement('span'); icon.className = 'check-icon'; icon.setAttribute('aria-hidden','true'); icon.textContent = status === 'pass' ? '✓' : status === 'fail' ? '×' : '○';
    const title = document.createElement('span'); title.className = 'check-title';
    title.textContent = (manual ? 'Visual review · ' : '') + (check.name || 'Recorded check');
    const expectation = document.createElement('p'); expectation.className = 'check-description';
    expectation.textContent = manual ? 'Needs your eye. Automated checks do not confirm this; add your observations to the note below.' : 'Expected: ' + simple(check.expected);
    row.append(icon, title, expectation);
    if (!manual) {
      const actual = document.createElement('p'); actual.className = 'check-description';
      actual.textContent = (status === 'pass' ? 'Passed — ' : status === 'fail' ? 'Failed — ' : 'Pending — ') + 'observed: ' + simple(check.actual);
      row.append(actual);
    }
    $('checks').append(row);
  }

  function renderResults() {
    const runs = state.runs || [];
    const run = (viewedRun && runs.find(item => item.id === viewedRun)) || state.current_run || runs[0];
    $('checks').replaceChildren();
    if (!run || typeof run !== 'object') return;
    const scenario = state.scenarios.find(item => item.id === run.scenario);
    const checks = Array.isArray(run.checks) ? run.checks : [];
    const passed = checks.filter(check => check.passed === true).length;
    const failed = checks.filter(check => check.passed === false).length;
    const pending = checks.length - passed - failed;
    const badge = $('result-badge'); badge.className = 'badge ' + (failed || run.status === 'failed' ? 'fail' : pending || !checks.length ? 'pending' : 'pass');
    badge.textContent = failed || run.status === 'failed' ? 'Needs attention' : pending || !checks.length ? 'Checks pending' : 'Checks passed';
    $('result-summary').textContent = `${scenario?.title || run.scenario}: ${passed} of ${checks.length} automated checks passed.${failed ? ` ${failed} need attention.` : ''} Visual review is separate.`;
    checks.forEach(check => addCheck(check));
    const manual = Array.isArray(run.manual_checks) && run.manual_checks.length ? run.manual_checks : [{name:'Painting, symbols and layout'}];
    manual.forEach(check => addCheck(check, true));
    $('technical-details').hidden = false; $('evidence-json').textContent = JSON.stringify(run, null, 2);
    $('result-time').textContent = [localTime(run.finished_at || run.started_at), run.seed !== undefined ? 'Repeatable seed: ' + run.seed : ''].filter(Boolean).join(' · ');
    const history = $('run-history'); history.replaceChildren(); history.hidden = runs.length < 2;
    if (runs.length > 1) {
      const label = document.createElement('p'); label.className = 'small-label'; label.textContent = 'Earlier moments'; history.append(label);
      runs.slice(0,8).forEach(item => {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'history-button';
        button.setAttribute('aria-pressed', String(item.id === run.id));
        const title = state.scenarios.find(scenario => scenario.id === item.scenario)?.title || item.scenario;
        button.textContent = (item.status === 'passed' ? '✓ ' : '× ') + title;
        button.addEventListener('click', () => { viewedRun = item.id; renderResults(); }); history.append(button);
      });
    }
  }

  function render() {
    if (!state || !connected) return;
    $('workspace').hidden = false; $('report-section').hidden = false; $('unavailable').hidden = true;
    $('simulator-links').hidden = false;
    $('candidate-notice').hidden = state.candidate_artwork !== true;
    $('connection-dot').classList.add('connected'); $('connection-status').textContent = 'Practice garden connected';
    $('session-label').textContent = `${state.runs?.length || 0} scenario runs · isolated data`;
    if (!selected || !state.scenarios.some(item => item.id === selected)) selected = state.scenarios[0]?.id || null;
    renderSelection(); renderScenarios(); renderResults();
    const inbox = Array.isArray(state.local_inbox) ? state.local_inbox : [];
    $('local-inbox').hidden = !inbox.length; $('inbox-messages').replaceChildren();
    inbox.slice(-5).reverse().forEach(item => {
      const row = document.createElement('li'); const subject = document.createElement('strong');
      subject.textContent = item.subject || 'A visitor needs a portrait';
      const description = document.createElement('span'); description.textContent = 'Local capture only' + (localTime(item.captured_at) ? ' · ' + localTime(item.captured_at) : '');
      row.append(subject, description); $('inbox-messages').append(row);
    });
    reportButtons();
    if (!previewOpened) { $('painting-preview').src = '/'; previewOpened = true; $('preview-placeholder').hidden = true; }
  }

  async function refresh(initial=false) {
    if (polling || busy || document.hidden && !initial) return;
    polling = true;
    try {
      const next = await api('/api/simulation/status');
      if (next.simulation !== true || !Array.isArray(next.scenarios)) throw new Error('This address is not an isolated Songsketch simulator. Open “Open simulated garden.command” from the project folder.');
      reportSnapshot = reports.captureStatus(next);
      state = next; connected = true; render();
      if (connectionMessage) { message(''); connectionMessage = false; }
    } catch (error) {
      if (!state) unavailable(error.message);
      else {
        connected = false; $('connection-dot').classList.remove('connected'); $('connection-status').textContent = 'Simulator connection lost';
        connectionMessage = true;
        message('The simulator is not responding. The last recorded results are still shown, and you can download an offline report. ' + error.message);
        $('session-label').textContent = 'Last response: ' + localTime(reportSnapshot?.last_successful_status_at);
        $('report-status').textContent = 'Offline snapshot available from ' + localTime(reportSnapshot?.last_successful_status_at) + '. Actions after that response may be absent.';
        renderSelection(); renderScenarios(); reportButtons();
      }
    } finally { polling = false; }
  }

  async function runScenario() {
    if (busy || !connected || !selected) return;
    busy = true; viewedRun = null; render(); message('');
    $('run-status').textContent = 'Recording what the system does…';
    try {
      await api('/api/simulation/run', {scenario:selected});
      $('run-status').textContent = 'Scenario recorded. Watch the canvas and review the checks.';
    } catch (error) { message(error.message); $('run-status').textContent = 'This action was not confirmed. Check the recorded evidence before retrying.'; }
    finally { busy = false; await refresh(true); render(); }
  }

  async function makeReport(copy=false) {
    if (busy || reporting || !reportSnapshot) return;
    reporting = true; reportButtons();
    try {
      const notes = $('visual-notes').value;
      const safeNotes = reports.sanitizeNotes(notes);
      const browser = {viewport:{width:innerWidth,height:innerHeight},
        device_pixel_ratio:devicePixelRatio, reduced_motion:matchMedia('(prefers-reduced-motion: reduce)').matches,
        visual_quality_verified:false};
      let packet;
      if (connected) {
        try {
          const report = await api('/api/simulation/report', {notes:safeNotes.text}, 8000);
          if (report.simulation !== true) throw new Error('The report was not confirmed as simulated.');
          packet = {...report,offline_snapshot:false,last_successful_status_at:reportSnapshot.last_successful_status_at,
            notes_redacted:safeNotes.redacted,browser_observations:browser};
        } catch (_) { packet = reports.offlineReport(reportSnapshot,notes,browser); }
      } else packet = reports.offlineReport(reportSnapshot,notes,browser);
      const text = JSON.stringify(packet, null, 2);
      const description = packet.offline_snapshot ? 'Offline snapshot from ' + localTime(packet.last_successful_status_at) + '; newer actions may be absent.' : 'Report includes the recorded checks and your visual notes.';
      const privacy = packet.notes_redacted ? ' Common private patterns were removed. Review before sharing.' : ' Review your notes before sharing.';
      if (copy) {
        if (!navigator.clipboard?.writeText) throw new Error('Clipboard access is unavailable. Use Download report instead.');
        await navigator.clipboard.writeText(text); $('report-status').textContent = 'Copied. ' + description + privacy;
      } else {
        const url = URL.createObjectURL(new Blob([text], {type:'application/json'}));
        const link = document.createElement('a'); link.href = url; link.download = 'songsketch-simulation-' + new Date().toISOString().replace(/[:.]/g,'-') + '.json';
        document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 2000);
        $('report-status').textContent = 'Downloaded. ' + description + privacy;
      }
    } catch (error) { $('report-status').textContent = error.name === 'NotAllowedError' ? 'Your browser blocked copying. Use Download report instead.' : error.message; }
    finally { reporting = false; reportButtons(); }
  }

  $('run-scenario').addEventListener('click', runScenario);
  $('retry-connection').addEventListener('click', () => refresh(true));
  $('download-report').addEventListener('click', () => makeReport(false));
  $('copy-report').addEventListener('click', () => makeReport(true));
  $('visual-notes').addEventListener('input', () => {
    try { sessionStorage.setItem(noteKey, $('visual-notes').value); } catch (_) { /* Notes remain in the form. */ }
    $('report-status').textContent = 'Note kept in this tab. Download or copy a report when you are ready.';
  });
  try { $('visual-notes').value = sessionStorage.getItem(noteKey) || ''; } catch (_) { /* Storage is optional. */ }

  async function start() {
    if (location.protocol === 'file:') {
      unavailable('Open “Open simulated garden.command” in the Songsketch project folder, then use the local address it opens. A saved HTML file cannot run the simulator.');
      $('retry-connection').hidden = true;
      document.querySelector('.wordmark').href = 'qa.html';
      document.querySelector('footer a').href = '../guide/index.html';
      $('animation-gallery-link').href = '../artwork/review.html';
      return;
    }
    const fragment = new URLSearchParams(location.hash.slice(1)); const ticket = fragment.get('ticket');
    if (ticket) {
      history.replaceState(null, '', location.pathname + location.search);
      try { await api('/api/setup/session', {ticket}); }
      catch (error) { unavailable(error.message); return; }
    }
    await refresh(true);
    setInterval(() => refresh(), 4000);
  }
  start();
})();
