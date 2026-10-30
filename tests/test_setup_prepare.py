"""Minimal-input setup discovery; no real Pi or network connection."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock
from songsketch.setup_prepare import prepare
from songsketch.github_launcher import private_write, read_details, merge_details

class PrepareTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name).resolve()
    def tearDown(self):self.tmp.cleanup()
    def test_hostname_only_discovers_route_and_lists_only_unknowns(self):
        route=Mock(return_value='http://192.168.1.20:8765')
        value=prepare(self.path,8765,{'hostname':'garden.local'},route=route)
        route.assert_called_once_with('garden.local',8765)
        self.assertEqual(value['missing'],['username','latitude','longitude'])
        self.assertFalse(value['pi_login_attempted']);self.assertFalse(value['ready_to_probe'])
        self.assertEqual(read_details(self.path/'setup-details.json')['server_url'],'http://192.168.1.20:8765')
    def test_saved_complete_details_need_no_questions_or_network_probe(self):
        saved={'hostname':'garden.local','username':'monty','latitude':50.7,'longitude':-2.3,'server_url':'http://192.168.1.2:8765'}
        private_write(self.path/'setup-details.json',saved)
        route=Mock(side_effect=AssertionError('Do not rediscover saved values'))
        value=prepare(self.path,8765,{'hostname':'garden.local'},route=route)
        self.assertEqual(value['details'],saved);self.assertTrue(value['ready_to_probe']);self.assertEqual(value['questions'],[])
    def test_route_failure_and_loopback_are_not_success(self):
        value=prepare(self.path,8765,{'hostname':'missing.local'},route=Mock(side_effect=OSError()))
        self.assertIn('server_url',value['missing']);self.assertFalse(value['ready_to_probe'])
        value=prepare(self.path,8765,{'server_url':'http://localhost:8765'},route=Mock())
        self.assertIn('server_url',value['missing'])
    def test_previous_same_host_job_reused_but_new_host_account_not_assumed(self):
        inputs={'hostname':'garden.local','username':'known','latitude':50.7,'longitude':-2.3,'server_url':'http://192.168.1.2:8765'}
        context={'setup':{'job':{'inputs':inputs}}}
        self.assertTrue(prepare(self.path,8765,{'hostname':'garden.local'},context)['ready_to_probe'])
        value=prepare(self.path,8765,{'hostname':'new.local'},context)
        self.assertIn('username',value['missing']);self.assertEqual(value['details']['latitude'],50.7)
    def test_launcher_merge_keeps_saved_details_and_separates_hosts(self):
        saved={'hostname':'garden.local','username':'known','latitude':50.7,'capture_device':'hw:1','notification_email':'example@example.org'}
        self.assertEqual(merge_details(saved,{'hostname':'garden.local'}),saved)
        next=merge_details(saved,{'hostname':'new.local'})
        self.assertNotIn('username',next);self.assertNotIn('capture_device',next)
        self.assertEqual(next['notification_email'],saved['notification_email'])
        self.assertIn('username',saved,'must not mutate the caller')
