"""Read private deployment profile before importing the unchanged AMI app."""
import os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
sys.path.insert(0, str(PROJECT))
from reproduction.serve import read_profile, clear_model_environment

def configure(mock=False):
    key = os.environ.get('MEMORY_SYSTEM_KEY', '')
    clear_model_environment()
    profile = read_profile(ROOT / ('profile.env' if mock else 'private/provider.env'))
    os.environ.update(profile)
    if not key:
        key = read_profile(ROOT / 'private/memory.env').get('MEMORY_SYSTEM_KEY', '')
    if not key:
        raise RuntimeError('MEMORY_SYSTEM_KEY is required')
    os.environ.update(AMI_AUTH_SCHEME='token', AMI_AUTH_TOKEN=key,
                     AMI_DB_PATH=str(ROOT / 'data' / ('mock.sqlite3' if mock else 'memory.sqlite3')),
                     AMI_REQUEST_LOG='', HF_HOME=str(ROOT / 'cache/hf'))
    if mock:
        os.environ.update(OPENAI_API_KEY='offline-fixture', AMI_EMBED_API_KEY='offline-fixture',
                          OPENAI_BASE_URL='http://offline.invalid/v1', AMI_EMBED_BASE_URL='http://offline.invalid/v1')
        from reproduction.serve import install_fakes
        install_fakes()
    return key
