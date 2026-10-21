"""Power configuration tests use temporary files; never touch a Pi or boot files."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location("pi_power", Path(__file__).resolve().parents[1] / "scripts/pi-production-power.py")
p = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(p)


def healthy():
    return {"pi5": True, "usb_high_limit_active": 0, "throttle": p.throttle_flags("throttled=0x0"),
            "device_tree_power": {"usb_over_current_detected": 0}}


class ProductionPowerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name).resolve()
        self.config = self.root / "config.txt"; self.config.write_text("# keep cooling settings\ndtparam=fan_temp0=50000\n[pi4]\narm_boost=1\n")

    def tearDown(self): self.tmp.cleanup()

    def test_preserves_existing_content_and_explicit_pi5_scope(self):
        before = self.config.read_bytes(); after = p.proposed_config(before)
        self.assertTrue(after.startswith(before)); self.assertIn(b"[all]\n[pi5]\nusb_max_current_enable=1\n[all]", after)
        self.assertEqual(after, p.proposed_config(after))

    def test_conflicting_or_included_configs_are_preserved_for_review(self):
        for value in (b"include usercfg.txt\n", b"[pi5]\nusb_max_current_enable=0\n", b"usb_max_current_enable=1\n", p.BLOCK.replace("=1", "=0").encode(), (p.BLOCK * 2).encode()):
            with self.assertRaises(p.PowerError): p.proposed_config(value)

    def test_model_supply_load_and_live_evidence_required(self):
        report = p.assess(healthy(), True, 900, 4300)
        self.assertTrue(report["ready_to_change"]); self.assertTrue(report["override_needed_for_declared_load"])
        for report in (p.assess(healthy()), p.assess(healthy(), True, 1700, 4300), p.assess(healthy(), True, 900, 5100),
                       p.assess(dict(healthy(), pi5=False), True, 900, 4300),
                       p.assess(dict(healthy(), usb_high_limit_active=None), True, 900, 4300),
                       p.assess(dict(healthy(), throttle=p.throttle_flags("throttled=0x50000")), True, 900, 4300)):
            self.assertFalse(report["ready_to_change"]); self.assertTrue(report["next_actions"])

    def test_small_microphone_load_does_not_need_blanket_override(self):
        self.assertFalse(p.assess(healthy(), True, 150, 3500)["override_needed_for_declared_load"])
        self.assertTrue(p.assess(healthy(), True, 500, 4000, usb_boot=True)["override_needed_for_declared_load"])

    def test_telemetry_parses_bits_and_never_claims_to_measure_total_load(self):
        model = self.root / "model"; model.write_bytes(b"Raspberry Pi 5 Model B Rev 1.0\x00")
        folder = self.root / "power"; folder.mkdir()
        (folder / "max_current").write_bytes((3000).to_bytes(4, "big"))
        (folder / "usb_max_current_enable").write_bytes((0).to_bytes(4, "big"))
        outputs = {"get_throttled": "throttled=0x50001", "get_config": "usb_max_current_enable=0",
                   "measure_temp": "temp=54.2'C", "pmic_read_adc": "EXT5V_V volt(5.11000000V)"}
        calls = []
        def runner(args): calls.append(args); return outputs[args[1]]
        result = p.inspect(model, folder, runner)
        self.assertTrue(result["pi5"]); self.assertEqual(result["input_voltage_v"], 5.11)
        self.assertEqual(result["device_tree_power"]["max_current"], 3000)
        self.assertTrue(result["throttle"]["undervoltage_now"]); self.assertTrue(result["throttle"]["throttling_occurred"])
        self.assertFalse(result["hardware_load_verified"]); self.assertFalse(result["total_current_measured"])
        self.assertTrue(all(args[0] == "/usr/bin/vcgencmd" for args in calls))

    def test_backup_atomic_write_and_second_run_is_noop(self):
        before, mode = p.read_config(self.config); after = p.proposed_config(before)
        backup = p.write_with_backup(self.config, before, after, mode)
        self.assertEqual(Path(backup).read_bytes(), before); self.assertEqual(self.config.read_bytes(), after)
        self.assertIsNone(p.write_with_backup(self.config, after, p.proposed_config(after), mode))
        self.assertEqual(len(list(self.root.glob("*.bak"))), 1)

    def test_concurrent_edits_and_symlinks_never_overwritten(self):
        before, mode = p.read_config(self.config); self.config.write_text("new user change\n")
        with self.assertRaises(p.PowerError): p.write_with_backup(self.config, before, p.proposed_config(before), mode)
        self.assertEqual(self.config.read_text(), "new user change\n"); self.assertFalse(list(self.root.glob("*.bak")))
        link = self.root / "link"; link.symlink_to(self.config)
        with self.assertRaises(p.PowerError): p.read_config(link)

    def test_plan_and_diagnose_have_no_writes_or_service_commands(self):
        before = self.config.read_bytes()
        with mock.patch.object(p, "CONFIG", self.config), mock.patch.object(p, "inspect", return_value=healthy()), mock.patch.object(p, "write_with_backup") as writer, contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(p.main(["--plan"]), 0)
            report = json.loads(out.getvalue()); self.assertEqual(report["status"], "plan"); self.assertFalse(report["ready_to_change"])
            self.assertEqual(p.main(["--diagnose"]), 0); writer.assert_not_called()
        self.assertEqual(self.config.read_bytes(), before); self.assertFalse(list(self.root.glob("*.bak")))


if __name__ == "__main__": unittest.main()
