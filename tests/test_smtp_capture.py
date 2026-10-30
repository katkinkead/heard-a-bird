"""Real SMTP sockets against a loopback-only sink. Never forwards mail."""
import socketserver,threading,tempfile,unittest
from songsketch.server import App
from songsketch.store import iso
class Sink(socketserver.StreamRequestHandler):
 def handle(self):
  self.wfile.write(b'220 localhost capture\r\n');data=False;body=[]
  while True:
   line=self.rfile.readline(65537)
   if not line:return
   if data:
    if line==b'.\r\n':
     self.server.messages.append(b''.join(body));data=False
     if self.server.mode=='drop':return
     self.wfile.write(b'250 captured locally\r\n')
    else:body.append(line)
    continue
   command=line.split(b' ',1)[0].strip().upper()
   if command in (b'EHLO',b'HELO'):self.wfile.write(b'250 localhost\r\n')
   elif command==b'RCPT' and self.server.mode=='refuse':self.wfile.write(b'550 controlled refusal\r\n')
   elif command==b'DATA':self.wfile.write(b'354 end with dot\r\n');data=True
   elif command==b'QUIT':self.wfile.write(b'221 goodbye\r\n');return
   else:self.wfile.write(b'250 ok\r\n')
class SMTPTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.app=App(self.tmp.name,background=False)
  self.sink=socketserver.ThreadingTCPServer(('127.0.0.1',0),Sink);self.sink.daemon_threads=True;self.sink.mode='capture';self.sink.messages=[]
  self.thread=threading.Thread(target=self.sink.serve_forever,kwargs={'poll_interval':.01},daemon=True);self.thread.start()
  self.app.config.update({'smtp_host':'127.0.0.1','smtp_port':self.sink.server_address[1],'smtp_from':'sender@example.invalid','notification_email':'recipient@example.invalid','smtp_tls':False})
  self.event()
 def event(self):self.app.store.ingest({'station_id':'garden','event_id':'smtp-qa','scientific_name':'Songsketch qa_species','common_name':'QA fixture','confidence':.99,'observed_at':iso()})
 def tearDown(self):self.sink.shutdown();self.sink.server_close();self.thread.join(2);self.app.close();self.tmp.cleanup()
 def row(self):return self.app.store.query('SELECT * FROM email_outbox')[0]
 def test_real_capture_and_duplicate_suppression(self):
  self.app.maintenance.send_mail();self.assertEqual(self.row()['status'],'sent');self.assertEqual(len(self.sink.messages),1);self.event();self.app.maintenance.send_mail();self.assertEqual(len(self.sink.messages),1);self.assertIn(b'QA fixture',self.sink.messages[0])
 def test_refusal_is_retryable_and_recovery_succeeds(self):
  self.sink.mode='refuse';self.app.maintenance.send_mail();self.assertEqual(self.row()['status'],'failed');self.assertEqual(self.row()['attempts'],1);self.assertFalse(self.sink.messages);self.sink.mode='capture';self.app.maintenance.retry_email();self.app.maintenance.send_mail();self.assertEqual(self.row()['status'],'sent');self.assertEqual(len(self.sink.messages),1)
 def test_lost_ack_is_uncertain_without_automatic_resend(self):
  self.sink.mode='drop';self.app.maintenance.send_mail();self.assertEqual(self.row()['status'],'uncertain');self.assertEqual(len(self.sink.messages),1);self.sink.mode='capture';self.app.maintenance.send_mail();self.assertEqual(len(self.sink.messages),1)
