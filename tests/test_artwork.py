"""Offline checks for the shipped, portable five-bird painting package."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artwork"


class ArtworkPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = json.loads((ART / "catalogue.json").read_text())

    def test_catalogue_has_five_prepared_birds_with_separate_approval(self):
        birds = self.catalogue["birds"]
        self.assertEqual({b["id"] for b in birds}, {"robin", "goldfinch", "blue-tit", "blackbird", "wren"})
        self.assertEqual(len({b["scientific_name"] for b in birds}), 5)
        for bird in birds:
            with self.subTest(bird=bird["id"]):
                self.assertTrue(bird["approved"])
                self.assertTrue(bird["artwork_approved"])
                self.assertTrue(bird["animation_ready"])
                self.assertEqual(bird["duration_seconds"], 75)
                self.assertIn(bird["scientific_name"], bird["aliases"])
                for key in ("image_url", "animation_url"):
                    url = urlsplit(bird[key])
                    self.assertFalse(url.scheme or url.netloc or url.query)
                    target = (ROOT / url.path.lstrip("/")).resolve()
                    self.assertIn(ART.resolve(), target.parents)
                    self.assertTrue(target.is_file(), target)
                page = ROOT / bird["animation_url"].lstrip("/")
                self.assertEqual(hashlib.sha256(page.read_bytes()).hexdigest(), bird["animation_sha256"])

    def test_frozen_sources_and_rebuild_are_exact(self):
        spec = importlib.util.spec_from_file_location("package_artwork", ROOT / "scripts/package-artwork.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        manifest = json.loads((ART / "source-manifest.json").read_text())
        for name, metadata in manifest.items():
            digest = hashlib.sha256((ART / "source" / name).read_bytes()).hexdigest()
            self.assertEqual(digest, metadata["sha256"])
            self.assertEqual(digest, module.SOURCES[name])
        for bird in self.catalogue["birds"]:
            expected = module.standalone((ART / bird["source_file"]).read_text(), bird["id"])
            self.assertEqual((ROOT / bird["animation_url"].lstrip("/")).read_text(), expected)

    def test_player_pages_are_self_contained_and_live_marks_are_disabled(self):
        for bird in self.catalogue["birds"]:
            text = (ROOT / bird["animation_url"].lstrip("/")).read_text()
            with self.subTest(bird=bird["id"]):
                self.assertTrue(text.startswith("<!doctype html>"))
                self.assertNotRegex(text, r"/Users/|/home/|\.codex/visualizations")
                refs = re.findall(r'''(?:src|href)=["']([^"']+)["']''', text)
                self.assertFalse([r for r in refs if not r.startswith(("data:", "#"))])
                self.assertIn("strokes=strokes.filter(s=>!['Singing now'", text)
                self.assertLess(text.index("strokes=strokes.filter(s=>!['Singing now'"), text.index("for(const s of strokes)resample(s);"))
                self.assertIn("event.origin !== location.origin || event.source !== parent", text)

    def test_thumbnails_are_full_canvas_pngs(self):
        for bird in self.catalogue["birds"]:
            data = (ROOT / bird["image_url"].lstrip("/")).read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", data[16:24]), (1000, 750))

    def test_style_guide_references_are_packaged(self):
        text = (ART / "style-guide.html").read_text()
        for reference in re.findall(r'''(?:src|href)=["']([^"']+)["']''', text):
            if reference.startswith(("#", "https:", "data:")):
                continue
            self.assertTrue((ART / reference.split("#")[0]).is_file(), reference)

    def test_browser_validation_covers_all_birds(self):
        report = json.loads((ART / "validation.json").read_text())
        self.assertEqual(report["errors"], [])
        self.assertEqual({b["id"] for b in report["birds"]}, {b["id"] for b in self.catalogue["birds"]})
        for bird in report["birds"]:
            self.assertEqual(bird["annotations"]["bakedLiveMarks"], 0)
            self.assertEqual(bird["invalidTimes"], 0)
            final = bird["completedPlayback"]
            self.assertEqual(final["time"], 75)
            self.assertFalse(final["playing"])
            self.assertEqual(final["completed"], final["strokeCount"])

    def test_display_validation_and_final_fidelity(self):
        report = json.loads((ART / "display-validation.json").read_text())
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["disconnected"], "Pi disconnected")
        self.assertEqual(report["listeningUnavailable"], "Listening unavailable")
        self.assertEqual(report["test"], "Test painting")
        self.assertEqual(report["offline"], "Display offline")
        self.assertEqual(report["keptFrame"], 1)
        for viewport in report["responsive"]:
            self.assertEqual(viewport["width"], viewport["scrollWidth"])
        fidelity = json.loads((ART / "fidelity-validation.json").read_text())
        self.assertEqual(len(fidelity["birds"]), 5)
        for bird in fidelity["birds"]:
            self.assertLess(bird["mean_rgb_difference_0_to_255"], 1)


if __name__ == "__main__":
    unittest.main()
