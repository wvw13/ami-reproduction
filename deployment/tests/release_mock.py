"""Free isolated candidate HTTP regression. No real secrets/provider/live instance."""
import concurrent.futures,json,os,secrets,shutil,sqlite3,subprocess,sys,tempfile,urllib.error,urllib.request
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
checks=[]
def check(value,label):
 checks.append({'check':label,'pass':bool(value)})
 if not value:raise AssertionError(label)
with tempfile.TemporaryDirectory(prefix='ami-release-mock-') as directory:
 root=Path(directory)
 for name in ['app','reproduction','deployment']:
  shutil.copytree(REPO/name,root/name,ignore=shutil.ignore_patterns('__pycache__','private','data','cache','logs','run'))
 for name in ['data','cache','logs','run','private']:(root/'deployment'/name).mkdir(exist_ok=True)
 token=secrets.token_urlsafe(32)
 (root/'deployment/private/memory.env').write_text('MEMORY_SYSTEM_KEY='+token+'\n')
 env={k:v for k,v in os.environ.items() if not k.startswith(('AMI_','OPENAI_','DASHSCOPE_','MEMORY_SYSTEM_','NGROK_'))}
 env.update(PYTHONPATH=str(root),NO_PROXY='127.0.0.1,localhost',no_proxy='127.0.0.1,localhost')
 control=[sys.executable,str(root/'deployment/control.py')]
 def manage(action,port=None):
  cmd=control+[action,'--mock']+(['--port',str(port)] if port else [])
  p=subprocess.run(cmd,cwd=root,env=env,capture_output=True,text=True,timeout=45)
  check(p.returncode==0,action+' own isolated mock')
 def call(path,body=None,auth='correct'):
  h={'Content-Type':'application/json'}
  if auth!='none':h['Authorization']='Token '+(token if auth=='correct' else 'intentionally-invalid')
  req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=h)
  opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
  try:
   with opener.open(req,timeout=20) as r:return r.status,json.loads(r.read())
  except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
 def rows():
  with sqlite3.connect((root/'deployment/data/mock.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
   return db.execute('SELECT id,user_id,content FROM items ORDER BY id').fetchall()
 started=False
 try:
  manage('start');started=True
  state=json.loads((root/'deployment/run/mock.json').read_text());port=state['port'];base=f'http://127.0.0.1:{port}'
  check(port!=38563,'separate ephemeral port')
  p={'request_id':'release-fixture-001','user_id':'fixture-a','session_id':'fixture-session','messages':[{'role':'user','content':'My bicycle bell is silver.'}]}
  q={'query':'What color is my bicycle bell?','user_id':'fixture-a','top_k':100}
  check(call('/health',auth='none')==(200,{'status':'ok'}),'anonymous health')
  for endpoint,body in [('/add',p),('/search',q)]:
   for auth in ['none','wrong']:check(call(endpoint,body,auth)[0]==401,endpoint+' '+auth+'401')
  check(call('/add',p)==(200,dict(success=True,**{k:p[k] for k in ['request_id','user_id','session_id']})),'synchronous Add exactecho')
  saved=rows();status,result=call('/search',q)
  check(status==200 and any('silver' in x['content'] for x in result['data']),'immediate Search evidence')
  check(all(x['id'] and x['content'] for x in result['data']),'stable nonempty id/content')
  check(all(x[1].startswith('aml-local-ami-baseline-v1:') for x in saved),'same deployed namespace')
  for k in [0,1,100]:check(len(call('/search',dict(q,top_k=k))[1]['data'])<=k,'top_k='+str(k))
  check(call('/search',dict(q,options=['silver','red']))[0]==200,'optional options')
  check(call('/add',p)[0]==200 and rows()==saved,'duplicate idempotency')
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:statuses=list(pool.map(lambda _:call('/add',p)[0],range(4)))
  check(statuses==[200]*4 and rows()==saved,'concurrent duplicate idempotency')
  check(call('/add',dict(p,messages=[{'role':'user','content':'Changed.'}]))[0]==409,'changed payload409')
  check(call('/add',dict(p,user_id='fixture-b',messages=[{'role':'user','content':'My bicycle bell is bronze.'}]))[0]==200,'independent second user')
  check(all('silver' not in x['content'] for x in call('/search',dict(q,user_id='fixture-b'))[1]['data']),'user B isolation')
  check(all('bronze' not in x['content'] for x in call('/search',q)[1]['data']),'user A isolation')
  for field in p:check(call('/add',{k:v for k,v in p.items() if k!=field})[0]==422,'missing Add '+field)
  for field in q:check(call('/search',{k:v for k,v in q.items() if k!=field})[0]==422,'missing Search '+field)
  for bad in [dict(q,top_k=-1),dict(q,top_k='100'),dict(q,query='')]:check(call('/search',bad)[0]==422,'invalid Search422')
  saved=rows();before=call('/search',q)[1];manage('stop');started=False
  manage('start',port);started=True
  check(rows()==saved and call('/search',q)[1]==before,'restart persistence and stable IDs')
  check(call('/add',p)[0]==200 and rows()==saved,'restart idempotency')
  for dbname in ['mock.sqlite3','mock-contract.sqlite3']:
   with sqlite3.connect((root/'deployment/data'/dbname).as_uri()+'?mode=ro',uri=True) as db:check(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok',dbname+' integrity')
  check(not (root/'deployment/logs/cost.jsonl').exists(),'no real provider ledger')
 finally:
  if started:manage('stop')
print(json.dumps({'status':'ISOLATED_MOCK_PASS','checks':len(checks),'all_pass':all(x['pass'] for x in checks),'provider_calls':0,'live_service_contacted':False}))
