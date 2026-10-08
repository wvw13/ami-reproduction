"""Offline verification: no credentials, SDK, socket or live DB."""
import json,sys,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phase_budget_guard import restrict_budget
class FakeBase:
 def __init__(self,total):self.total=total;self.lock=threading.RLock();self.sent=0;self.stopped=None
 def check(self):
  if self.stopped:raise RuntimeError(self.stopped)
 def halt(self,reason):self.stopped=reason;raise RuntimeError(reason)
 def request(self,*a):self.sent+=1;return 'sent'
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.file=self.root/'run/windows-real-e2e/server-phase-budget.json';self.file.parent.mkdir(parents=True);self.baseline=.0002367
  self.permit={'enabled':True,'limit_RMB':.02,'baseline_RMB':self.baseline};self.file.write_text(json.dumps(self.permit));self.cls=restrict_budget(FakeBase,self.root)
  self.req=SimpleNamespace(content=json.dumps({'max_tokens':200}).encode())
 def tearDown(self):self.tmp.cleanup()
 def test_small_call_allowed(self):
  b=self.cls(self.baseline);self.assertEqual(b.request(self.req,'gpt-4o-mini','fixture'),'sent')
 def test_phase_reservation_blocks_before_send(self):
  b=self.cls(self.baseline+.02-.00001)
  with self.assertRaises(RuntimeError):b.request(self.req,'gpt-4o-mini','fixture')
  self.assertEqual(b.sent,0)
 def test_baseline_never_resets_on_restart(self):
  b=self.cls(self.baseline+.02)
  with self.assertRaises(RuntimeError):b.request(self.req,'text-embedding-v4','fixture')
  self.assertEqual(b.sent,0)
 def test_cumulative_ceiling_also_blocks(self):
  self.permit['baseline_RMB']=.045;self.file.write_text(json.dumps(self.permit));b=self.cls(.04999)
  with self.assertRaises(RuntimeError):b.request(self.req,'text-embedding-v4','fixture')
  self.assertEqual(b.sent,0)
 def test_disabled_permit_blocks(self):
  self.permit['enabled']=False;self.file.write_text(json.dumps(self.permit));b=self.cls(self.baseline)
  with self.assertRaises(RuntimeError):b.request(self.req,'gpt-4o-mini','fixture')
  self.assertEqual(b.sent,0)
 def test_phase_cost_persisted(self):
  b=self.cls(self.baseline);b.request(self.req,'gpt-4o-mini','fixture')
  state=json.loads((self.file.parent/'phase-cost.json').read_text())
  self.assertEqual(state['baseline_RMB'],self.baseline)
  self.assertEqual(state['pending_reservation_RMB'],0)
 def test_float_ledger_sum_matches_persisted_baseline(self):
  b=self.cls(self.baseline-1e-19)
  self.assertEqual(b.request(self.req,'gpt-4o-mini','fixture'),'sent')
 def test_persisted_spending_cannot_reset(self):
  (self.file.parent/'phase-cost.json').write_text(json.dumps({'baseline_RMB':self.baseline,'limit_RMB':.02,'spent_RMB':.02,'pending_reservation_RMB':0}))
  b=self.cls(self.baseline)
  with self.assertRaises(RuntimeError):b.request(self.req,'gpt-4o-mini','fixture')
  self.assertEqual(b.sent,0)
 def test_interrupted_reservation_blocks_after_restart(self):
  (self.file.parent/'phase-cost.json').write_text(json.dumps({'baseline_RMB':self.baseline,'limit_RMB':.02,'spent_RMB':0,'pending_reservation_RMB':.001}))
  b=self.cls(self.baseline)
  with self.assertRaises(RuntimeError):b.request(self.req,'gpt-4o-mini','fixture')
  self.assertEqual(b.sent,0)
 def test_phase_just_below_boundary_allows(self):
  reserve=((len(self.req.content)+1024)*.15+200*.6)/1e6
  b=self.cls(self.baseline+.02-reserve-1e-8)
  self.assertEqual(b.request(self.req,'gpt-4o-mini','fixture'),'sent')
 def test_phase_just_above_boundary_blocks(self):
  reserve=((len(self.req.content)+1024)*.15+200*.6)/1e6
  b=self.cls(self.baseline+.02-reserve+1e-8)
  with self.assertRaises(RuntimeError):b.request(self.req,'gpt-4o-mini','fixture')
  self.assertEqual(b.sent,0)
 def test_cumulative_just_below_boundary_allows(self):
  self.permit['baseline_RMB']=.045;self.file.write_text(json.dumps(self.permit))
  reserve=((len(self.req.content)+1024)*.15+200*.6)/1e6
  b=self.cls(.05-reserve-1e-8)
  self.assertEqual(b.request(self.req,'gpt-4o-mini','fixture'),'sent')
 def test_cumulative_just_above_boundary_blocks(self):
  self.permit['baseline_RMB']=.045;self.file.write_text(json.dumps(self.permit))
  reserve=((len(self.req.content)+1024)*.15+200*.6)/1e6
  b=self.cls(.05-reserve+1e-8)
  with self.assertRaises(RuntimeError):b.request(self.req,'gpt-4o-mini','fixture')
  self.assertEqual(b.sent,0)
if __name__=='__main__':unittest.main()
