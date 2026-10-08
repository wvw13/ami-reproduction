import argparse
import logging
import threading
import httpx
from bootstrap import ROOT, configure
p=argparse.ArgumentParser();p.add_argument('--mock',action='store_true');p.add_argument('--port',type=int,required=True);args=p.parse_args()
configure(args.mock)
if not args.mock:
    from reproduction.baseline_cache import CacheBudget, CachedTransport
    class LocalBudget(CacheBudget):
        def __init__(self,*a,**kw):
            super().__init__(*a,**kw)
            if (ROOT/'logs/provider-stop.json').exists():
                self.stopped='persisted_provider_stop'
        def halt(self,reason):
            import json
            (ROOT/'logs/provider-stop.json').write_text(json.dumps({'reason':reason}))
            return super().halt(reason)
        def request(self, request, model, endpoint):
            import json
            with self.lock:
                self.check()
                payload=json.loads(request.content)
                upper_input=len(request.content)+1024
                reserve=(upper_input*(.5 if model=='text-embedding-v4' else .15)+payload.get('max_tokens',0)*.6)/1e6
                # Applies also to cached calls, conservatively. No retries.
                if self.total+reserve > .05: self.halt('local_RMB_0.05_budget_limit')
                return super().request(request,model,endpoint)
    from app import config, embed, llm, store
    from openai import OpenAI
    from phase_budget_guard import restrict_budget
    PhaseBudget = restrict_budget(LocalBudget, ROOT)
    # Startup warm-up must be cache-only: recovery is not a paid probe.
    budget=PhaseBudget(ROOT/'cache/provider',ROOT/'logs/cost.jsonl','deployment-ami-baseline-v1',allow_network=False)
    lc=OpenAI(api_key=config.LLM_API_KEY,base_url=config.LLM_BASE_URL,max_retries=0,http_client=httpx.Client(transport=CachedTransport(budget,'gpt-4o-mini',config.LLM_BASE_URL.rstrip('/')+'/chat/completions')))
    ec=OpenAI(api_key=config.EMBED_API_KEY,base_url=config.EMBED_BASE_URL,max_retries=0,http_client=httpx.Client(transport=CachedTransport(budget,'text-embedding-v4',config.EMBED_BASE_URL.rstrip('/')+'/embeddings')))
    llm._get_client=lambda:lc
    gate=threading.BoundedSemaphore(config.EMBED_CONCURRENCY)
    embed._get_remote_client=lambda:(ec,gate)
    original=store.add
    def guarded_add(*a,**kw):
        with budget.lock:
            budget.check()
            return original(*a,**kw)
    store.add=guarded_add
    # Upstream may swallow provider errors; never report partial Add/Search success.
    import service
    @service.app.on_event('startup')
    def enable_provider_after_cached_startup():
        budget.check()
        budget.allow_network=True
    @service.app.middleware('http')
    async def budget_guard(request,call_next):
        from fastapi.responses import JSONResponse
        if request.url.path not in ('/add','/search'):
            return await call_next(request)
        try:
            service.auth(request.headers.get('authorization'), None)
        except Exception:
            return JSONResponse({'detail':'invalid credentials'},status_code=401)
        if budget.stopped:
            return JSONResponse({'detail':'provider unavailable or budget stopped'},status_code=503)
        try:
            result=await call_next(request)
        except Exception:
            return JSONResponse({'detail':'provider or storage unavailable'},status_code=503)
        if budget.stopped:
            return JSONResponse({'detail':'provider unavailable or budget stopped'},status_code=503)
        return result

else:
    import service
# Never log provider bodies/headers/error strings (which may contain credentials).
logging.getLogger('ami.llm').disabled=True
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.CRITICAL)
import uvicorn
uvicorn.run(service.app,host='127.0.0.1',port=args.port,workers=1,access_log=False)
