"""Final-art availability is separate from playable animation; no external calls."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from songsketch.config import Config
from songsketch.store import Store, iso


def detected(event='sparrow', scientific='Passer domesticus', common='House Sparrow', **extra):
    return dict(event_id=event,station_id='garden',scientific_name=scientific,common_name=common,
                confidence=.95,observed_at=iso(),**extra)


class ReferenceArtTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
        self.catalogue=self.root/'catalogue.json';self.catalogue.write_text(json.dumps({'birds':[]}))
        self.image=self.root/'references/final-art/sparrow.png';self.image.parent.mkdir(parents=True)
        self.image.write_bytes(b'fixture-approved-final-art')
        self.entry={'id':'house-sparrow','common_name':'House sparrow','scientific_name':'Passer domesticus',
                    'aliases':['House Sparrow','Passer domesticus_House Sparrow','Oldus sparrowus'],
                    'final_art_accepted':True,'final_art_status':'approved',
                    'reference_path':'references/final-art/sparrow.png',
                    'reference_sha256':hashlib.sha256(self.image.read_bytes()).hexdigest(),
                    'animation_ready':True,'animation_path':'unvalidated.html'}
        self.registry=self.root/'registry.json';self.write_registry()
        self.store=Store(Config(self.root/'data'),self.catalogue,reference_registry=self.registry)

    def write_registry(self):
        self.registry.write_text(json.dumps({'schema_version':1,'birds':[self.entry]}))

    def tearDown(self):self.store.close();self.tmp.cleanup()

    def test_known_final_art_records_detection_without_mail_or_playback(self):
        current={'artwork_id':'old-approved-bird','started_at':iso(),'event_id':'existing'}
        self.store.set_meta('current',current)
        self.store.ingest(detected())
        self.store.ingest(detected('reference-test', test=True))
        self.store.tick()
        row=self.store.summary('all')[0]
        self.assertTrue(row['has_artwork']);self.assertTrue(row['final_art_available'])
        self.assertFalse(row['has_animation']);self.assertFalse(row['animation_ready'])
        self.assertEqual(self.store.query('SELECT * FROM email_outbox'),[])
        self.assertEqual(self.store.query('SELECT * FROM missing_art'),[])
        self.assertEqual(self.store.query('SELECT * FROM queue'),[])
        self.assertEqual(self.store.meta('current'),current)
        self.assertEqual(self.store.birds,[])

    def test_scientific_and_birdnet_label_aliases_resolve_to_same_species(self):
        for n,alias in enumerate(('Oldus sparrowus','Passer domesticus_House Sparrow','Passer domesticus')):
            self.store.ingest(detected(str(n),alias,common='unknown common'))
        self.assertEqual([(r['scientific_name'],r['count']) for r in self.store.summary('all')],[('Passer domesticus',3)])
        self.assertFalse(self.store.query('SELECT * FROM email_outbox'))

    def test_unknown_species_still_gets_one_durable_notice(self):
        for event in ('unknown-one','unknown-one','unknown-two'):
            self.store.ingest(detected(event,'Unknownus fixture','Unknown fixture bird'))
        self.store.ingest(detected('unknown-test','Unknownus fixture','Unknown fixture bird',test=True))
        notices=self.store.query('SELECT * FROM email_outbox')
        self.assertEqual(len(notices),1);self.assertEqual(notices[0]['status'],'pending')
        self.assertEqual(self.store.summary('all')[0]['count'],2)
        self.assertFalse(self.store.summary('all')[0]['has_artwork'])

    def test_reference_registry_does_not_leak_into_fixture_catalogue(self):
        isolated=Store(Config(self.root/'isolated'),self.catalogue)
        try:
            self.assertIsNone(isolated.bird('Passer domesticus'))
            isolated.ingest(detected())
            self.assertEqual(len(isolated.query('SELECT * FROM email_outbox')),1)
        finally:isolated.close()

    def test_import_resolves_only_unsent_matching_notices(self):
        self.store.reference_registry_path=None;self.store.reload_catalogue()
        self.store.ingest(detected())
        self.store.ingest(detected('unknown','Unknownus fixture','Unknown'))
        self.store.reference_registry_path=self.registry
        for status,expected in [('pending','resolved'),('failed','resolved'),('sent','sent'),('uncertain','uncertain')]:
            with self.subTest(status=status):
                with self.store.tx() as db:
                    db.execute("UPDATE email_outbox SET status=? WHERE species='Passer domesticus'",(status,))
                self.store.reload_catalogue()
                rows={r['species']:r['status'] for r in self.store.query('SELECT species,status FROM email_outbox')}
                self.assertEqual(rows['Passer domesticus'],expected)
                self.assertEqual(rows['Unknownus fixture'],'pending')
        self.assertEqual(self.store.query("SELECT resolved FROM missing_art WHERE scientific_name='Passer domesticus'")[0]['resolved'],1)

    def test_rejected_art_missing_hash_or_changed_image_never_claims_available(self):
        self.entry['final_art_accepted']=False;self.write_registry();self.store.reload_catalogue()
        self.assertIsNone(self.store.bird('Passer domesticus'))
        self.entry['final_art_accepted']=True;self.entry['reference_sha256']='0'*64;self.write_registry()
        with self.assertRaisesRegex(ValueError,'approved snapshot'):self.store.reload_catalogue()
        self.entry['reference_sha256']=hashlib.sha256(self.image.read_bytes()).hexdigest()
        self.entry['reference_path']='../outside.png';self.write_registry()
        with self.assertRaisesRegex(ValueError,'image path'):self.store.reload_catalogue()

    def test_packaged_catalogue_imports_registry_but_readiness_stays_five(self):
        packaged=Store(Config(self.root/'packaged'),ROOT/'artwork/catalogue.json')
        try:
            self.assertEqual(len(packaged.reference_birds),45)
            self.assertEqual(sum(bool(b.get('animation_ready')) for b in packaged.birds),5)
            self.assertTrue(packaged.bird('Erithacus rubecula')['animation_ready'])
            self.assertFalse(packaged.bird('Passer domesticus')['animation_ready'])
        finally:packaged.close()

if __name__=='__main__':unittest.main()
