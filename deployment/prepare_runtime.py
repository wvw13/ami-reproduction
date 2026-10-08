"""Create only missing local runtime directories; never reset existing data/state."""
import argparse,json,os
from pathlib import Path
R=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--mock',action='store_true');a=p.parse_args()
os.umask(0o077)
for name in ['private','data','cache','logs','run','run/windows-real-e2e']:
 (R/name).mkdir(parents=True,exist_ok=True)
if a.mock:
 # Public synthetic fixture only. Never create or read a real Memory System Key.
 target=R/'private/memory.env'
 if not target.exists():
  with target.open('x') as f:f.write('MEMORY_SYSTEM_KEY=offline-fixture-token-not-a-credential\n')
print(json.dumps({'directories_ready':True,'mock_fixture_requested':a.mock,'existing_state_preserved':True}))
