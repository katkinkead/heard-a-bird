import unittest
import test_simulation
class BranchHTTPTests(unittest.TestCase):
 setUp=test_simulation.SimulationTests.setUp
 tearDown=test_simulation.SimulationTests.tearDown
 request=test_simulation.SimulationTests.request
 def act(self,action,id='robin',**kw):
  status,_,v=self.request('POST','/api/simulation/branch',{'action':action,'id':id,**kw});self.assertEqual(status,200,v);return v['state']
 def test_station_delivery_retries_and_bouts(self):
  self.act('reset');s=self.act('send');self.assertEqual(s['observations'],1);self.assertEqual(self.act('retry')['observations'],1);s=self.act('repeat');self.assertEqual((s['observations'],s['bouts']),(2,2));self.assertEqual(self.act('send',confidence=.1)['observations'],2)
 def test_concurrent_species_and_full_collection(self):
  self.act('reset');s=self.act('chorus');self.assertEqual(s['species'],5);s=self.act('all');self.assertEqual(len(self.app.store.query('SELECT DISTINCT scientific_name FROM detections')),45);self.assertTrue(all(b['art_ready'] for b in s['birds']))
 def test_faults_recovery_and_freshness(self):
  self.act('reset');self.act('send');s=self.act('microphone');self.assertTrue(s['station']['connected']);self.assertFalse(s['birds'][0]['live']);self.assertEqual(s['station']['listening'],'unavailable');s=self.act('disconnect');self.assertFalse(s['station']['connected']);s=self.act('connect');self.assertTrue(s['birds'][0]['live'])
 def test_missing_art_is_local_only(self):
  self.act('reset');s=self.act('unknown');self.assertFalse(s['birds'][0]['art_ready']);mail=self.app.store.meta('simulation_mail');self.assertEqual(len(mail),1);self.assertFalse(mail[0]['external_delivery']);self.act('unknown');self.assertEqual(len(self.app.store.meta('simulation_mail')),1)
 def test_auth_validation_and_periods(self):
  self.assertEqual(self.request('POST','/api/simulation/branch',{'action':'reset'},authorized=False)[0],401)
  self.assertEqual(self.request('POST','/api/simulation/branch',{'action':'reset'},headers={'Origin':'https://example.com'})[0],401)
  self.assertEqual(self.request('GET','/api/branch/state?period=year',authorized=False)[0],400)
  for p in ['day','week','month']:self.assertEqual(self.request('GET','/api/branch/state?period='+p,authorized=False)[0],200)
 def test_reset_changes_display_generation(self):
  a=self.act('reset')['generation'];self.act('send');s=self.act('reset');self.assertNotEqual(a,s['generation']);self.assertEqual(s['species'],0)

 def test_automatic_flow_uses_ingress_and_stops(self):
  from songsketch.branch_lab import advance_flow
  from songsketch.store import timestamp
  from datetime import timedelta
  self.act('reset');s=self.act('flow-start');self.assertTrue(s['rehearsal_flow']['running'])
  start=timestamp(s['rehearsal_flow']['started_at'])
  advance_flow(self.app,start);self.assertEqual(len(self.app.store.query('SELECT * FROM detections')),1)
  advance_flow(self.app,start+timedelta(seconds=19));self.assertEqual(len(self.app.store.query('SELECT * FROM detections')),1)
  self.act('flow-stop');advance_flow(self.app,start+timedelta(seconds=20));self.assertEqual(len(self.app.store.query('SELECT * FROM detections')),1)

 def test_evidence_requires_admin_and_matches_public_counts(self):
  self.act('reset');self.act('send');self.assertEqual(self.request('GET','/api/admin/branch-evidence',authorized=False)[0],401)
  status,_,data=self.request('GET','/api/admin/branch-evidence');self.assertEqual(status,200);self.assertEqual(data['bouts'],1);self.assertEqual(data['library']['facts'],45);self.assertIn('confirmed_hours',data['coverage']);self.assertFalse(data['birds'][0]['assessment']['unusual'])
 def test_local_recording_is_served_as_audio(self):
  import http.client
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
  c.request('GET','/artwork/branch/audio/robin.mp3');r=c.getresponse();self.assertEqual(r.status,200);self.assertEqual(r.getheader('Content-Type'),'audio/mpeg');self.assertGreater(len(r.read()),1000);c.close()
