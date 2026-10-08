"""Persistent content cache and first-error, zero-retry RMB budget transport.

Only request JSON and validated response JSON are cached; never HTTP headers.
AMI prompts/preprocessing/ranking remain unchanged. Local cache is not publishable.
"""
import hashlib
import json
import math
from pathlib import Path
import threading
from datetime import datetime, timezone
import httpx
from .real_minimal import ALLOWED_RESPONSE_MODELS

VERSION = 'ami-baseline-cache-v1'

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

class Halt(RuntimeError):
    pass

class CacheBudget:
    def __init__(self, root, ledger, identity, *, allow_network=False, client=None):
        self.root, self.ledger, self.identity = Path(root), Path(ledger), identity
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.allow_network = allow_network
        self.client = client or httpx.Client(timeout=25, follow_redirects=False)
        self.context = {'stage':'startup','benchmark':'startup','source_id':'startup'}
        self.stopped = None
        self.total = 0.0
        self.calls = 0
        if self.ledger.exists():
            for line in self.ledger.read_text().splitlines():
                self.total += json.loads(line)['estimated_RMB_cost']

    def check(self):
        if self.stopped:
            raise Halt(self.stopped)

    def halt(self, reason):
        self.stopped = reason
        raise Halt(reason)

    def record(self, *, event, model='', input_tokens=0, output_tokens=0, embedding_tokens=0,
               cost=0.0, exact=True, key='', **extra):
        self.total += cost
        row = dict(timestamp=datetime.now(timezone.utc).isoformat(), **self.context,
                   event=event, model=model, input_tokens=input_tokens, output_tokens=output_tokens,
                   embedding_tokens=embedding_tokens, cache_hit=event=='HIT', estimated_RMB_cost=cost,
                   cumulative_RMB=round(self.total,10), usage_exact=exact, cache_key=key, **extra)
        with self.ledger.open('a') as f:
            f.write(json.dumps(row, sort_keys=True)+'\n')

    def artifact(self, kind, value, compute):
        with self.lock:
            self.check()
            key=digest([VERSION,self.identity,kind,value]);path=self.root/(key+'.json')
            if path.exists():
                self.record(event='HIT',key=key,cache_kind=kind)
                return json.loads(path.read_text())
            self.record(event='MISS',key=key,cache_kind=kind)
            result=compute()
            self.check()
            temporary=path.with_suffix('.tmp')
            temporary.write_text(json.dumps(result, ensure_ascii=False));temporary.replace(path)
            return result

    def request(self, request, model, endpoint):
        with self.lock:
            self.check()
            if request.method!='POST' or str(request.url)!=endpoint:
                self.halt('unexpected_provider_endpoint')
            payload=json.loads(request.content)
            if payload.get('model')!=model or request.headers.get('x-stainless-retry-count','0')!='0':
                self.halt('model_or_retry_mismatch')
            kind='embedding' if model=='text-embedding-v4' else 'llm'
            key=digest([VERSION,self.identity,endpoint,payload]);path=self.root/(key+'.json')
            if path.exists():
                self.record(event='HIT',model=model,key=key,cache_kind=kind)
                return httpx.Response(200,json=json.loads(path.read_text()),request=request)
            self.record(event='MISS',model=model,key=key,cache_kind=kind)
            if not self.allow_network:self.halt('cache_only_miss')
            # UTF-8 bytes + framing is deliberately conservative, not claimed token usage.
            upper_input=len(request.content)+1024
            upper_output=payload.get('max_tokens',0) if kind=='llm' else 0
            reserve=(upper_input*(.15 if kind=='llm' else .5)+upper_output*.6)/1e6
            if self.total+reserve>.50:self.halt('hard_budget_reservation_exceeded')
            self.calls+=1
            try:
                r=self.client.send(request,stream=False,follow_redirects=False);r.read()
            except Exception:
                self.record(event='API_CALL',model=model,cost=reserve,exact=False,key=key,status='network_error')
                self.halt('provider_network_error')
            try:body=r.json()
            except Exception:body={}
            usage=body.get('usage',{}) if isinstance(body,dict) else {}
            inp=usage.get('prompt_tokens',usage.get('input_tokens'))
            out=usage.get('completion_tokens',0)
            exact=isinstance(inp,int) and inp>=0 and isinstance(out,int) and out>=0
            inp=inp if exact else upper_input
            out=out if exact else upper_output
            cost=(inp*(.15 if kind=='llm' else .5)+(out*.6 if kind=='llm' else 0))/1e6
            self.record(event='API_CALL',model=model,input_tokens=inp if kind=='llm' else 0,
                        output_tokens=out if kind=='llm' else 0,embedding_tokens=inp if kind=='embedding' else 0,
                        cost=cost,exact=exact,key=key,http_status=r.status_code)
            if r.status_code!=200:self.halt('provider_http_'+str(r.status_code))
            if not isinstance(body,dict) or body.get('error') or body.get('model') not in ALLOWED_RESPONSE_MODELS[model]:
                self.halt('provider_model_or_response_mismatch')
            if kind=='llm':
                try:assert isinstance(body['choices'][0]['message']['content'],str) and body['choices'][0]['message']['content'].strip()
                except Exception:self.halt('llm_response_shape')
            else:
                try:
                    rows=body['data'];assert len(rows)==len(payload['input'])
                    assert sorted(x['index'] for x in rows)==list(range(len(rows)))
                    for row in rows:
                        v=row['embedding'];assert len(v)==payload['dimensions'] and any(v)
                        assert all(isinstance(x,(int,float)) and math.isfinite(x) for x in v)
                except Exception:self.halt('embedding_response_shape')
            temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(body));temporary.replace(path)
            return httpx.Response(200,json=body,request=request)

class CachedTransport(httpx.BaseTransport):
    def __init__(self,budget,model,endpoint):self.b,self.model,self.endpoint=budget,model,endpoint
    def handle_request(self,request):return self.b.request(request,self.model,self.endpoint)
