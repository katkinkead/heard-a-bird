"""Local tests for the staging gate; no live catalogue is touched."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("sync_fork", Path(__file__).with_name("sync-fork.py"))
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.source, self.art = base / "source", base / "artwork"
        self.source.mkdir(); self.art.mkdir()
        (self.art / "registry.json").write_text(json.dumps({"birds": [{"id": "house-sparrow", "animation_ready": False}, {"id": "robin", "animation_ready": True}]}))
        (self.art / "catalogue.json").write_bytes(b"unchanged live catalogue")
        self.patch = patch.object(sync, "ART", self.art); self.patch.start()
        data = b"<html>test fixture, not a real bird animation</html>"
        (self.source / "portrait.html").write_bytes(data)
        self.manifest = {"schema": sync.SCHEMA, "status": "complete", "approval": {"accepted": True, "evidence": "Local test fixture approval"}, "validation": {"complete": True, "evidence": "Local test fixture verification"}, "birds": [{"id": "house-sparrow", "duration_seconds": 75}], "files": [{"path": "portrait.html", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}]}

    def tearDown(self):
        self.patch.stop(); self.tmp.cleanup()

    def run_stage(self):
        (self.source / "handoff.json").write_text(json.dumps(self.manifest))
        return sync.stage_animations(self.source, "handoff.json")

    def test_valid_handoff_stages_exact_bytes_and_is_idempotent_without_promotion(self):
        result = self.run_stage()
        self.assertFalse(result["promoted"])
        target = self.art / result["staged_path"]
        self.assertEqual((target / "files/portrait.html").read_bytes(), (self.source / "portrait.html").read_bytes())
        self.assertEqual((target / "handoff-manifest.json").read_bytes(), (self.source / "handoff.json").read_bytes())
        self.assertTrue(self.run_stage()["already_staged"])
        self.assertEqual((self.art / "catalogue.json").read_bytes(), b"unchanged live catalogue")

    def test_in_progress_or_missing_evidence_is_not_staged(self):
        for field in ("status", "validation", "approval"):
            with self.subTest(field=field):
                old = self.manifest[field]
                self.manifest[field] = "in_progress" if field == "status" else {}
                with self.assertRaises(ValueError): self.run_stage()
                self.manifest[field] = old
        self.assertFalse((self.art / "pending-animations").exists())

    def test_missing_or_partial_file_is_rejected(self):
        (self.source / "portrait.html").write_text("half written")
        with self.assertRaisesRegex(ValueError, "incomplete or changed"): self.run_stage()
        self.assertFalse((self.art / "pending-animations").exists())

    def test_path_traversal_and_symlinks_are_rejected(self):
        self.manifest["files"][0]["path"] = "../portrait.html"
        with self.assertRaisesRegex(ValueError, "escapes"): self.run_stage()
        self.manifest["files"][0]["path"] = "alias.html"
        (self.source / "alias.html").symlink_to(self.source / "portrait.html")
        with self.assertRaisesRegex(ValueError, "Symlinked"): self.run_stage()

    def test_original_completed_birds_cannot_be_replaced(self):
        self.manifest["birds"][0]["id"] = "robin"
        with self.assertRaisesRegex(ValueError, "already-completed"): self.run_stage()

    def test_manifest_change_during_validation_leaves_no_stage(self):
        (self.source / "handoff.json").write_text(json.dumps(self.manifest))
        original = Path.read_bytes
        calls = []
        def read(path):
            raw = original(path)
            if path == self.source / "handoff.json":
                calls.append(True)
                if len(calls) > 1: return raw + b" "
            return raw
        with patch.object(Path, "read_bytes", read):
            with self.assertRaisesRegex(ValueError, "Manifest changed"): sync.stage_animations(self.source, "handoff.json")
        self.assertFalse((self.art / "pending-animations").exists())

    def test_changed_staged_file_cannot_pass_idempotency_check(self):
        result = self.run_stage()
        (self.art / result["staged_path"] / "files/portrait.html").write_text("changed")
        with self.assertRaisesRegex(ValueError, "staging directory is incomplete or changed"): self.run_stage()

    def test_malformed_evidence_or_file_records_are_rejected(self):
        self.manifest["approval"] = []
        with self.assertRaises(ValueError): self.run_stage()
        self.manifest["approval"] = {"accepted": True, "evidence": "test"}
        self.manifest["files"] = [None]
        with self.assertRaises(ValueError): self.run_stage()


if __name__ == "__main__":
    unittest.main()
