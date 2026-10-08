import json
import tempfile
from pathlib import Path
import unittest
import httpx
from .baseline_cache import CacheBudget,Halt,VERSION,digest

class Tests(unittest.TestCase):
    def test_cache_only_above_budget_hit_and_miss_never_send(self):
        for total in (.45,.51):
            with self.subTest(total=total),tempfile.TemporaryDirectory() as d:
                d=Path(d);root=d/'cache';root.mkdir()
                ledger=d/'ledger';ledger.write_text(json.dumps({'estimated_RMB_cost':total})+'\n')
                payload={'model':'gpt-4o-mini','messages':[],'max_tokens':10}
                endpoint='https://fake.invalid/chat/completions'
                key=digest([VERSION,'fixed',endpoint,payload])
                response={'model':'gpt-4o-mini-2024-07-18','choices':[{'message':{'content':'cached'}}]}
                path=root/(key+'.json');path.write_text(json.dumps(response));before=path.read_bytes()
                sends=[]
                def forbidden(request):
                    sends.append(request)
                    raise AssertionError('Cache-only must never send')
                with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
                    b=CacheBudget(root,ledger,'fixed',allow_network=False,client=client)
                    req=httpx.Request('POST',endpoint,json=payload)
                    self.assertEqual(b.request(req,'gpt-4o-mini',endpoint).json(),response)
                    miss=httpx.Request('POST',endpoint,json={**payload,'max_tokens':11})
                    with self.assertRaisesRegex(Halt,'cache_only_miss'):
                        b.request(miss,'gpt-4o-mini',endpoint)
                    self.assertEqual(sends,[])
                    self.assertEqual(b.calls,0)
                    self.assertEqual(b.total,total)
                    self.assertEqual(path.read_bytes(),before)

    def test_persistent_hit_and_zero_network(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);calls=[]
            def respond(r):
                calls.append(1)
                return httpx.Response(200,json={'model':'gpt-4o-mini-2024-07-18','choices':[{'message':{'content':'[]'}}],'usage':{'prompt_tokens':20,'completion_tokens':2}})
            b=CacheBudget(d/'cache',d/'ledger','fixed',allow_network=True,client=httpx.Client(transport=httpx.MockTransport(respond)))
            req=httpx.Request('POST','https://fake.invalid/chat/completions',json={'model':'gpt-4o-mini','messages':[{'role':'user','content':'synthetic'}],'max_tokens':10})
            b.request(req,'gpt-4o-mini',str(req.url));b.request(req,'gpt-4o-mini',str(req.url));self.assertEqual(len(calls),1)
            b2=CacheBudget(d/'cache',d/'ledger','fixed',allow_network=False)
            b2.request(req,'gpt-4o-mini',str(req.url));self.assertEqual(b2.calls,0)
            self.assertAlmostEqual(b2.total,.0000042)
            rows=[json.loads(x) for x in (d/'ledger').read_text().splitlines()];self.assertEqual(rows[-1]['event'],'HIT')
            self.assertNotIn('Authorization',(d/'ledger').read_text())
    def test_first_error_latches(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);calls=[]
            def respond(r):calls.append(1);return httpx.Response(429,json={})
            b=CacheBudget(d/'cache',d/'ledger','fixed',allow_network=True,client=httpx.Client(transport=httpx.MockTransport(respond)))
            req=httpx.Request('POST','https://fake.invalid/embeddings',json={'model':'text-embedding-v4','input':['test'],'dimensions':1024})
            for _ in range(2):
                with self.assertRaises(Halt):b.request(req,'text-embedding-v4',str(req.url))
            self.assertEqual(len(calls),1)
    def test_reservation_blocks_before_network(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);b=CacheBudget(d/'cache',d/'ledger','fixed',allow_network=True);b.total=.4999
            req=httpx.Request('POST','https://fake.invalid/chat/completions',json={'model':'gpt-4o-mini','messages':[],'max_tokens':1200})
            with self.assertRaises(Halt):b.request(req,'gpt-4o-mini',str(req.url))
            self.assertEqual(b.calls,0)
    def test_invalidation(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);b=CacheBudget(d/'cache',d/'ledger','fixed')
            self.assertEqual(b.artifact('facts',['model','prompt','text'],lambda:[1]),[1])
            self.assertEqual(b.artifact('facts',['model','prompt','different'],lambda:[2]),[2])

if __name__=='__main__':unittest.main()
