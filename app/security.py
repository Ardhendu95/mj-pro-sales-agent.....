import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import timedelta
from fastapi import HTTPException, Request
from sqlalchemy import select
from .models import AdminSession, Session, utcnow

def digest(text): return hashlib.sha256(text.encode()).hexdigest()
def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    value = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return salt + ':' + value

def password_valid(password):
    saved = os.getenv('ADMIN_PASSWORD_HASH', '')
    try: return hmac.compare_digest(password_hash(password, saved.split(':')[0]), saved)
    except (ValueError, TypeError): return False

async def require_admin(request: Request):
    async with Session() as db:
        row = await db.scalar(select(AdminSession).where(AdminSession.token_hash == digest(request.cookies.get('demo_admin', '')), AdminSession.active.is_(True), AdminSession.expires_at > utcnow()))
        if not row: raise HTTPException(401, 'Sign in to the sales workspace.')
        return row.id

attempts = defaultdict(deque)
def rate_limit(key, count, seconds=60):
    now = time.monotonic()
    for stale in list(attempts):
        if not attempts[stale] or attempts[stale][-1] < now - 3600: attempts.pop(stale, None)
    q = attempts[key]
    while q and q[0] <= now - seconds: q.popleft()
    if len(q) >= count: raise HTTPException(429, 'Too many requests. Wait a minute and try again.')
    q.append(now)
