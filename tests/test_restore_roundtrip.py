import importlib.util,json,tempfile,unittest,zipfile,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from songsketch.config import Config,ROOT
from songsketch.store import Store,iso
from songsketch.locking import RunLock
spec=importlib.util.spec_from_file_location('restore_helper',ROOT/'scripts/restore.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
class RestoreTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.source=self.root/'source';self.target=self.root/'target';cfg=Config(self.source);cfg.update({'site_name':'Restored Garden'});store=Store(cfg,ROOT/'artwork/catalogue.json');store.ingest({'station_id':'garden','event_id':'e1','scientific_name':'Erithacus rubecula','confidence':.97,'observed_at':iso()});store.close();self.archive=self.root/'garden.zip'
  with zipfile.ZipFile(self.archive,'w') as z:
   for name in ['config.json','songsketch.sqlite3']:z.write(self.source/name,name)
   z.writestr('approved-artwork.json',json.dumps({'birds':[]}));z.writestr('approved/qa.png',b'qa-art')
  self.cfg=Config(self.target);self.cfg.update({'site_name':'Original Garden'});self.old=(self.target/'config.json').read_bytes();self.secrets=(self.target/'secrets.json').read_bytes()
 def tearDown(self):self.tmp.cleanup()
 def test_cli_roundtrip_and_restart(self):
  result=subprocess.run([sys.executable,str(ROOT/'scripts/restore.py'),str(self.archive),'--data-dir',str(self.target)],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
  store=Store(Config(self.target),ROOT/'artwork/catalogue.json');self.assertEqual(store.query('SELECT event_id FROM detections')[0]['event_id'],'e1');self.assertEqual(store.config.values['site_name'],'Restored Garden');self.assertEqual((self.target/'approved/qa.png').read_bytes(),b'qa-art');store.close();self.assertEqual((self.target/'secrets.json').read_bytes(),self.secrets);self.assertEqual(next(self.target.glob('before-restore-*')) .joinpath('config.json').read_bytes(),self.old)
 def test_running_target_is_protected(self):
  lock=RunLock(self.target)
  try:
   with self.assertRaises(RuntimeError):helper.restore(self.archive,self.target)
  finally:lock.close()
  self.assertEqual((self.target/'config.json').read_bytes(),self.old)
 def test_invalid_archives_leave_target_untouched(self):
  for name in ['../outside','secrets.json','/absolute']:
   bad=self.root/'bad.zip'
   with zipfile.ZipFile(bad,'w') as z:z.writestr(name,'bad')
   with self.assertRaises(ValueError):helper.restore(bad,self.target)
   self.assertEqual((self.target/'config.json').read_bytes(),self.old)
 def test_interrupted_copy_restores_original(self):
  original=helper.shutil.move
  def fail(src,dest):
   if str(dest)==str(self.target/'approved-artwork.json'):raise OSError('Injected failure')
   return original(src,dest)
  with patch.object(helper.shutil,'move',side_effect=fail):
   with self.assertRaises(OSError):helper.restore(self.archive,self.target)
  self.assertEqual((self.target/'config.json').read_bytes(),self.old);self.assertFalse((self.target/'songsketch.sqlite3').exists());self.assertEqual((self.target/'secrets.json').read_bytes(),self.secrets)
