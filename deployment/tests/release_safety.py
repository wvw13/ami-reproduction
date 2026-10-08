"""Pattern/history audit of publishable files only. Never reads private runtime files."""
import collections,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
files=git('ls-files','--cached','--others','--exclude-standard').decode().splitlines()
issues=[];legacy=[];blobs={};scopes=collections.Counter()
def forbidden(name):
 p=Path(name)
 return bool(set(p.parts)&{'private','data','cache','logs','run','.venv','artifacts'} or p.suffix in {'.db','.sqlite3','.jsonl','.log','.pem','.key','.tgz'} or name.endswith(('-wal','-shm')) or (p.name.startswith('.env') and not p.name.endswith('.example')))
def audit(name,data,scope):
 scopes[scope]+=1
 if forbidden(name):issues.append(dict(scope=scope,file=name,kind='forbidden_runtime_file'))
 if b'\x00' in data:issues.append(dict(scope=scope,file=name,kind='unexpected_binary'));return
 text=data.decode('utf-8',errors='replace')
 for number,line in enumerate(text.splitlines(),1):
  patterns=[('provider_key',r'\bsk-[A-Za-z0-9_-]{20,}'),('github_token',r'\b(?:ghp_|github_pat_)[A-Za-z0-9_]{25,}'),('private_key',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),('embedded_url_credentials',r'https?://[^\s/@:]+:[^\s/@]+@')]
  for kind,pattern in patterns:
   if re.search(pattern,line):issues.append(dict(scope=scope,file=name,line=number,kind=kind))
  # Literal key assignments only; do not mistake variable references for credentials.
  m=re.search(r'(?i)(?:api[_-]?key|authtoken|memory_system_key|auth_token)\s*[=:]\s*[\"\']?([^\s\"\',;\)]+)',line)
  if m:
   value=m.group(1)
   literal=bool(re.search(r'(?i)(?:api[_-]?key|authtoken|memory_system_key|auth_token)\s*[=:]\s*[\"\']',line)) or Path(name).name.startswith('.env') or name.endswith('.env.example')
   fixture=value in {'embedding-test-key','llm-only-secret'} or value.startswith(('fixture-','offline-','fake-','placeholder-','not-a-'))
   if literal and len(value)>=12 and not fixture and re.fullmatch(r'[A-Za-z0-9_./+-]+',value):
    issues.append(dict(scope=scope,file=name,line=number,kind='literal_credential_review'))
  if re.search(r'/(?:home|data1)/sp(?:/|\b)',line):legacy.append(dict(scope=scope,file=name,line=number,kind='machine_specific_path'))
for name in files:
 p=ROOT/name
 if p.is_symlink():issues.append(dict(scope='candidate',file=name,kind='symlink_review'));continue
 audit(name,p.read_bytes(),'candidate')
# Unique reachable committed blobs: includes parent branches and old tags.
for row in git('rev-list','--objects','--all').decode().splitlines():
 oid,_,name=row.partition(' ')
 if not name or git('cat-file','-t',oid).strip()!=b'blob':continue
 if oid in blobs:continue
 blobs[oid]=name;audit(name,git('cat-file','blob',oid),'history')
emails=git('log','--all','--format=%ae%x09%ce').decode().splitlines()
email_classes=collections.Counter('github_noreply' if 'noreply' in e else 'local_address' if '@localhost' in e else 'personal_email_review' for row in emails for e in row.split('\t'))
out=dict(pattern_audit_pass=not issues,findings=issues,legacy_machine_path_count=len(legacy),machine_paths_by_scope=dict(collections.Counter(x['scope'] for x in legacy)),legacy_machine_path_files=sorted(set(x['file'] for x in legacy)),scope_file_counts=dict(scopes),candidate_files=len(files),reachable_history_blobs=len(blobs),commit_email_categories=dict(email_classes),limitations='Pattern audit plus curated source review; no private files or actual keys were loaded. Existing public historical machine paths are recorded without rewriting history.')
print(json.dumps(out,indent=2))
sys.exit(int(bool(issues)))
