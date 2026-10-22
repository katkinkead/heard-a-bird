"""Isolated real HTTP tests; synthetic data, no providers or hardware."""
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from songsketch.simulation import (COOKIE, SCENARIOS, SimulationApp, SimulationServer,
                                   DisabledJobs, DisabledCommissioning, prepare_directory)
from songsketch import __version__


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.folder=Path(self.temp.name)/"garden"
        self.app=SimulationApp(self.folder)
        self.server=SimulationServer(("127.0.0.1",0),self.app)
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={"poll_interval":.01},daemon=True)
        self.thread.start()
        self.external=[]
        for target in ("smtplib.SMTP","smtplib.SMTP_SSL","songsketch.ai_jobs.call_openai","songsketch.commissioning.CommissioningManager.action","songsketch.github_launcher.open_terminal"):
            p=patch(target,side_effect=AssertionError("External action forbidden in simulation"))
            self.external.append(p); p.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)
        self.app.close()
        for p in self.external: p.stop()
        self.temp.cleanup()

    def request(self,method,path,data=None,authorized=True,headers=None):
        h=dict(headers or {})
        if authorized: h["Authorization"]="Bearer "+self.app.config.secrets["admin_token"]
        body=json.dumps(data) if data is not None else None
        if body: h["Content-Type"]="application/json"
        conn=http.client.HTTPConnection("127.0.0.1",self.app.port,timeout=10)
        try:
            conn.request(method,path,body=body,headers=h)
            response=conn.getresponse(); content=response.read()
            return response.status,dict(response.getheaders()),json.loads(content)
        finally: conn.close()

    def test_every_scenario_exercises_real_http_and_has_evidence(self):
        for definition in SCENARIOS:
            with self.subTest(scenario=definition["id"]):
                status,_,body=self.request("POST","/api/simulation/run",{"scenario":definition["id"],"seed":91})
                self.assertEqual(status,200)
                run=body["run"]
                self.assertEqual(run["status"],"passed",run["checks"])
                self.assertTrue(run["checks"])
                self.assertTrue(all(c["passed"] for c in run["checks"]))
                self.assertFalse(run["hardware_verified"])
                self.assertTrue(all(c["status"]=="not_checked" for c in run["manual_checks"]))
                self.assertEqual(run["diagnostics"]["database_check"]["quick_check"],"ok")
        self.assertEqual(len(self.app.saved_runs()),len(SCENARIOS))
        self.assertFalse(self.app.admin_status()["verification"]["real_pi"])

    def test_scenario_reset_preserves_reports_not_live_counts(self):
        self.app.run_scenario("burst-idle",77)
        self.app.run_scenario("known-bird",77)
        self.assertEqual(self.app.admin_status()["counts"]["detections"],1)
        self.assertEqual(len(self.app.saved_runs()),2)
        self.assertEqual(self.app.state()["current_run"]["scenario"],"known-bird")

    def test_seed_repeats_event_order_and_snapshot_has_real_counts(self):
        first=self.app.run_scenario("burst-idle",99)
        second=self.app.run_scenario("burst-idle",99)
        names=lambda run:[s["event"]["scientific_name"] for s in run["steps"] if "event" in s]
        self.assertEqual(names(first),names(second))
        self.assertEqual(sum(b["count"] for b in second["snapshot"]["birds"]),12)
        self.assertNotEqual(first["steps"][1]["event"]["event_id"],second["steps"][1]["event"]["event_id"])

    def test_no_external_capabilities_and_all_write_paths_denied(self):
        self.assertIsInstance(self.app.jobs,DisabledJobs)
        self.assertIsInstance(self.app.commissioning,DisabledCommissioning)
        self.assertFalse(self.app.thread.is_alive())
        for path in ("/api/admin/jobs","/api/admin/jobs/abc/approve","/api/admin/settings","/api/admin/launch-assistant","/api/admin/setup/probe","/api/admin/setup/install","/api/admin/maintenance","/api/admin/email-retry-confirmed","/api/admin/station-token"):
            with self.subTest(path=path):
                status,_,body=self.request("POST",path,{"action":"retry_email"})
                self.assertEqual(status,403)
                self.assertIn("simulated garden",body["error"])
        with self.assertRaisesRegex(ValueError,"simulated garden"):
            self.app.jobs.requester("anything")
        with self.assertRaisesRegex(ValueError,"simulated garden"):
            self.app.config.update({"openai_api_key":"ignored"})
        self.assertEqual(self.request("GET","/api/admin/export")[0],403)

    def test_capture_is_once_per_species_and_never_sent(self):
        self.app.run_scenario("missing-art")
        self.assertEqual(self.app.maintenance.send_mail(),0)
        outbox=self.app.store.query("SELECT * FROM email_outbox")
        self.assertEqual(len(outbox),1)
        self.assertEqual(outbox[0]["status"],"captured")
        self.assertIsNone(outbox[0]["sent_at"])
        self.assertFalse(self.app.state()["local_inbox"][0]["external_delivery"])

    def test_download_redacts_notes_and_has_expected_actual(self):
        self.app.run_scenario("known-bird",9)
        secret=self.app.config.secrets["station_token"]
        status,headers,body=self.request("POST","/api/simulation/report",{"notes":"token="+secret+" password=do-not-share"})
        self.assertEqual(status,200)
        self.assertIn("attachment",headers["Content-Disposition"])
        self.assertNotIn(secret,json.dumps(body))
        self.assertNotIn("do-not-share",json.dumps(body))
        self.assertEqual(body["runs"][0]["seed"],9)
        self.assertIn("actual",body["runs"][0]["checks"][0])
        self.assertEqual(body["version"],__version__)
        self.assertEqual(body["diagnostics"]["version"],__version__)
        self.assertEqual(body["runs"][0]["snapshot"]["status"]["version"],__version__)
        self.assertTrue((self.folder/"latest-simulation-report.json").exists())
        self.assertEqual((self.folder/"latest-simulation-report.json").stat().st_mode&0o777,0o600)

    def test_auth_origin_cookie_separate_from_production(self):
        self.assertEqual(self.request("GET","/api/simulation/status",authorized=False)[0],401)
        self.assertEqual(self.request("POST","/api/simulation/run",{"scenario":"known-bird"},headers={"Origin":"https://example.com"})[0],401)
        self.assertEqual(self.request("GET","/api/simulation/status",headers={"Host":"external.example"})[0],401)
        _,headers,_=self.request("POST","/api/session",{"token":self.app.config.secrets["admin_token"]},authorized=False)
        cookie=headers["Set-Cookie"].split(";",1)[0]
        self.assertTrue(cookie.startswith(COOKIE+"="))
        self.assertIn("HttpOnly",headers["Set-Cookie"])
        self.assertEqual(self.request("GET","/api/simulation/status",authorized=False,headers={"Cookie":cookie})[0],200)
        self.assertEqual(self.request("GET","/api/simulation/status",authorized=False,headers={"Cookie":cookie.replace(COOKIE,"songsketch_session")})[0],401)
        self.assertEqual(self.request("POST","/api/admin/logout",{},authorized=False,headers={"Cookie":cookie})[0],200)
        self.assertEqual(self.request("GET","/api/simulation/status",authorized=False,headers={"Cookie":cookie})[0],401)

    def test_simulation_marker_required_and_live_folder_protected(self):
        unmarked=Path(self.temp.name)/"unmarked"; unmarked.mkdir(); (unmarked/"history").write_text("keep")
        with self.assertRaisesRegex(ValueError,"unmarked"):
            prepare_directory(unmarked)
        self.assertEqual((unmarked/"history").read_text(),"keep")
        with patch("songsketch.simulation.data_directory",return_value=self.folder):
            with self.assertRaisesRegex(ValueError,"separate"):
                prepare_directory(self.folder)
        alias=Path(self.temp.name)/"alias"; alias.symlink_to(self.folder)
        with self.assertRaises(ValueError): prepare_directory(alias)
        with self.assertRaisesRegex(ValueError,"127.0.0.1"):
            SimulationServer(("0.0.0.0",0),self.app)

    def test_validation_rejects_unknown_seed_or_path_and_saves_no_run(self):
        for data in ({"scenario":"bad"},{"scenario":"known-bird","seed":True},{"scenario":"known-bird","seed":-1},{"scenario":"known-bird","shell":"touch bad"}):
            self.assertEqual(self.request("POST","/api/simulation/run",data)[0],400)
        self.assertEqual(self.request("GET","/api/simulation/report?run_id=../../secrets.json")[0],400)
        self.assertFalse(self.app.saved_runs())

    def test_existing_run_records_survive_app_restart(self):
        run=self.app.run_scenario("known-bird",123)
        self.server.shutdown(); self.server.server_close(); self.thread.join(2); self.app.close()
        self.app=SimulationApp(self.folder)
        self.server=SimulationServer(("127.0.0.1",0),self.app)
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={"poll_interval":.01},daemon=True)
        self.thread.start()
        saved=self.app.saved_runs()[0]
        self.assertEqual(saved["id"],run["id"])
        self.assertEqual(saved["seed"],123)
        self.assertEqual((self.folder/"simulation.json").stat().st_mode&0o777,0o600)

    def test_candidate_preview_is_explicit_and_does_not_rewrite_source(self):
        catalogue=ROOT/"artwork/review-catalogue.json"
        if not catalogue.exists(): self.skipTest("Candidate snapshot not packaged")
        source=catalogue.read_bytes()
        candidate=SimulationApp(Path(self.temp.name)/"candidate",catalogue)
        try:
            self.assertEqual(len(candidate.store.birds),45)
            self.assertEqual(sum(bool(b.get("candidate")) for b in candidate.store.birds),40)
            self.assertTrue(candidate.store.bird("Parus major")["candidate"])
            self.assertIs(candidate.store.bird("Parus major")["source_approved"],False)
            self.assertEqual(len(self.app.store.birds),5)
            self.assertEqual(catalogue.read_bytes(),source)
        finally: candidate.close()


if __name__=="__main__": unittest.main()
