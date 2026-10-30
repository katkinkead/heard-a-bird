"""Keep the shipped recording inventory, credits and actual media in sync."""
import csv
import hashlib
import json
import unittest

from songsketch.config import ROOT


class BirdAudioLibraryTests(unittest.TestCase):
    def test_every_illustrated_species_has_a_credited_local_recording(self):
        branch = ROOT / 'artwork' / 'branch'
        birds = json.loads((branch / 'content.json').read_text())['birds']
        expected = {bird['id'] for bird in json.loads((branch / 'manifest.json').read_text())['birds']}
        self.assertEqual(set(birds), expected)
        with (branch / 'audio' / 'CREDITS.csv').open(newline='') as source:
            credits = {row['file']: row for row in csv.DictReader(source)}
        self.assertEqual(set(credits), {bird + '.mp3' for bird in expected})
        for bird_id, bird in birds.items():
            with self.subTest(bird=bird_id):
                audio = bird['audio']
                self.assertTrue(audio['available'])
                self.assertEqual(audio['url'], '/artwork/branch/audio/' + bird_id + '.mp3')
                media = branch / 'audio' / (bird_id + '.mp3')
                self.assertGreater(media.stat().st_size, 1000)
                self.assertEqual(hashlib.sha256(media.read_bytes()).hexdigest(), audio['sha256'])
                self.assertGreater(audio['duration_seconds'], 0.3)
                self.assertLessEqual(audio['duration_seconds'], 12)
                self.assertTrue(audio['source'].startswith('https://'))
                self.assertTrue(audio['license_url'].startswith('https://'))
                self.assertIn(audio['license'], ['CC BY-SA 3.0', 'CC BY-SA 4.0', 'CC BY 4.0', 'Public domain', 'CC0'])
                self.assertTrue(audio['changes'])
                self.assertNotIn(audio['author'], ['', 'See source'])
                credit = credits[media.name]
                for field in ['author', 'source', 'license', 'license_url', 'changes']:
                    self.assertEqual(credit[field], audio[field])

    def test_taxon_and_nonvocal_exceptions_are_visible_in_the_catalogue(self):
        birds = json.loads((ROOT / 'artwork/branch/content.json').read_text())['birds']
        self.assertIn('subspecies', birds['pied-wagtail']['audio']['note'])
        self.assertIn('drumming', birds['great-spotted-woodpecker']['audio']['note'])
