"""Watchdog tests use fake time, subprocesses and HTTP; no services launched."""
import io
import http.client
import json
import logging
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from songsketch.supervisor import (Health, Supervisor, RestartBudget, health_check,
                                  configure_logging, MAX_BACKOFF, MAX_RESTARTS,
                                  NoHealthRedirect)


class Response:
    def __init__(self, value, status=200):
        self.status = status
        self.payload = value if isinstance(value,bytes) else json.dumps(value).encode()
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self, maximum): return self.payload[:maximum]


class FakeClock:
    def __init__(self):
        self.now = 0
        self.waits = []
        self.stop_at = None
        self.callback = None
    def __call__(self): return self.now
    def wait(self, seconds):
        self.waits.append(seconds)
        self.now += seconds
        if self.callback: self.callback(self.now)
        return self.stop_at is not None and self.now >= self.stop_at


class FakeChild:
    serial = 100
    def __init__(self, exited=None, slow_stop=False):
        FakeChild.serial += 1
        self.pid = FakeChild.serial
        self.code = exited
        self.slow_stop = slow_stop
        self.terminated = 0
        self.killed = 0
        self.waited = 0
    def poll(self): return self.code
    def terminate(self):
        self.terminated += 1
        if not self.slow_stop: self.code = -15
    def kill(self):
        self.killed += 1
        self.code = -9
    def wait(self,timeout=None):
        self.waited += 1
        if self.code is None: raise subprocess.TimeoutExpired("owned child",timeout)
        return self.code


class HealthProbeTests(unittest.TestCase):
    def probe(self,response):
        opener = Mock()
        opener.open.return_value = response
        return health_check(8765,opener), opener

    def test_exact_application_and_boolean_health_are_required(self):
        result, opener = self.probe(Response({"application":"songsketch","ok":True}))
        self.assertEqual(result.state,"healthy")
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url,"http://127.0.0.1:8765/health")
        self.assertEqual(opener.open.call_args.kwargs["timeout"],5)
        for payload in ({"application":"songsketch","ok":"true"},{"ok":True},{"application":"songsketch","ok":False}):
            self.assertEqual(self.probe(Response(payload))[0].state,"unhealthy")

    def test_foreign_service_is_distinguished_without_logging_body(self):
        result,_ = self.probe(Response({"application":"different","token":"do-not-copy"}))
        self.assertEqual(result.state,"foreign")
        self.assertNotIn("do-not-copy",result.reason)

    def test_unreachable_malformed_and_oversized_responses_are_bounded(self):
        opener = Mock()
        opener.open.side_effect = URLError("A private server description")
        result = health_check(8765,opener)
        self.assertEqual(result.state,"unhealthy")
        self.assertNotIn("private",result.reason)
        for response in (Response(b"not json"),Response([True]),Response(b"x"*20000),Response({},503)):
            self.assertEqual(self.probe(response)[0].state,"unhealthy")

    def test_health_checks_cannot_follow_remote_redirects(self):
        handler = NoHealthRedirect()
        self.assertIsNone(handler.redirect_request(None,None,302,"Found",{},"https://example.invalid/"))
        with patch("songsketch.supervisor.build_opener") as build:
            build.return_value.open.return_value = Response({"application":"songsketch","ok":True})
            self.assertEqual(health_check(8765).state,"healthy")
            self.assertTrue(any(isinstance(arg,NoHealthRedirect) for arg in build.call_args.args))


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.clock = FakeClock()
        self.children = []
        self.logger = Mock()
    def tearDown(self): self.temp.cleanup()

    def make(self, *, outcomes=None, probe=None, port_probe=None):
        codes = list(outcomes or [])
        def factory(*args,**kwargs):
            child = FakeChild(codes.pop(0) if codes else None)
            self.children.append(child)
            return child
        self.factory = Mock(side_effect=factory)
        self.supervisor = Supervisor(directory=self.temp.name,process_factory=self.factory,
            probe=probe or Mock(return_value=Health("healthy","ok")),
            port_probe=port_probe or Mock(return_value=False),clock=self.clock,
            wait=self.clock.wait,logger=self.logger)
        return self.supervisor

    def test_command_uses_current_python_and_portable_project_directory(self):
        supervisor = self.make()
        self.clock.stop_at = 1
        self.assertEqual(supervisor.run(),0)
        command = self.factory.call_args.args[0]
        self.assertEqual(command[:3],[sys.executable,"-m","songsketch.server"])
        self.assertIn(str(Path(self.temp.name).resolve()),command)
        self.assertEqual(self.factory.call_args.kwargs["cwd"],str(ROOT))
        self.assertTrue(self.factory.call_args.kwargs["start_new_session"])
        self.assertEqual(self.children[0].terminated,1)
        self.assertIsNone(supervisor.child)

    def test_existing_server_is_never_started_over_or_killed(self):
        supervisor = self.make(port_probe=Mock(return_value=True))
        self.assertEqual(supervisor.run(),3)
        self.factory.assert_not_called()
        state = json.loads((Path(self.temp.name)/"supervisor-status.json").read_text())
        self.assertEqual(state["state"],"already_running")
        self.assertIn("already running",state["reason"])
        self.assertEqual(self.children,[])

    def test_three_consecutive_failures_restart_owned_child_once(self):
        probe = Mock(side_effect=[Health("unhealthy","offline")]*3+[Health("healthy","ok")]*3)
        supervisor = self.make(probe=probe)
        self.clock.stop_at = 123
        self.assertEqual(supervisor.run(),0)
        self.assertEqual(self.factory.call_count,2)
        self.assertEqual(supervisor.total_restarts,1)
        self.assertEqual(self.children[0].terminated,1)
        self.assertEqual(self.children[1].terminated,1)

    def test_successful_check_breaks_the_failure_streak(self):
        probe = Mock(side_effect=[Health("unhealthy","offline"),Health("unhealthy","offline"),Health("healthy","ok"),Health("unhealthy","offline")])
        supervisor = self.make(probe=probe)
        self.clock.stop_at = 121
        self.assertEqual(supervisor.run(),0)
        self.assertEqual(self.factory.call_count,1)
        self.assertEqual(supervisor.total_restarts,0)

    def test_crash_loop_stops_after_five_restarts_with_exponential_wait(self):
        supervisor = self.make(outcomes=[1]*7)
        self.assertEqual(supervisor.run(),4)
        self.assertEqual(self.factory.call_count,MAX_RESTARTS+1)
        self.assertEqual(supervisor.total_restarts,5)
        self.assertEqual(self.clock.waits,[1,2,4,8,16])
        self.assertTrue(all(child.waited for child in self.children))
        state = json.loads((Path(self.temp.name)/"supervisor-status.json").read_text())
        self.assertEqual(state["state"],"failed")
        self.assertIsNone(state["child_pid"])

    def test_backoff_is_capped_and_stop_during_wait_launches_no_child(self):
        supervisor = self.make(outcomes=[1])
        supervisor.consecutive_restarts = 20
        self.clock.stop_at = 1
        self.assertEqual(supervisor.run(),0)
        self.assertEqual(self.clock.waits,[MAX_BACKOFF])
        self.assertEqual(self.factory.call_count,1)

    def test_new_port_owner_during_restart_is_left_alone(self):
        supervisor = self.make(outcomes=[1],port_probe=Mock(side_effect=[False,True]))
        self.assertEqual(supervisor.run(),3)
        self.assertEqual(self.factory.call_count,1)
        self.assertEqual(self.children[0].terminated,0)
        self.assertEqual(self.children[0].killed,0)

    def test_foreign_health_response_stops_only_owned_child(self):
        supervisor = self.make(probe=Mock(return_value=Health("foreign","different app")))
        self.assertEqual(supervisor.run(),3)
        self.assertEqual(self.factory.call_count,1)
        self.assertEqual(self.children[0].terminated,1)

    def test_signal_request_causes_graceful_child_shutdown(self):
        supervisor = self.make()
        self.clock.callback = lambda now: supervisor.request_stop() if now >= 2 else None
        self.assertEqual(supervisor.run(),0)
        self.assertEqual(self.children[0].terminated,1)
        self.assertEqual(self.children[0].killed,0)

    def test_stuck_owned_child_is_killed_then_reaped(self):
        supervisor = self.make()
        child = FakeChild(slow_stop=True)
        supervisor.child = child
        supervisor.stop_child()
        self.assertEqual(child.terminated,1)
        self.assertEqual(child.killed,1)
        self.assertEqual(child.waited,2)
        self.assertIsNone(supervisor.child)

    def test_status_write_failure_does_not_orphan_owned_server(self):
        supervisor = self.make()
        self.clock.stop_at = 2
        with patch("songsketch.supervisor.private_json",side_effect=OSError("Disk full")):
            self.assertEqual(supervisor.run(),0)
        self.assertEqual(self.factory.call_count,1)
        self.assertEqual(self.children[0].terminated,1)
        self.assertIsNone(supervisor.child)
        self.assertTrue(self.logger.error.called)

    def test_invalid_host_or_port_does_not_launch(self):
        for values in ({"host":"192.0.2.1"},{"port":0},{"port":65536},{"port":True}):
            with self.assertRaises(ValueError): Supervisor(directory=self.temp.name,**values)


class BudgetAndLogTests(unittest.TestCase):
    def test_rolling_window_recovers_without_wall_clock(self):
        budget = RestartBudget()
        for t in range(5): self.assertTrue(budget.record(t))
        self.assertFalse(budget.record(10))
        self.assertTrue(budget.record(900))
        self.assertEqual(len(budget.times),5)

    def test_rotating_log_is_bounded_and_private(self):
        with tempfile.TemporaryDirectory() as directory:
            logger = configure_logging(directory)
            handler = next(h for h in logger.handlers if hasattr(h,"maxBytes"))
            try:
                self.assertEqual(handler.maxBytes,1024*1024)
                self.assertEqual(handler.backupCount,3)
                logger.warning("Owned child restarted after failed local checks")
                handler.flush()
                handler.doRollover()
                path = Path(directory)/"logs/supervisor.log"
                self.assertEqual(path.stat().st_mode & 0o777,0o600)
                self.assertTrue(path.with_name("supervisor.log.1").exists())
            finally:
                for h in list(logger.handlers): h.close();logger.removeHandler(h)


@unittest.skipUnless(hasattr(signal,"SIGKILL"),"Real crash recovery check requires POSIX process signals")
class RealProcessSupervisorRecoveryTests(unittest.TestCase):
    def test_real_child_crash_recovers_http_and_history_then_parent_stop_reaps_child(self):
        """Exercise actual Python processes on an isolated, ephemeral local port."""
        with tempfile.TemporaryDirectory(prefix="songsketch-watchdog-test-") as directory:
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as reservation:
                reservation.bind(("127.0.0.1",0))
                port = reservation.getsockname()[1]
            status_path = Path(directory)/"supervisor-status.json"
            parent = subprocess.Popen(
                [sys.executable,"-m","songsketch.supervisor","--host","127.0.0.1",
                 "--port",str(port),"--data-dir",directory],
                cwd=str(ROOT),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            owned_pids = set()

            def request(method,path,value=None,token=None):
                conn = http.client.HTTPConnection("127.0.0.1",port,timeout=.4)
                headers = {"Content-Type":"application/json"}
                if token: headers["Authorization"] = "Bearer "+token
                try:
                    conn.request(method,path,body=json.dumps(value) if value is not None else None,headers=headers)
                    response = conn.getresponse()
                    return response.status,json.loads(response.read())
                finally:
                    conn.close()

            def wait_for_owned_healthy_child(previous=None):
                # Startup and post-crash recovery are independent phases. A
                # slow initial launch must not consume the recovery allowance.
                deadline = time.monotonic()+30
                while time.monotonic()<deadline:
                    self.assertIsNone(parent.poll(),"Supervisor exited before recovery")
                    try:
                        note = json.loads(status_path.read_text())
                        pid = note.get("child_pid")
                        if note.get("supervisor_pid")==parent.pid and pid and pid!=previous:
                            owned_pids.add(pid)
                            code,health = request("GET","/health")
                            if code==200 and health.get("application")=="songsketch" and health.get("ok") is True:
                                return pid
                    except (OSError,ValueError,http.client.HTTPException):
                        pass
                    time.sleep(.05)
                self.fail("Owned server did not become healthy within the bounded recovery deadline")

            try:
                original_pid = wait_for_owned_healthy_child()
                secrets = json.loads((Path(directory)/"secrets.json").read_text())
                code,result = request("POST","/api/admin/test-detection",
                                      {"scientific_name":"Erithacus rubecula"},secrets["admin_token"])
                self.assertEqual(code,200)
                event_id = result["id"]
                # The PID is taken only from this newly launched supervisor's
                # private status file. No process is discovered/killed by port.
                latest = json.loads(status_path.read_text())
                self.assertEqual(latest["supervisor_pid"],parent.pid)
                self.assertEqual(latest["child_pid"],original_pid)
                self.assertNotIn(original_pid,(os.getpid(),parent.pid))
                os.kill(original_pid,signal.SIGKILL)
                replacement_pid = wait_for_owned_healthy_child(previous=original_pid)
                self.assertNotEqual(replacement_pid,original_pid)
                code,history = request("GET","/api/admin/detections",token=secrets["admin_token"])
                self.assertEqual(code,200)
                records = [r for r in history["detections"] if r["event_id"]==event_id]
                self.assertEqual(len(records),1)
                self.assertEqual(records[0]["test"],1)
                note = json.loads(status_path.read_text())
                self.assertEqual(note["restarts_this_run"],1)
                parent.terminate()
                self.assertEqual(parent.wait(timeout=3),0)
                for pid in (original_pid,replacement_pid):
                    with self.assertRaises(ProcessLookupError): os.kill(pid,0)
                final = json.loads(status_path.read_text())
                self.assertEqual(final["state"],"stopped")
                self.assertIsNone(final["child_pid"])
            finally:
                try:
                    note = json.loads(status_path.read_text())
                    if note.get("supervisor_pid")==parent.pid and note.get("child_pid"):
                        owned_pids.add(note["child_pid"])
                except (OSError,ValueError): pass
                if parent.poll() is None:
                    parent.terminate()
                    try: parent.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        # Cleanup only PIDs recorded as this test parent's own
                        # children, never the application's normal preview port.
                        try:
                            note = json.loads(status_path.read_text())
                            if note.get("supervisor_pid")==parent.pid and note.get("child_pid"):
                                owned_pids.add(note["child_pid"])
                        except (OSError,ValueError): pass
                        for pid in owned_pids:
                            try: os.kill(pid,signal.SIGKILL)
                            except ProcessLookupError: pass
                        parent.kill()
                        parent.wait(timeout=2)
                # Also clean up an owned child if the supervisor itself failed
                # before its normal shutdown handler could reap that child.
                for pid in owned_pids:
                    if pid in (os.getpid(),parent.pid) or pid<=1: continue
                    try: os.kill(pid,signal.SIGKILL)
                    except ProcessLookupError: pass


if __name__ == "__main__": unittest.main()
