/* Pure local report tests: no browser, network, production data or credentials. */
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const report = require('../static/qa-report.js');
const at = '2026-10-22T12:00:00.000Z';
const status = () => ({simulation:true,version:'0.1.0',runs:[{id:'run-one',scenario:'known-bird',status:'passed',seed:7,
  checks:[{name:'Selected artwork',expected:'robin',actual:'robin',passed:true}],
  manual_checks:[{name:'Watch the painting',status:'not_checked'}]}]});

test('an unverified page cannot create or export an offline snapshot', () => {
  assert.throws(() => report.captureStatus({simulation:false,runs:[]},at));
  assert.throws(() => report.captureStatus({runs:[]},at));
  assert.throws(() => report.offlineReport(null,'note',{}));
  assert.throws(() => report.captureStatus(status(),'invalid date'));
});

test('cached evidence is an immutable copy with an explicit narrow field allowlist', () => {
  const source = status(); source.config={smtp_password:'private-setting'};
  source.runs[0].diagnostics={secret:'private-diagnostic'}; source.runs[0].steps=[{token:'private-step'}];
  const saved = report.captureStatus(source,at);
  source.runs[0].checks[0].actual='changed after capture';
  assert.equal(saved.runs[0].checks[0].actual,'robin');
  for(const key of ['config','diagnostics','steps','private-setting','private-diagnostic','private-step']) assert.ok(!JSON.stringify(saved).includes(key));
  assert.equal(saved.last_successful_status_at,at);
});

test('offline report labels its age, limitations and manual review without creating a new pass', () => {
  const saved=report.captureStatus(status(),at);
  const packet=report.offlineReport(saved,'The pie overlaps the title.',{viewport:{width:390,height:844},visual_quality_verified:false},'2026-10-22T12:05:00.000Z');
  assert.equal(packet.offline_snapshot,true); assert.equal(packet.last_successful_status_at,at);
  assert.equal(saved.version,'0.1.0'); assert.equal(packet.version,'0.1.0');
  assert.equal(packet.manual_visual_notes,'The pie overlaps the title.');
  assert.equal(packet.runs[0].manual_checks[0].status,'not_checked');
  assert.equal(packet.browser_observations.visual_quality_verified,false);
  assert.equal(packet.external_messages_sent,false);
  assert.ok(packet.limitations.some(line=>line.includes('may be absent')));
});

test('common credential patterns and email addresses are removed from notes', () => {
  const privateNotes='token=sample-token-123 password="example password" Authorization: Bearer demoSecret123\n'+
    'sk-proj-FAKEabcdefghijklmnop github_pat_FAKEabcdefghijklmnop\n'+
    'https://exampleuser:samplepassword@host.test/ person@example.test\n'+
    '-----BEGIN PRIVATE KEY-----\nEXAMPLE PRIVATE MATERIAL\n-----END PRIVATE KEY-----';
  const safe=report.sanitizeNotes(privateNotes);
  assert.equal(safe.redacted,true);
  for(const secret of ['sample-token-123','example password','demoSecret123','FAKEabcdefghijklmnop','exampleuser','samplepassword','person@example.test','EXAMPLE PRIVATE MATERIAL']) assert.ok(!safe.text.includes(secret),secret);
});

test('structured secret keys in check evidence are redacted and unknown top-level fields discarded', () => {
  const source=status(); source.runs[0].checks[0].actual={code:401,api_key:'private-value',message:'Bearer sampletoken123'};
  const saved=report.captureStatus(source,at); saved.config={secret:'must-not-export'};
  const packet=report.offlineReport(saved,'',{},at);
  assert.equal(packet.runs[0].checks[0].actual.code,401);
  assert.equal(packet.runs[0].checks[0].actual.api_key,'[REDACTED]');
  assert.ok(!JSON.stringify(packet).includes('private-value')); assert.ok(!JSON.stringify(packet).includes('must-not-export'));
});

test('cached reports remain bounded and preserve failed checks', () => {
  const source=status(); source.runs=Array.from({length:35},()=>source.runs[0]);
  source.runs[0].status='failed'; source.runs[0].checks[0].passed=false;
  const saved=report.captureStatus(source,at);
  assert.equal(saved.runs.length,20); assert.equal(saved.runs[0].checks[0].passed,false);
  const safe=report.sanitizeNotes('a'.repeat(5000)); assert.equal(safe.text.length,4000);
});
