"""Isolated offline review server. Never calls Google or opens the trial database."""
import asyncio
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['DATABASE_URL']='sqlite+aiosqlite:///./data/ui-review.db'
os.environ['GEMINI_API_KEY']=''
os.environ['GOOGLE_FREE_PROJECT_CONFIRMED']='false'
from app.security import password_hash
os.environ['ADMIN_PASSWORD_HASH']=password_hash('fictional-test-password')
from app.models import Base,engine
async def prepare():
    async with engine.begin() as c:await c.run_sync(Base.metadata.create_all)
asyncio.run(prepare())
import uvicorn
uvicorn.run('app.main:app',host='127.0.0.1',port=8012)
