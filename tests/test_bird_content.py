import unittest,tempfile
from datetime import date,datetime,timedelta,timezone
from songsketch.bird_content import decision,baseline,evidence,catalogue
from songsketch.config import Config,ROOT
from songsketch.store import Store,iso
class ContentTests(unittest.TestCase):
 def setUp(self):
  self.today=date(2026,10,23);self.bird={'scientific_name':'Erithacus rubecula'};self.record={'season':{'months':list(range(1,13))},'regional':{'eligible':True}}
  self.history={'day':self.today,'days':{self.today-timedelta(days=i):5 for i in range(1,36)},'observations':{}}
 def test_new_install_has_no_unusual_badge(self):
  self.history['days']={};s=decision(self.bird,self.record,self.history);self.assertFalse(s['unusual']);self.assertTrue(s['rare'])
 def test_infrequent_in_season_with_coverage(self):
  s=decision(self.bird,self.record,self.history);self.assertTrue(s['unusual']);self.assertEqual(s['baseline_days'],35)
 def test_regular_bird_is_not_unusual(self):
  self.history['observations']['erithacus rubecula']={self.today-timedelta(days=i) for i in [1,2,3]};self.assertFalse(decision(self.bird,self.record,self.history)['unusual'])
 def test_out_of_season_retained_without_badge(self):
  self.record['season']['months']=[5,6,7];s=decision(self.bird,self.record,self.history);self.assertFalse(s['unusual']);self.assertFalse(s['in_season'])
 def test_short_coverage_and_different_season_do_not_count(self):
  self.history['days']={self.today-timedelta(days=i):3.99 for i in range(1,36)};self.history['days'].update({date(2026,6,1)+timedelta(days=i):24 for i in range(30)});self.assertEqual(decision(self.bird,self.record,self.history)['baseline_days'],0)
 def test_prior_year_same_season_counts(self):
  self.history['days']={date(2025,10,1)+timedelta(days=i):4 for i in range(30)};self.assertTrue(decision(self.bird,self.record,self.history)['unusual'])
 def test_missing_season_not_guessed(self):
  self.record.pop('season');s=decision(self.bird,self.record,self.history);self.assertIsNone(s['in_season']);self.assertFalse(s['unusual'])
 def test_confirmed_spans_only_and_tests_excluded(self):
  with tempfile.TemporaryDirectory() as folder:
   store=Store(Config(folder),ROOT/'artwork/catalogue.json');now=datetime(2026,10,23,12,tzinfo=timezone.utc)
   with store.tx() as db:
    db.execute('INSERT INTO listening_windows(start_at,last_at,open) VALUES (?,?,1)',(iso(now-timedelta(days=1,hours=4)),iso(now-timedelta(days=1))))
   h=baseline(store,now);self.assertEqual(sum(h['days'].values()),4);s=evidence(store,'day',now);self.assertEqual(s['coverage']['confirmed_hours'],0);self.assertGreater(s['coverage']['unconfirmed_hours'],12);store.close()
 def test_content_complete_and_sources_present(self):
  birds=catalogue()['birds'];self.assertEqual(len(birds),45)
  for b in birds.values():
   self.assertTrue(b['facts'][0]['source'].startswith('https://'));self.assertLess(len(b['facts'][0]['text'].split()),35);self.assertTrue(b['season']['months'])

 def test_pruned_history_cannot_become_false_absence(self):
  with tempfile.TemporaryDirectory() as folder:
   store=Store(Config(folder),ROOT/'artwork/catalogue.json');now=datetime(2026,10,23,12,tzinfo=timezone.utc)
   with store.tx() as db:db.execute('INSERT INTO listening_windows(start_at,last_at,open) VALUES (?,?,0)',(iso(now-timedelta(days=100)),iso(now-timedelta(days=50))))
   store.set_meta('detection_history_floor',iso(now-timedelta(days=30)))
   self.assertEqual(baseline(store,now)['days'],{});store.close()
