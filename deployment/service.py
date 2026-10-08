"""AML transport adapter; AMI algorithms/models/prompts are unchanged."""
import hashlib
import json
import sqlite3
import threading
from fastapi import FastAPI, Header, HTTPException
from pydantic import ConfigDict, Field, field_validator
from bootstrap import ROOT
from app import main as ami, store, config, llm

class Add(ami.AddRequest):
    model_config = ConfigDict(extra='allow', strict=True)
    @field_validator('request_id', 'user_id', 'session_id')
    @classmethod
    def nonblank(cls, value):
        if not value.strip(): raise ValueError('empty identifier')
        return value

class Search(ami.SearchRequest):
    model_config = ConfigDict(extra='allow', strict=True)
    top_k: int = Field(ge=0)
    @field_validator('query', 'user_id')
    @classmethod
    def nonblank(cls, value):
        if not value.strip(): raise ValueError('empty query or identifier')
        return value

app = FastAPI(title='ami_baseline_v1 AML local deployment', docs_url=None, redoc_url=None)
app.add_middleware(ami.AdmissionValve)
app.add_exception_handler(llm.UpstreamUnavailable, ami.upstream_unavailable)
lock = threading.RLock()
namespace = 'aml-local-ami-baseline-v1:'
ledger_path = ROOT / 'data' / ('mock-contract.sqlite3' if config.LLM_API_KEY == 'offline-fixture' else 'contract.sqlite3')

def auth(authorization, x_api_key):
    # Declared deployment scheme is Token, reject raw unprefixed secrets.
    import hmac
    if not authorization or not authorization.lower().startswith('token '):
        raise HTTPException(401, detail='invalid credentials')
    if not hmac.compare_digest(authorization[6:], config.AUTH_TOKEN):
        raise HTTPException(401, detail='invalid credentials')

@app.on_event('startup')
def startup():
    ami.startup()
    with sqlite3.connect(ledger_path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS payloads (user_id TEXT, request_id TEXT, digest TEXT NOT NULL, PRIMARY KEY(user_id,request_id))')

@app.get('/health')
def health():
    with sqlite3.connect(config.DB_PATH) as db: db.execute('SELECT 1 FROM requests LIMIT 1').fetchall()
    return {'status':'ok'}

@app.post('/add', response_model=ami.AddResponse)
def add(request:Add, authorization:str|None=Header(None), x_api_key:str|None=Header(None)):
    auth(authorization,x_api_key)
    body=request.model_dump(mode='json')
    digest=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    # Single worker, serialize reservation + AMI persistence; reserve before work
    # so a crash/retry cannot introduce a different payload for the same ID.
    with lock, sqlite3.connect(ledger_path) as db:
        row=db.execute('SELECT digest FROM payloads WHERE user_id=? AND request_id=?',(request.user_id,request.request_id)).fetchone()
        if row and row[0]!=digest: raise HTTPException(409,detail='request_id payload conflict')
        db.execute('INSERT OR IGNORE INTO payloads VALUES (?,?,?)',(request.user_id,request.request_id,digest));db.commit()
        internal=ami.AddRequest(**dict(body,user_id=namespace+request.user_id))
        ami.add(internal,authorization,None)
    return ami.AddResponse(success=True,request_id=request.request_id,user_id=request.user_id,session_id=request.session_id)

@app.post('/search')
def search(request:Search, authorization:str|None=Header(None), x_api_key:str|None=Header(None)):
    auth(authorization,x_api_key)
    return ami.search(ami.SearchRequest(**dict(request.model_dump(),user_id=namespace+request.user_id)),authorization,None)
