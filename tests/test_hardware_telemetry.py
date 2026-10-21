"""Mocked Pi hardware sampling + durable server contract; no hardware commands."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('pi_hardware_relay', ROOT / 'pi/relay.py')
relay = importlib.util.module_from_spec(spec); spec.loader.exec_module(relay)
from songsketch.config import Config
from songsketch.store import Store, validate_hardware, iso
from songsketch.setup_health import build_setup_health
NOW = datetime(2026,10,21,12,tzinfo=timezone.utc)


def sample(mask='throttled=0x0', temperature="temp=50.2'C", fallback=None):
    outputs={'get_throttled':mask,'measure_temp':temperature}
    return relay.sample_hardware(lambda command:(outputs[command], None if outputs[command] is not None else 'unavailable'),
                                 lambda:fallback, now=NOW.timestamp())


class HardwareSamplerTests(unittest.TestCase):
    def test_current_and_historical_bits_remain_distinct(self):
        historical=sample('throttled=0x50000')
        self.assertEqual(historical['current_flags'],[])
        self.assertEqual(historical['historical_flags'],['under_voltage','throttled'])
        self.assertEqual(historical['power_status'],'healthy')
        current=sample('throttled=0x50005')
        self.assertEqual(current['current_flags'],['under_voltage','throttled'])
        self.assertEqual(current['power_status'],'warning')
        self.assertEqual(current['thermal_status'],'healthy')
        self.assertEqual(sample('throttled=0xf000f')['historical_flags'],list(relay.HARDWARE_FLAGS))

    def test_provisional_temperature_and_soft_limit_not_shutdown(self):
        self.assertEqual(sample(temperature="temp=74.9'C")['thermal_status'],'healthy')
        self.assertEqual(sample(temperature="temp=75.0'C")['thermal_status'],'warning')
        self.assertEqual(sample('throttled=0x8')['thermal_status'],'warning')
        self.assertEqual(sample('throttled=0x80000')['thermal_status'],'healthy')
        self.assertEqual(sample()['thermal_warning_c'],75)

    def test_unavailable_malformed_and_fallback_samples_do_not_invent_health(self):
        missing=sample(None,None)
        self.assertEqual(missing['power_status'],'unknown')
        self.assertEqual(missing['thermal_status'],'unknown')
        self.assertEqual(missing['sample_errors'],['throttled_unavailable','temperature_unavailable'])
        malformed=sample('throttled=secret-raw-output',"temp=nan'C")
        self.assertNotIn('secret',json.dumps(malformed))
        self.assertEqual(malformed['sample_errors'],['throttled_invalid','temperature_invalid'])
        fallback=sample(temperature=None,fallback=61.5)
        self.assertEqual((fallback['temperature_source'],fallback['thermal_status']),('sysfs','healthy'))
        partial=sample(None,None,fallback=61.5)
        self.assertEqual(partial['temperature_c'],61.5)
        self.assertEqual(partial['thermal_status'],'unknown')
        self.assertEqual(sample(None,None,fallback=78)['thermal_status'],'warning')
        for raw in ("temp=151'C","temp=-41'C","temp=50'C\nother"):
            self.assertIsNone(sample(temperature=raw)['temperature_c'])

    def test_only_allowlisted_commands_are_executed_with_bounded_timeout(self):
        with mock.patch.object(relay.os.path,'isfile',return_value=True), mock.patch.object(relay.os,'access',return_value=True), mock.patch.object(relay.subprocess,'run') as run:
            run.return_value=subprocess.CompletedProcess([],0,'throttled=0x0\n')
            self.assertEqual(relay.read_vcgencmd('get_throttled'),('throttled=0x0',None))
            args,kwargs=run.call_args
            self.assertEqual(args[0],['/usr/bin/vcgencmd','get_throttled'])
            self.assertEqual(kwargs['timeout'],1)
            self.assertEqual(kwargs['stdin'],subprocess.DEVNULL)
            self.assertNotIn('shell',kwargs)
            run.side_effect=subprocess.TimeoutExpired(['vcgencmd'],1)
            self.assertEqual(relay.read_vcgencmd('measure_temp'),(None,'timeout'))
            with self.assertRaises(ValueError):relay.read_vcgencmd('anything_else')
            self.assertEqual(run.call_count,2)

    def test_sysfs_uses_pi_marker_and_millidegrees(self):
        with mock.patch('builtins.open',side_effect=[mock.mock_open(read_data='Raspberry Pi 5 Model B\0')(),mock.mock_open(read_data='61234\n')()]):
            self.assertEqual(relay.read_sysfs_temperature(),61.2)
        with mock.patch('builtins.open',mock.mock_open(read_data='Unrelated host')) as reader:
            self.assertIsNone(relay.read_sysfs_temperature())
            reader.assert_called_once()


class HardwareDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        token=self.root/'station.token';token.write_text('test-station-secret-never-networked');token.chmod(0o600)
        self.config={'station_id':'garden','source_instance_id':'fixture','server_url':'http://server.invalid',
                     'birdnet_url':'http://birdnet.invalid','token_file':str(token),'data_dir':str(self.root/'pi'),
                     'timezone':'Europe/London','model_id':'BirdNET_V2.4'}
        self.server=Store(Config(self.root/'server'),ROOT/'artwork/catalogue.json')
        self.bodies=[]
        def transport(url,token=None,body=None,timeout=8):
            if url.endswith('/heartbeat'):
                self.bodies.append(body)
                return self.server.heartbeat(body)
            return {}
        self.relay=relay.Relay(self.config,transport)

    def tearDown(self):
        self.relay.store.close();self.server.close();self.tmp.cleanup()

    def test_live_faults_group_survive_unknown_samples_and_report_recovery(self):
        warning=sample('throttled=0x50005',"temp=78'C")
        with mock.patch.object(relay,'sample_hardware',return_value=warning):
            for _ in range(3):self.relay.heartbeat()
        self.assertEqual(len(self.relay.store.reports()),2)
        self.assertEqual(self.bodies[-1]['hardware'],warning)
        self.assertEqual(self.server.station_status()['hardware']['power_status'],'warning')
        for report in self.relay.store.reports():
            self.server.report(report)
            self.assertIn('hardware',report['details'])
        self.assertEqual(len(self.server.query('SELECT * FROM issues WHERE resolved=0')),2)
        with mock.patch.object(relay,'sample_hardware',return_value=sample(None,None)):
            self.relay.heartbeat()
        self.assertEqual(len(self.relay.store.reports()),2)
        self.assertTrue(all(row['active'] for row in self.relay.store.snapshot()['faults']))
        with mock.patch.object(relay,'sample_hardware',return_value=sample('throttled=0x50000')):
            self.relay.heartbeat()
        self.assertEqual(len(self.relay.store.reports()),4)
        for report in self.relay.store.reports():self.server.report(report)
        self.assertEqual(len(self.server.query('SELECT * FROM issues WHERE resolved=0')),0)
        self.assertEqual(self.server.station_status()['hardware']['historical_flags'],['under_voltage','throttled'])

    def test_schema_rejects_inconsistent_unbounded_or_untrusted_measurements(self):
        good=sample();original=deepcopy(good)
        self.assertEqual(validate_hardware(good)['temperature_c'],50.2)
        self.assertEqual(good,original)
        invalid=[{'power_status':'warning'},{'temperature_c':float('nan')},{'temperature_c':True},
                 {'current_flags':['under_voltage']},{'throttled_hex':'0x100000000'},
                 {'historical_flags':['bad']},{'sample_errors':['raw exception with secrets']},
                 {'sample_errors':[]*0,'thermal_warning_c':80},{'observed_at':'no date'},
                 {'temperature_source':'arbitrary source'}, {'extra':'unexpected'}]
        for changes in invalid:
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.server.heartbeat({'station_id':'garden','hardware':dict(good,**changes)})
        self.server.heartbeat({'station_id':'garden'})
        self.assertIsNone(self.server.station_status()['hardware'])

    def test_setup_health_preserves_current_history_partial_and_stale_boundaries(self):
        hardware=sample('throttled=0x50000')
        evidence={'generated_at':iso(NOW),'database_check':{'quick_check':'ok'},
                  'station':{'connected':True,'last_heartbeat':iso(NOW),'hardware':hardware}}
        result=build_setup_health({},evidence,now=NOW)
        components={c['id']:c for c in result['components']}
        self.assertEqual(components['power']['status'],'healthy')
        self.assertIn('under_voltage',json.dumps(components['power']['evidence']))
        hardware['observed_at']=iso(NOW-timedelta(minutes=10))
        result=build_setup_health({},evidence,now=NOW)
        components={c['id']:c for c in result['components']}
        self.assertEqual(components['power']['status'],'unverified')
        self.assertEqual(components['thermal']['status'],'unverified')
        fingerprint=hashlib.sha256(b'garden:power').hexdigest()[:24]
        evidence['reports']=[{'station_id':'garden','details':{'component':'power'}}]
        evidence['issues']=[{'id':fingerprint,'resolved':0,'message':'Power fault','severity':'warning'}]
        result=build_setup_health({},evidence,now=NOW)
        self.assertEqual(result['problems'][-1]['component'],'power')

if __name__=='__main__':unittest.main()
