"""Production handlers over real local sockets; no external services."""
from datetime import timedelta
import uuid
import unittest
from unittest.mock import patch
import test_simulation
from songsketch.store import iso, utcnow
from songsketch.capture_exclusion import contains, subtract, status, action

class RecoveryTests(unittest.TestCase):
    setUp=test_simulation.SimulationTests.setUp
    tearDown=test_simulation.SimulationTests.tearDown
    request=test_simulation.SimulationTests.request

    def session(self):
        code,_,data=self.request('GET','/api/display/session',authorized=False,headers={'Sec-Fetch-Site':'same-origin'})
        self.assertEqual(code,200,data)
        return data['token']

    def report(self,token,data=None):
        return self.request('POST','/api/display/reports',data or self.payload(),authorized=False,headers={'Sec-Fetch-Site':'same-origin','X-Display-Token':token})

    def payload(self):
        return {'report_id':str(uuid.uuid4()),'code':'artwork-load','bird':'robin','view':'branch','observed_at':iso()}

    def test_scoped_report_auth_dedup_and_dashboard(self):
        self.assertEqual(self.request('GET','/api/display/session',authorized=False)[0],401)
        self.assertEqual(self.report('bad')[0],401)
        token=self.session();data=self.payload()
        self.assertEqual(self.report(token,data)[0],200)
        self.assertTrue(self.report(token,data)[2]['duplicate'])
        self.assertEqual(len(self.app.store.query('SELECT * FROM reports')),1)
        self.assertEqual(self.app.store.query('SELECT occurrences FROM issues')[0]['occurrences'],1)
        self.assertEqual(self.request('GET','/api/admin/status',authorized=False,headers={'X-Display-Token':token})[0],401)
        self.assertEqual(self.request('POST','/api/display/reports',data,authorized=False,headers={'Origin':'https://other.example','Sec-Fetch-Site':'same-origin','X-Display-Token':token})[0],401)
        self.assertIn('display could not load',self.app.admin_status()['issues'][0]['message'])

    def test_fixed_fields_expiry_limits_and_no_secret_upload(self):
        token=self.session()
        for changes in ({'message':'never-upload-this'},{'bird':'not-a-bird'},{'code':'arbitrary'},{'observed_at':iso(utcnow()-timedelta(days=8))}):
            data={**self.payload(),**changes};self.assertEqual(self.report(token,data)[0],400)
        for _ in range(20):self.assertEqual(self.report(token)[0],200)
        self.assertEqual(self.report(token)[0],429)
        self.assertNotIn('never-upload-this',str(self.app.store.diagnostics()))
        self.app.display_reports.tokens[token]=(0,0)
        self.assertEqual(self.report(token)[0],401)

    def event(self,name='Erithacus rubecula',when=None):
        return self.app.local_ingest('detections',{'station_id':'garden','event_id':str(uuid.uuid4()),'scientific_name':name,'confidence':.99,'observed_at':iso(when or utcnow())})

    def test_capture_window_delayed_reports_do_not_count_mail_or_paint(self):
        self.assertEqual(self.request('POST','/api/admin/capture-test',{'action':'start'},authorized=False)[0],401)
        start=utcnow()-timedelta(seconds=20)
        with patch('songsketch.capture_exclusion.utcnow',return_value=start):
            self.assertEqual(self.request('POST','/api/admin/capture-test',{'action':'start'})[0],200)
        when=start+timedelta(seconds=5)
        self.assertTrue(self.event(when=when)['commissioning_capture'])
        self.assertEqual(self.request('POST','/api/admin/capture-test',{'action':'stop'})[0],200)
        self.assertTrue(self.event('Testus unknown',when)['test'],'buffered test remains excluded after stop')
        self.assertEqual(self.app.store.summary('all'),[])
        self.assertEqual(self.app.store.query('SELECT * FROM email_outbox'),[])
        self.assertEqual(self.app.store.query('SELECT * FROM queue'),[])
        self.assertIsNone(self.app.store.meta('test_override'))
        self.assertFalse(self.event()['test'])
        self.assertEqual(sum(b['count'] for b in self.app.store.summary('all')),1)
        # Metadata is on disk; reopening SQLite does not depend on an in-memory timer.
        import sqlite3,json
        with sqlite3.connect(self.app.store.path) as db:
            windows=json.loads(db.execute("SELECT value FROM meta WHERE key='commissioning_capture_windows'").fetchone()[0])
        self.assertEqual(len(windows),1)
        self.assertTrue(contains(self.app.store,when))

    def test_capture_expiry_and_coverage_subtraction(self):
        start=utcnow()-timedelta(minutes=11)
        with patch('songsketch.capture_exclusion.utcnow',return_value=start):action(self.app.store,{'action':'start'})
        self.assertFalse(status(self.app.store)['active'])
        self.assertTrue(self.event(when=start+timedelta(minutes=1))['test'])
        spans=subtract(self.app.store,[(start-timedelta(minutes=1),start+timedelta(minutes=12))])
        self.assertEqual(sum((b-a).total_seconds() for a,b in spans),180)
        self.assertFalse(self.event()['test'])

if __name__=='__main__':unittest.main()
