"""Local setup security, handoff and preservation checks; no SSH or real install."""
import importlib.util
import json
from pathlib import Path
import tempfile
import os
import signal
import socket
import subprocess
import sys
import time
import unittest
from unittest.mock import patch, Mock
import threading
import test_server as fixtures
from songsketch.server import Server
from songsketch.config import Config
from songsketch.setup_client import SetupClient

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ai_bootstrap',ROOT/'scripts/ai-bootstrap.py')
bootstrap=importlib.util.module_from_spec(spec);spec.loader.exec_module(bootstrap)

class SetupHTTPTests(fixtures.AppTest):
    def setUp(self):
        super().setUp()
        self.server=Server(("127.0.0.1",0),self.app)
        self.port=self.server.server_address[1]
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={"poll_interval":.05},daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(2)
        super().tearDown()

    request=fixtures.HTTPServerTests.request
    admin=fixtures.HTTPServerTests.admin

    def ticket(self):
        status, _, value=self.request('POST','/api/admin/setup-ticket',{},token=self.admin)
        self.assertEqual(status,200)
        return value['ticket']

    def test_single_use_ticket_creates_http_only_local_session(self):
        ticket=self.ticket()
        self.assertNotEqual(ticket,self.admin)
        status,headers,result=self.request('POST','/api/setup/session',{'ticket':ticket})
        self.assertEqual(status,200)
        self.assertIn('HttpOnly',headers['Set-Cookie'])
        self.assertIn('SameSite=Strict',headers['Set-Cookie'])
        status,_,_=self.request('GET','/api/admin/setup',headers={'Cookie':headers['Set-Cookie'].split(';')[0]})
        self.assertEqual(status,200)
        self.assertEqual(self.request('POST','/api/setup/session',{'ticket':ticket})[0],401)

    def test_ticket_expiry_cross_origin_and_remote_host_are_rejected(self):
        ticket=self.ticket()
        self.assertEqual(self.request('POST','/api/setup/session',{'ticket':ticket},headers={'Origin':'https://example.com'})[0],401)
        self.assertEqual(self.request('POST','/api/setup/session',{'ticket':ticket},headers={'Host':'192.168.1.5'})[0],401)
        self.app.setup_tickets[ticket]=time.time()-1
        self.assertEqual(self.request('POST','/api/setup/session',{'ticket':ticket})[0],401)
        self.assertEqual(self.request('POST','/api/admin/setup-ticket',{})[0],401)

    def test_setup_api_does_not_offer_generic_commands_or_public_control(self):
        self.assertEqual(self.request('GET','/api/admin/setup')[0],401)
        self.assertEqual(self.request('POST','/api/admin/setup/execute',{'command':'echo no'},token=self.admin)[0],400)
        with patch.object(self.app.commissioning,'action',return_value={'ok':True}) as action:
            self.assertEqual(self.request('POST','/api/admin/setup/cancel',{'job_id':'fake'},token=self.admin)[0],200)
            action.assert_called_once_with('cancel',{'job_id':'fake'})
        with patch.object(self.app.commissioning,'action') as action:
            self.assertEqual(self.request('POST','/api/admin/setup/probe',{},token=self.admin,headers={'Origin':'http://untrusted.test'})[0],401)
            action.assert_not_called()

    def test_recovery_packet_excludes_durable_secrets(self):
        status,_,packet=self.request('GET','/api/admin/setup-context',token=self.admin)
        self.assertEqual(status,200)
        self.assertIn('setup',packet);self.assertIn('diagnostics',packet)
        text=json.dumps(packet)
        for value in self.app.config.secrets.values():
            if value:self.assertNotIn(value,text)
        self.assertIn('two repair cycles',text)

    def test_client_handoff_keeps_ticket_out_of_returned_output(self):
        client=SetupClient(self.app.config,self.port)
        with patch('songsketch.setup_client.webbrowser.open',return_value=True) as opened:
            result=client.open_guide()
        self.assertTrue(result['opened'])
        self.assertNotIn('ticket',json.dumps(result))
        url=opened.call_args.args[0]
        self.assertIn('#ticket=',url);self.assertNotIn(self.admin,url)

class BootstrapPreservationTests(unittest.TestCase):
    def test_dry_run_makes_no_folders_or_processes(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)/'private'
            with patch.object(bootstrap.subprocess,'Popen') as process:
                result=bootstrap.bootstrap(folder,8765,dry_run=True)
            self.assertTrue(result['dry_run']);self.assertFalse(folder.exists());process.assert_not_called()

    def test_existing_install_is_never_overlaid(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);dest=root/'app';(dest/'songsketch').mkdir(parents=True)
            sentinel=dest/'songsketch/server.py';sentinel.write_text('local changes')
            self.assertEqual(bootstrap.managed_copy(ROOT,dest),'existing')
            self.assertEqual(sentinel.read_text(),'local changes')
            alien=root/'other';alien.mkdir();(alien/'mine.txt').write_text('keep')
            with self.assertRaises(RuntimeError):bootstrap.managed_copy(ROOT,alien)
            self.assertEqual((alien/'mine.txt').read_text(),'keep')

    def test_wrong_service_is_not_stopped_or_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(bootstrap,'port_is_open',return_value=True),patch.object(bootstrap,'health_check',return_value=Mock(state='foreign')),patch.object(bootstrap.subprocess,'Popen') as process,patch.object(bootstrap,'managed_copy') as copy:
                with self.assertRaises(RuntimeError):bootstrap.bootstrap(temporary,8765,no_open=True)
                process.assert_not_called();copy.assert_not_called()

    def test_real_managed_start_reuse_and_shutdown(self):
        with tempfile.TemporaryDirectory() as temporary:
            with socket.socket() as sock:
                sock.bind(("127.0.0.1",0)); port=sock.getsockname()[1]
            pid=None
            try:
                launched=subprocess.run([sys.executable,str(ROOT/"scripts/ai-bootstrap.py"),"--data-dir",temporary,"--port",str(port),"--no-open"],capture_output=True,text=True,timeout=45)
                self.assertEqual(launched.returncode,0,launched.stdout)
                value=json.loads(launched.stdout);pid=value["supervisor_pid"]
                self.assertEqual(value["installation"],"installed")
                self.assertFalse(value["persistent_service"])
                app=Path(value["application"])
                for name in ("Pair Garden Pi.command","integration-plan.md","scripts/commission-pi.py","artwork/catalogue.json"):
                    self.assertTrue((app/name).is_file(),name)
                preflight=subprocess.run([sys.executable,str(app/"scripts/check-install.py")],capture_output=True,text=True,timeout=15)
                self.assertEqual(preflight.returncode,0,preflight.stdout)
                cfg=Config(temporary)
                client=SetupClient(cfg,port)
                context=client.request("/api/admin/setup-context")
                self.assertIsNone(context["setup"]["job"])
                self.assertEqual(value["version"],context["version"])
                again=bootstrap.bootstrap(temporary,port,no_open=True)
                self.assertTrue(again["reused_running_server"])
                for secret in cfg.secrets.values():
                    if secret:self.assertNotIn(secret,launched.stdout)
            finally:
                if pid:
                    os.kill(pid,signal.SIGTERM)
                    deadline=time.monotonic()+30
                    while time.monotonic()<deadline and bootstrap.port_is_open(port):time.sleep(.1)
                    self.assertFalse(bootstrap.port_is_open(port),"Owned server should stop with its supervisor")

    def test_existing_server_requires_matching_admin_credentials(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(bootstrap,'port_is_open',return_value=True),patch.object(bootstrap,'health_check',return_value=Mock(state='healthy')),patch.object(bootstrap.SetupClient,'request',side_effect=RuntimeError('different data folder')),patch.object(bootstrap.subprocess,'Popen') as process:
                with self.assertRaises(RuntimeError):bootstrap.bootstrap(temporary,8765,no_open=True)
                process.assert_not_called()

if __name__=='__main__':unittest.main()
