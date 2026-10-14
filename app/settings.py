import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://demo:demo-local-only@127.0.0.1:55432/mjpro_demo')
MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite')
EMBED_MODEL = os.getenv('GEMINI_EMBED_MODEL', 'gemini-embedding-001')
SOURCE_URL = 'https://eprocurement.mjunction.in/mjproconnect'
REVIEW_DATE = '2026-10-11'

def ai_ready():
    return bool(os.getenv('GEMINI_API_KEY')) and os.getenv('GOOGLE_FREE_PROJECT_CONFIRMED') == 'true'

def ai_reason():
    if not os.getenv('GEMINI_API_KEY'): return 'Add a Gemini API key in the local .env file.'
    if os.getenv('GOOGLE_FREE_PROJECT_CONFIRMED') != 'true': return 'Confirm that Google project billing is disabled in the local setup.'
    return 'Configured; connection has not been verified by this status check.'
