"""Optional AI and mail are always mocked; tests never make paid/external calls."""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import smtplib
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from songsketch.server import App
from songsketch.store import iso

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


class JobTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = App(self.temp.name,background=False)
        self.calls = []
        self.app.jobs.requester = self.provider

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def provider(self,endpoint,payload,key):
        self.calls.append((endpoint,payload,key))
        if endpoint == "images/edits":
            return {"data":[{"b64_json":base64.b64encode(PNG).decode()}],"usage":{"mock":True}}
        return {"output":[{"content":[{"type":"output_text","text":"# Reviewable proposal\nNo changes applied."}]}],"usage":{"mock":True}}

    def configure(self):
        self.app.config.update({"openai_api_key":"unit-test-provider-key-not-real"})

    def start(self, kind="style", **extra):
        return self.app.jobs.start({"kind":kind,"confirm_paid":True,**extra},background=False)

    def unknown_bird(self,event="new-1",confidence=.95,test=False):
        return self.app.store.ingest({"event_id":event,"station_id":"garden","scientific_name":"Passer domesticus","common_name":"House sparrow","confidence":confidence,"observed_at":iso(),"test":test})


class OptionalAITests(JobTest):
    def test_credentials_and_explicit_confirmation_are_required(self):
        with self.assertRaisesRegex(ValueError,"API key"): self.start()
        self.configure()
        self.assertEqual(self.calls,[])
        self.assertEqual(self.app.jobs.list(),[])
        with self.assertRaisesRegex(ValueError,"Confirm"):
            self.app.jobs.start({"kind":"style"},background=False)
        self.assertEqual(self.calls,[])

    def test_normal_detection_and_recovery_never_invoke_ai(self):
        self.configure()
        self.unknown_bird()
        self.app.store.tick()
        self.app.maintenance.check()
        self.app.maintenance.backup()
        self.assertEqual(self.calls,[])
        self.assertEqual(self.app.jobs.list(),[])

    def test_style_draft_keeps_existing_guide_and_catalogue_unchanged(self):
        paths = [ROOT/"artwork/catalogue.json",ROOT/"artwork/painting-system/references/final-art-system.md",ROOT/"artwork/painting-system/assets/benchmarks/robin-approved-75s.html"]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        self.configure()
        job = self.start("style",direction="Explore spacious composition")
        self.assertEqual(job["status"],"review")
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.calls[0][0],"responses")
        self.assertFalse(self.calls[0][1]["store"])
        self.assertEqual(self.calls[0][1]["max_output_tokens"],3500)
        self.assertEqual(before,[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        with self.assertRaisesRegex(ValueError,"proposal"):
            self.app.jobs.approve(job["id"])

    def test_artwork_draft_requires_approval_and_does_not_invent_animation(self):
        self.configure()
        self.unknown_bird()
        job = self.start("artwork",scientific_name="Passer domesticus",common_name="House sparrow")
        self.assertEqual(job["status"],"review")
        self.assertIsNone(self.app.store.bird("Passer domesticus"))
        self.assertEqual(len(self.calls),1)
        self.assertEqual(self.calls[0][0],"images/edits")
        self.assertEqual(len(self.calls[0][1]["images"]),3)
        self.assertTrue((Path(self.temp.name)/"drafts"/job["id"]/"artwork.png").exists())
        self.app.jobs.approve(job["id"])
        bird = self.app.store.bird("Passer domesticus")
        self.assertTrue(bird["artwork_approved"])
        self.assertFalse(bird["animation_ready"])
        self.assertNotIn("animation_url",bird)
        self.assertEqual(self.app.store.query("SELECT resolved FROM missing_art")[0]["resolved"],1)
        self.assertEqual(self.app.store.query("SELECT status FROM email_outbox")[0]["status"],"resolved")

    def test_existing_approved_species_cannot_be_overwritten(self):
        self.configure()
        original = dict(self.app.store.bird("Erithacus rubecula"))
        job = self.start("artwork",scientific_name="Erithacus rubecula",common_name="Robin")
        with self.assertRaisesRegex(ValueError,"protected"):
            self.app.jobs.approve(job["id"])
        self.assertEqual(self.app.store.bird("Erithacus rubecula"),original)

    def test_animation_action_is_a_plan_not_a_claimed_new_renderer(self):
        self.configure()
        job = self.start("animation",scientific_name="Erithacus rubecula")
        self.assertEqual(job["status"],"review")
        self.assertIn("proposal",job["result"]["review"])
        self.assertEqual(job["result"]["preview_url"],"/artwork/animations/robin.html")
        with self.assertRaises(ValueError): self.app.jobs.approve(job["id"])

    def test_provider_failure_has_no_automatic_paid_retry_and_redacts_key(self):
        self.configure()
        secret = self.app.config.secrets["openai_api_key"]
        requester = Mock(side_effect=RuntimeError("Provider failed with "+secret))
        self.app.jobs.requester = requester
        job = self.start("diagnose")
        self.assertEqual(job["status"],"failed")
        self.assertEqual(requester.call_count,1)
        self.assertNotIn(secret,json.dumps(job))
        self.assertIn("[redacted]",job["message"])

    def test_job_cap_and_key_removal_stop_further_calls(self):
        self.configure()
        self.app.config.update({"ai_daily_job_limit":1})
        self.start()
        with self.assertRaisesRegex(ValueError,"24-hour"):
            self.start()
        self.assertEqual(len(self.calls),1)
        self.app.config.update({"remove_ai_key":True})
        with self.assertRaisesRegex(ValueError,"API key"):
            self.start()

    def test_interrupted_paid_job_is_not_automatically_retried_after_restart(self):
        now = iso()
        with self.app.store.tx() as db:
            db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)",("a"*32,"style","","running","Working",now,now,"{}",None))
        self.app.close()
        self.app = App(self.temp.name,background=False)
        self.app.jobs.requester = self.provider
        job = self.app.jobs.list()[0]
        self.assertEqual(job["status"],"failed")
        self.assertIn("Interrupted",job["message"])
        self.assertEqual(self.calls,[])


class MissingArtworkMailTests(JobTest):
    def configure_email(self):
        self.app.config.update({"smtp_host":"smtp.invalid.test","smtp_port":587,"smtp_from":"garden@example.test","notification_email":"friend@example.test","smtp_tls":True})

    def test_one_notice_per_species_real_new_events_update_history(self):
        self.configure_email()
        self.unknown_bird("one")
        self.unknown_bird("one")
        self.unknown_bird("two")
        self.unknown_bird("not-qualified",confidence=.2)
        self.unknown_bird("test",test=True)
        self.assertEqual(self.app.store.summary()[0]["count"],2)
        self.assertEqual(len(self.app.store.query("SELECT * FROM email_outbox")),1)
        with patch("songsketch.maintenance.smtplib.SMTP") as smtp_class:
            smtp = smtp_class.return_value.__enter__.return_value
            self.assertEqual(self.app.maintenance.send_mail(),1)
            self.assertEqual(self.app.maintenance.send_mail(),0)
            smtp.starttls.assert_called_once()
            smtp.send_message.assert_called_once()
            message = smtp.send_message.call_args.args[0]
            self.assertEqual(message["To"],"friend@example.test")
            self.assertIn("House sparrow",message.get_body().get_content())
        self.assertEqual(self.app.store.query("SELECT status FROM email_outbox")[0]["status"],"sent")

    def test_failed_email_is_retained_and_retry_does_not_affect_history(self):
        self.configure_email()
        self.unknown_bird()
        with patch("songsketch.maintenance.smtplib.SMTP",side_effect=ConnectionRefusedError("mail unavailable")):
            self.assertEqual(self.app.maintenance.send_mail(),0)
        row = self.app.store.query("SELECT * FROM email_outbox")[0]
        self.assertEqual(row["status"],"failed")
        self.assertEqual(row["attempts"],1)
        self.assertEqual(self.app.store.summary()[0]["count"],1)
        self.app.maintenance.retry_email()
        with patch("songsketch.maintenance.smtplib.SMTP") as smtp_class:
            self.assertEqual(self.app.maintenance.send_mail(),1)
        self.assertEqual(self.app.store.query("SELECT status FROM email_outbox")[0]["status"],"sent")

    def test_uncertain_smtp_delivery_needs_confirmation_before_retry(self):
        self.configure_email()
        self.unknown_bird()
        with patch("songsketch.maintenance.smtplib.SMTP") as smtp_class:
            smtp_class.return_value.__enter__.return_value.send_message.side_effect = smtplib.SMTPServerDisconnected("Lost connection after DATA")
            self.app.maintenance.send_mail()
        self.assertEqual(self.app.store.query("SELECT status FROM email_outbox")[0]["status"],"uncertain")
        self.app.maintenance.retry_email()
        self.assertEqual(self.app.store.query("SELECT status FROM email_outbox")[0]["status"],"uncertain")


if __name__ == "__main__": unittest.main()
