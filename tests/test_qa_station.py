import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('qa_station',ROOT/'scripts/qa-station.py');qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
class StationTests(unittest.TestCase):
    def test_fault_windows_repeat_without_touching_network(self):
        for seconds,expected in [(0,'healthy'),(300,'capture-failed'),(420,'healthy'),(480,'offline'),(719,'offline'),(720,'healthy'),(1680,'offline')]:self.assertEqual(qa.phase(seconds),expected)
    def test_wrong_ack_retains_durable_event(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.json';state={'pending':[{'event_id':'one'}],'accepted':0,'duplicate_acks':0};qa.save(p,state)
            with patch.object(qa,'request',return_value={'ok':True,'id':'other'}):
                with self.assertRaises(ValueError):qa.deliver_pending({},state,p)
            self.assertEqual(json.loads(p.read_text())['pending'],[{'event_id':'one'}])
    def test_lost_ack_then_duplicate_ack_drains_once(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.json';state={'pending':[{'event_id':'one'}],'accepted':0,'duplicate_acks':0};qa.save(p,state)
            with patch.object(qa,'request',side_effect=TimeoutError):
                with self.assertRaises(TimeoutError):qa.deliver_pending({},state,p)
            recovered=json.loads(p.read_text())
            with patch.object(qa,'request',return_value={'ok':True,'id':'one','duplicate':True}):qa.deliver_pending({},recovered,p)
            self.assertEqual(recovered['pending'],[]);self.assertEqual(recovered['duplicate_acks'],1)
if __name__=='__main__':unittest.main()
