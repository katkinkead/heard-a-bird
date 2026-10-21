"""Evidence boundaries for the read-only setup summary. No network or mutation."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from songsketch.setup_health import build_setup_health

NOW = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
def stamp(seconds=0):
    return (NOW + timedelta(seconds=seconds)).isoformat()
def diagnostics(**changes):
    value = {"generated_at":stamp(), "database_check":{"quick_check":"ok"},
             "station":{"connected":False, "ever_connected":False}, "issues":[], "reports":[]}
    value.update(changes)
    return value
def station(**changes):
    value = {"connected":True, "ever_connected":True, "last_heartbeat":stamp(-10),
             "audio_status":"healthy", "inference_status":"healthy"}
    value.update(changes)
    return value
def component(summary, key):
    return next(c for c in summary["components"] if c["id"] == key)
def issue(identifier, **changes):
    value = {"id":identifier, "resolved":0, "severity":"warning", "message":"Recorded fault", "last_seen":stamp(-50)}
    value.update(changes)
    return value

class SetupHealthTests(unittest.TestCase):
    def build(self, setup=None, evidence=None, **options):
        return build_setup_health(setup or {}, evidence or diagnostics(), now=NOW, **options)

    def test_first_start_is_unknown_not_broken_and_browser_is_never_assumed(self):
        result = self.build()
        self.assertEqual(component(result,"server")["status"],"healthy")
        self.assertEqual(component(result,"garden_pi")["status"],"not_started")
        self.assertEqual(component(result,"display")["status"],"unverified")
        self.assertEqual(result["problems"],[])

    def test_fresh_report_verifies_scoped_capture_recognition_and_delivery(self):
        result = self.build(evidence=diagnostics(station=station()))
        for key in ("garden_pi","microphone","birdnet","delivery"):
            self.assertEqual(component(result,key)["status"],"healthy")
        self.assertIn("real bird",component(result,"delivery")["message"])
        self.assertEqual(component(result,"display")["status"],"unverified")

    def test_stale_future_malformed_and_disconnected_reports_do_not_reuse_health(self):
        for overrides in ({"last_heartbeat":stamp(-151)}, {"last_heartbeat":stamp(90)},
                          {"last_heartbeat":"bad"}, {"connected":False}, {"last_heartbeat":[]},
                          {"last_heartbeat":"2026-10-21T12:00:00"}):
            with self.subTest(overrides=overrides):
                result=self.build(evidence=diagnostics(station=station(**overrides)))
                self.assertNotEqual(component(result,"microphone")["status"],"healthy")
                self.assertNotEqual(component(result,"birdnet")["status"],"healthy")

    def test_connected_audio_fault_is_located_without_blaming_server(self):
        result=self.build(evidence=diagnostics(station=station(audio_status="failed")))
        self.assertEqual(component(result,"microphone")["status"],"attention")
        self.assertEqual(component(result,"birdnet")["status"],"healthy")
        self.assertEqual(component(result,"server")["status"],"healthy")
        self.assertEqual(result["problems"][0]["component"],"microphone")

    def test_fixed_failure_codes_identify_actual_location(self):
        for code, expected in (("authentication_failed","garden_pi"),("sudo_required","garden_pi"),
                               ("host_key_changed","garden_pi"),("ssh_missing","server"),
                               ("capture_missing","microphone"),("server_unreachable","delivery"),
                               ("birdnet_access_required","birdnet")):
            with self.subTest(code=code):
                result=self.build({"job":{"state":"failed","stage":"connect","error":{"code":code,"message":"Failed checkpoint"}}})
                self.assertEqual(result["problems"][0]["component"],expected)
                self.assertTrue(result["problems"][0]["failed_evidence"])

    def test_completed_diagnosis_is_not_installation_and_failed_checks_show(self):
        job={"state":"completed","operation":"diagnose","stage":"diagnostics", "updated_at":stamp(-20),
             "result":{"status":"diagnostic","checks":{"audio":"failed","history_readable":False}}}
        result=self.build({"job":job})
        self.assertEqual(component(result,"garden_pi")["status"],"not_started")
        self.assertEqual({p["component"] for p in result["problems"]},{"microphone","birdnet"})
        self.assertNotIn("saved_software_commissioning",json.dumps(result))

    def test_historical_commissioning_cannot_override_current_failure(self):
        job={"state":"completed","commissioned":True,"last_successful_install":{"at":stamp(-3600)}}
        result=self.build({"job":job},diagnostics(station=station(last_heartbeat=stamp(-500))))
        self.assertEqual(component(result,"garden_pi")["status"],"attention")
        self.assertIn("saved_software_commissioning",json.dumps(result))
        self.assertNotEqual(component(result,"microphone")["status"],"healthy")

    def test_report_component_join_and_unknown_or_resolved_issue(self):
        fingerprint=hashlib.sha256(b"garden:audio").hexdigest()[:24]
        result=self.build(evidence=diagnostics(issues=[issue(fingerprint),issue("unexplained"),issue("resolved",resolved=1)],
                           reports=[{"station_id":"garden","details":{"component":"audio"}}]))
        self.assertEqual([p["component"] for p in result["problems"]],["microphone","system"])
        self.assertEqual(result["problems"][1]["location"],"Not yet isolated")

    def test_recorded_warning_superseded_only_by_newer_healthy_evidence(self):
        old=issue("pi-disconnected")
        self.assertEqual(self.build(evidence=diagnostics(station=station(),issues=[old]))["problems"],[])
        new=issue("pi-disconnected",last_seen=stamp())
        self.assertEqual(len(self.build(evidence=diagnostics(station=station(),issues=[new]))["problems"]),1)
        failed=issue("audio-unavailable")
        result=self.build(evidence=diagnostics(station=station(audio_status="failed"),issues=[failed]))
        self.assertIn("issue-audio-unavailable",{p["id"] for p in result["problems"]})

    def test_supervisor_is_timestamped_evidence_not_a_claim_api_is_down(self):
        result=self.build(evidence=diagnostics(supervisor={"state":"failed","updated_at":stamp(-10)}))
        self.assertEqual(component(result,"server")["status"],"attention")
        self.assertIn("API is responding",result["problems"][0]["message"])
        result=self.build(evidence=diagnostics(supervisor={"state":"failed","updated_at":stamp(-1000)}))
        self.assertEqual(result["problems"],[])
        self.assertEqual(component(result,"server")["evidence"][-1]["status"],"stale")

    def test_credentials_raw_logs_and_location_are_never_forwarded(self):
        secret="private-secret-that-must-not-appear"
        job={"state":"failed","stage":"connect","inputs":{"latitude":50.123456,"longitude":-2.123456},
             "logs":["private logfile"],"error":{"code":"host_unreachable","message":"x"*490+secret}}
        evidence=diagnostics(reports=[{"private":"private report"}])
        original=deepcopy((job,evidence))
        result=self.build({"job":job},evidence,secrets=[secret])
        encoded=json.dumps(result)
        for forbidden in (secret,secret[:10],"50.123456","-2.123456","private logfile","private report"):
            self.assertNotIn(forbidden,encoded)
        self.assertEqual((job,evidence),original)

    def test_malformed_optional_payloads_are_bounded_and_json_safe(self):
        result=self.build({"job":{"state":[],"result":{"checks":{"audio":[]}},"logs":None}},
                          diagnostics(station=None,reports=[None,{"details":{"component":[]}}],
                                      issues=[None,{"id":[],"resolved":0},issue("valid",message={"bad":"type"})]))
        json.dumps(result)
        self.assertTrue(result["problems"][0]["message"])
        self.assertEqual(len(result["components"]),8)

if __name__ == "__main__":
    unittest.main()
