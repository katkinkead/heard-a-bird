/* Limited offline evidence, captured only from a verified simulator response. */
(() => {
  'use strict';
  function redactText(value) {
    return String(value).slice(0,12000)
      .replace(/-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?(?:-----END [^-]*PRIVATE KEY-----|$)/g,'[REDACTED PRIVATE KEY]')
      .replace(/\bBearer\s+[A-Za-z0-9._~+\/-]+={0,2}/gi,'Bearer [REDACTED]')
      .replace(/\b(?:sk-(?:proj-)?|gh[pousr]_|github_pat_)[A-Za-z0-9_-]{10,}\b/g,'[REDACTED TOKEN]')
      .replace(/((?:api[_ -]?key|password|passwd|token|secret|authorization)\s*[:=]\s*)(?:"[^"\n]*"|'[^'\n]*'|[^\s,;}]+)/gi,'$1[REDACTED]')
      .replace(/([a-z][a-z0-9+.-]*:\/\/)[^\s/@]+:[^\s/@]+@/gi,'$1[REDACTED]@')
      .replace(/\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi,'[REDACTED EMAIL]');
  }
  function clean(value, depth=0) {
    if (depth > 6) return '[TRUNCATED]';
    if (typeof value === 'string') return redactText(value);
    if (value === null || typeof value === 'boolean') return value;
    if (typeof value === 'number') return Number.isFinite(value) ? value : null;
    if (Array.isArray(value)) return value.slice(0,100).map(item => clean(item,depth+1));
    if (value && typeof value === 'object') {
      const result = {};
      Object.keys(value).slice(0,50).forEach(key => {
        if (/^(?:__proto__|prototype|constructor)$/.test(key)) return;
        result[key] = /(?:password|passwd|secret|token|api[_-]?key|authorization|cookie)/i.test(key) ? '[REDACTED]' : clean(value[key],depth+1);
      });
      return result;
    }
    return null;
  }
  function pick(value, keys) {
    const result = {};
    keys.forEach(key => { if (value && Object.prototype.hasOwnProperty.call(value,key)) result[key] = clean(value[key]); });
    return result;
  }
  function captureStatus(status, capturedAt=new Date().toISOString()) {
    if (status?.simulation !== true || !Array.isArray(status.runs) || !Number.isFinite(Date.parse(capturedAt))) throw new Error('A verified simulator response is required for an offline report.');
    // Exclude config, diagnostics, steps and arbitrary state fields. Never cache
    // tokens, a full server response, or a production installation for export.
    const runs = status.runs.slice(0,20).map(run => ({
      ...pick(run,['id','scenario','seed','status','started_at','finished_at']),
      checks:(Array.isArray(run.checks) ? run.checks : []).slice(0,100).map(check => pick(check,['name','expected','actual','passed'])),
      manual_checks:(Array.isArray(run.manual_checks) ? run.manual_checks : []).slice(0,30).map(check => pick(check,['name','status']))
    }));
    const version = typeof status.version === 'string' ? redactText(status.version.slice(0,100)) : 'unknown';
    return {simulation:true,version,last_successful_status_at:capturedAt,runs};
  }
  function sanitizeNotes(value) {
    const original = typeof value === 'string' ? value.slice(0,4000) : '';
    const text = redactText(original);
    return {text,redacted:text !== original};
  }
  function offlineReport(snapshot, notes, browser, generatedAt=new Date().toISOString()) {
    if (snapshot?.simulation !== true || !Array.isArray(snapshot.runs) || !Number.isFinite(Date.parse(snapshot.last_successful_status_at))) throw new Error('No verified simulator snapshot is available yet.');
    // Reapply the allowlist rather than trust an arbitrary replacement object.
    const saved = captureStatus(snapshot,snapshot.last_successful_status_at);
    const safeNotes = sanitizeNotes(notes);
    return {application:'Songsketch',version:saved.version,simulation:true,offline_snapshot:true,generated_at:generatedAt,
      last_successful_status_at:saved.last_successful_status_at,runs:saved.runs,
      manual_visual_notes:safeNotes.text,manual_visual_review:'User notes only; not an automatic pass.',
      notes_redacted:safeNotes.redacted,browser_observations:pick(browser,['viewport','device_pixel_ratio','reduced_motion','visual_quality_verified']),
      limitations:['The simulator was unavailable or its report request was not confirmed. This is the last verified browser snapshot, not a fresh server report.',
        'Only the latest cached run checks are included. An action after the last successful status response may be absent. Private configuration and server diagnostics are excluded.',
        'Common credential patterns and email addresses are removed; review free-text notes before sharing. No automated filter can identify every private detail.',
        'Synthetic checks do not verify a real Pi, microphone, network, power supply or artistic quality.'],
      external_messages_sent:false};
  }
  const api = Object.freeze({captureStatus,sanitizeNotes,offlineReport});
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else globalThis.SongsketchQAReport = api;
})();
