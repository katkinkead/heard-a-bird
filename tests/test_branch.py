import tempfile, unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from songsketch.config import Config, ROOT
from songsketch.store import Store, iso
from songsketch.branch import snapshot, boundaries
class BranchTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.config=Config(self.temp.name);self.store=Store(self.config,ROOT/'artwork/catalogue.json');self.now=datetime(2026,10,22,12,tzinfo=timezone.utc)
 def tearDown(self): self.store.close();self.temp.cleanup()
 def event(self,n,seconds=0,confidence=.95,test=False,species='Erithacus rubecula'):
  with patch('songsketch.store.utcnow',return_value=self.now):return self.store.ingest({'event_id':str(n),'station_id':'garden','scientific_name':species,'confidence':confidence,'observed_at':iso(self.now+timedelta(seconds=seconds)),'test':test})
 def health(self,seconds=0,audio='healthy'):
  with patch('songsketch.store.utcnow',return_value=self.now+timedelta(seconds=seconds)):self.store.heartbeat({'station_id':'garden','audio_status':audio,'inference_status':'healthy'})
 def state(self,period='day',now=None):
  now=now or self.now
  with patch('songsketch.store.utcnow',return_value=now):return snapshot(self.store,period,now)
 def test_duplicates_continuous_and_filtered(self):
  self.health(-80);self.health();self.event(1,-40);self.event(1,-40);self.event(2,-20);self.event(3,confidence=.1);self.event(4,test=True)
  s=self.state();self.assertEqual((s['species'],s['bouts'],s['observations']),(1,1,2));self.assertTrue(s['birds'][0]['live'])
 def test_healthy_quiet_gap_separates_bouts(self):
  for t in [-400,-300,-200,-100,0]:self.health(t)
  self.event(1,-350);self.event(2,-340);self.event(3,-10);s=self.state();self.assertEqual(s['bouts'],2);self.assertFalse(s['count_uncertain'])
 def test_outage_is_not_proven_silence(self):
  self.health(-400);self.health(-300,audio='failed');self.health();self.event(1,-350);self.event(2,-10);s=self.state();self.assertEqual(s['bouts'],1);self.assertTrue(s['count_uncertain'])
 def test_buffered_history_never_live(self):
  self.health();self.event(1,-3600);s=self.state();self.assertEqual(s['bouts'],1);self.assertFalse(s['birds'][0]['live'])
 def test_fault_suppresses_live(self):
  self.health(audio='failed');self.event(1);self.assertFalse(self.state()['birds'][0]['live'])
 def test_retry_and_restart_stable(self):
  self.event(1);expected=self.state()['birds'];self.store.close();self.store=Store(self.config,ROOT/'artwork/catalogue.json');self.event(1);self.assertEqual(self.state()['birds'],expected)
 def test_first_heard_order_not_count(self):
  self.event(1,-60,species='Troglodytes troglodytes');self.event(2,-50);self.event(3,-20);self.assertEqual([b['id'] for b in self.state()['birds']],['wren','robin'])
 def test_periods_and_dst(self):
  now=datetime(2026,10,25,12,tzinfo=timezone.utc);start,_=boundaries('day',now,'Europe/London');self.assertEqual(start.utcoffset(),timedelta(hours=1));self.assertEqual((now-start.astimezone(timezone.utc)).total_seconds(),13*3600)
  for period,day in [('day',22),('week',19),('month',1)]:self.assertEqual(boundaries(period,self.now,'Europe/London')[0].day,day)
  with self.assertRaises(ValueError):self.state('year')
 def test_earlier_period_history(self):
  self.event(1,-86400*2);self.event(2);self.assertEqual(self.state()['observations'],1);self.assertEqual(self.state('week')['observations'],2)
 def test_unknown_art_is_retained(self):
  self.event(1,species='Songsketch qa_species');b=self.state()['birds'][0];self.assertIsNone(b['id']);self.assertFalse(b['art_ready'])
 def test_out_of_order_recalculates_without_duplicate(self):
  self.health(-500);self.health(-400);self.health(-300);self.health(-200);self.health(-100);self.health();self.event(1,-10);self.event(2,-350);self.event(3,-250);self.assertEqual(self.state()['bouts'],2)
