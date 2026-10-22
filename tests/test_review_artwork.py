"""Completed-review packaging boundaries, without browser/network/paid calls."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artwork"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_importer():
    spec = importlib.util.spec_from_file_location("review_import", ART / "tools/import-review-animations.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReviewPackageTests(unittest.TestCase):
    def test_candidates_do_not_promote_live_or_change_originals(self):
        live = json.loads((ART / "catalogue.json").read_text())
        review = json.loads((ART / "review-catalogue.json").read_text())
        registry = json.loads((ART / "registry.json").read_text())
        original = {b["id"]: b for b in live["birds"]}
        by_id = {b["id"]: b for b in registry["birds"]}
        self.assertEqual({b["id"] for b in review["birds"]}, set(by_id))
        awaiting = []
        for bird in review["birds"]:
            if bird["id"] in original:
                self.assertEqual(bird, original[bird["id"]])
                continue
            awaiting.append(bird)
            self.assertIs(bird["approved"], False)
            self.assertIs(bird["production_eligible"], False)
            self.assertIs(bird["animation_ready"], True)
            self.assertEqual(bird["review_status"], "completed_awaiting_review")
            self.assertIs(by_id[bird["id"]]["animation_ready"], False)
            self.assertEqual(bird["animation_url"], "/artwork/" + by_id[bird["id"]]["review_animation_path"])
        self.assertEqual(registry["completed_review_animation_count"], len(awaiting))
        self.assertEqual(registry["completed_asset_count"], len(review["birds"]))
        self.assertEqual(registry["completed_animation_count"], len(original))

    def test_all_review_dependencies_are_frozen_and_source_runtime_unchanged(self):
        snapshot = json.loads((ART / "animation-review-snapshot.json").read_text())
        source = json.loads((ART / snapshot["source_build_record"]).read_text())
        self.assertIs(snapshot["production_promoted"], False)
        self.assertIs(snapshot["prepared_score_cache_included"], False)
        self.assertEqual(len(snapshot["profiles"]), source["totalBirds"])
        self.assertIn("fragmentation", snapshot["review_context"]["later_feedback"])
        for row in snapshot["files"]:
            path = ART / row["path"]
            self.assertIn(ART.resolve(), path.resolve().parents)
            self.assertFalse(path.is_symlink())
            raw = path.read_bytes()
            self.assertEqual(len(raw), row["bytes"], row["path"])
            self.assertEqual(sha(raw), row["sha256"], row["path"])
        module = load_importer()
        for name in module.RUNTIME:
            self.assertEqual(sha((ART / "animations/review-runtime" / name).read_bytes()), source["runtimeFiles"]["runtime/" + name])
        self.assertFalse((ART / "animations/review-runtime/branch.js").exists())

    def test_profiles_use_exact_local_reference_without_illustrative_live_state(self):
        registry = json.loads((ART / "registry.json").read_text())
        for row in registry["birds"]:
            if not row.get("review_animation_ready"):
                continue
            identity = row["id"]
            packet_text = (ART / "animations/species" / (identity + ".js")).read_text()
            packet = json.loads(packet_text[len("window.BirdsongAssets.receive("):-3])
            profile = json.loads((ART / "animations/species" / (identity + ".json")).read_text())
            self.assertEqual(packet["config"], profile)
            self.assertEqual(packet["source"], "../references/final-art/" + identity + ".png")
            self.assertEqual(sha((ART / row["reference_path"]).read_bytes()), profile["sourceSha256"])
            self.assertNotIn("scoreFile", profile)
            self.assertFalse(profile.get("approvedOriginal") or profile.get("goldfinchOriginal"))
            self.assertNotRegex(packet_text, r"/Users/|/home/|file://|https?://")
            self.assertFalse(any(re.search(r"singing|live ripple", b.get("label", ""), re.I) for b in profile.get("textBoxes", [])))
            page = ART / row["review_animation_path"]
            for ref in re.findall(r'''(?:src|href)=["']([^"']+)["']''', page.read_text()):
                self.assertFalse(ref.startswith(("/", "http", "file:", "data:")))
                self.assertTrue((page.parent / ref).is_file(), ref)


class ReviewImportGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.art = self.root / "artwork"
        self.source = self.root / "authoring"
        self.anim = self.source / "animations"
        self.module = load_importer()
        self.patcher = patch.object(self.module, "ART", self.art)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jS5kAAAAASUVORK5CYII=")
        self.fixture()

    def put(self, root, path, data):
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())

    def fixture(self):
        ids = sorted(self.module.ORIGINALS) + ["great-tit"]
        records, live, proofs, species = [], [], [], []
        runtime = {}
        for name in self.module.RUNTIME:
            data = ("/* frozen " + name + " */").encode()
            self.put(self.anim, "runtime/" + name, data)
            runtime["runtime/" + name] = sha(data)
        for name in ("player.js", "player.css"):
            self.put(self.art, "animations/review-runtime/" + name, b"/* wrapper */")
        for identity in ids:
            self.put(self.art, "references/final-art/" + identity + ".png", self.png)
            record = {"id": identity, "common_name": identity, "scientific_name": identity + " scientific",
                      "final_art_accepted": True, "approval_basis": "fixture acceptance",
                      "reference_path": "references/final-art/" + identity + ".png", "reference_sha256": sha(self.png),
                      "animation_ready": identity in self.module.ORIGINALS}
            records.append(record)
            if identity in self.module.ORIGINALS:
                raw = ("unchanged original " + identity).encode()
                self.put(self.art, "animations/" + identity + ".html", raw)
                live.append({"id": identity, "animation_url": "/artwork/animations/" + identity + ".html", "animation_sha256": sha(raw)})
            profile = {"id": identity, "sourceFile": "/source/development/" + identity + ".png", "sourceSha256": sha(self.png), "scoreKey": "key", "scoreFile": "scores/" + identity + ".js"}
            self.put(self.anim, "species/" + identity + ".json", profile)
            packet = {"config": profile, "source": "data:image/png;base64," + base64.b64encode(self.png).decode()}
            self.put(self.anim, "species/" + identity + ".js", ("window.BirdsongAssets.receive(" + json.dumps(packet) + ");").encode())
            self.put(self.anim, "thumbnails/" + identity + ".webp", b"thumbnail")
            proofs.append({"id": identity, "preparedScoreVerified": True, "finalMarksComplete": True,
                           "durationSeconds": 75, "cachedFinalPixelComparison": {"equivalent": True}, "sourceSha256": sha(self.png), "scoreKey": "key"})
            species.append({"id": identity})
        self.put(self.art, "registry.json", {"birds": records})
        self.put(self.art, "catalogue.json", {"birds": live})
        self.put(self.anim, "catalog.json", {"total": len(ids), "species": species})
        self.put(self.anim, "build-record.json", {"createdAt": "test", "totalBirds": len(ids), "birds": proofs, "runtimeFiles": runtime, "durationSeconds": 75, "defaultFluidity": .78})

    def test_stable_import_reuses_png_and_preserves_live_originals(self):
        before = (self.art / "catalogue.json").read_bytes()
        result = self.module.import_collection(self.source)
        self.assertEqual(result["review_imported"], 1)
        self.assertEqual(result["live_unchanged"], 5)
        self.assertEqual((self.art / "catalogue.json").read_bytes(), before)
        packet = (self.art / "animations/species/great-tit.js").read_text()
        self.assertNotIn("base64", packet)
        self.assertNotIn("/source/development", packet)
        self.assertNotIn("scoreFile", packet)
        review = json.loads((self.art / "review-catalogue.json").read_text())
        self.assertIs(review["birds"][-1]["approved"], False)

    def test_incomplete_source_stops_before_writes(self):
        path = self.anim / "build-record.json"
        obj = json.loads(path.read_text()); obj["birds"][-1]["finalMarksComplete"] = False
        path.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError, "Incomplete painting"):
            self.module.import_collection(self.source)
        self.assertFalse((self.art / "review-catalogue.json").exists())

    def test_mismatched_reference_is_not_replaced(self):
        ref = self.art / "references/final-art/great-tit.png"
        ref.write_bytes(b"different existing portrait")
        with self.assertRaisesRegex(ValueError, "different accepted reference"):
            self.module.import_collection(self.source)
        self.assertEqual(ref.read_bytes(), b"different existing portrait")
        self.assertFalse((self.art / "review-catalogue.json").exists())

    def test_registration_not_matching_completed_score_is_rejected(self):
        path = self.anim / "species/great-tit.json"
        profile = json.loads(path.read_text())
        profile["scoreKey"] = "new-in-progress-score"
        path.write_text(json.dumps(profile))
        with self.assertRaisesRegex(ValueError, "Registration differs from completed score"):
            self.module.import_collection(self.source)
        self.assertFalse((self.art / "review-catalogue.json").exists())

    def test_concurrent_source_change_rejects_mixed_snapshot(self):
        target = (self.anim / "runtime/engine.js").resolve()
        real_read = Path.read_bytes
        changed = []
        def read(path):
            raw = real_read(path)
            if path == target and not changed:
                changed.append(True)
                path.write_bytes(b"new active authoring runtime")
            return raw
        with patch.object(Path, "read_bytes", read):
            with self.assertRaisesRegex(ValueError, "Source changed during snapshot"):
                self.module.import_collection(self.source)
        self.assertFalse((self.art / "review-catalogue.json").exists())

    def test_changed_live_baseline_is_never_overwritten(self):
        original = self.art / "animations/robin.html"
        original.write_bytes(b"local work must survive")
        with self.assertRaisesRegex(ValueError, "Live baseline differs"):
            self.module.import_collection(self.source)
        self.assertEqual(original.read_bytes(), b"local work must survive")


if __name__ == "__main__":
    unittest.main()
