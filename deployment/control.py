import argparse,json,os,signal,socket,subprocess,sys,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PYTHON=Path(sys.executable)
p=argparse.ArgumentParser();p.add_argument('action',choices=['start','stop','check']);p.add_argument('--mock',action='store_true');p.add_argument('--port',type=int,default=0);a=p.parse_args()
state=ROOT/'run'/('mock.json' if a.mock else 'service.json')
def identity(pid):
 try:return Path(f'/proc/{pid}/stat').read_text().split()[21]
 except OSError:return None
def live(s):
 try:
  stat=Path(f"/proc/{s['pid']}/stat").read_text().split()
  return stat[2]!='Z' and stat[21]==s['start_ticks']
 except OSError:return False
def health(port):
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with opener.open(f'http://127.0.0.1:{port}/health',timeout=2) as r:return r.status==200
s=json.loads(state.read_text()) if state.exists() else None
if a.action=='stop':
 if s and live(s):
  os.kill(s['pid'],signal.SIGTERM)
  for _ in range(100):
   if not live(s):break
   time.sleep(.1)
 print('deployment stop requested')
elif a.action=='check':
 if not s or not live(s) or not health(s['port']):sys.exit('deployment unavailable')
 print(json.dumps({'status':'ok','pid':s['pid'],'bind':'127.0.0.1','port':s['port']}))
else:
 if s and live(s):sys.exit('deployment already running')
 with socket.socket() as probe:
  probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
  probe.bind(('127.0.0.1',a.port or (s['port'] if s else 0)));port=probe.getsockname()[1]
 env={k:v for k,v in os.environ.items() if not k.startswith(('AMI_','OPENAI_','DASHSCOPE_'))}
 env.update(NO_PROXY='127.0.0.1,localhost',no_proxy='127.0.0.1,localhost')
 command=[str(PYTHON),str(ROOT/'run_service.py'),'--port',str(port)]+(['--mock'] if a.mock else [])
 with (ROOT/'logs'/('mock-service.log' if a.mock else 'service.log')).open('a') as log:
  proc=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
 state.write_text(json.dumps({'pid':proc.pid,'port':port,'start_ticks':identity(proc.pid),'command':command},indent=2))
 for _ in range(300):
  if proc.poll() is not None:sys.exit('deployment startup failed; inspect sanitized log')
  try:
   if health(port):print(f'RUNNING http://127.0.0.1:{port} pid={proc.pid}');break
  except OSError:pass
  time.sleep(.1)
 else:proc.terminate();sys.exit('startup timeout')
