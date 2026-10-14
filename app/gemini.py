import asyncio
import os
from datetime import timedelta
from google import genai
from google.genai import types
from sqlalchemy import select, func
from .models import Session, Usage, utcnow
from .settings import ai_ready, ai_reason, MODEL, EMBED_MODEL

class AIUnavailable(Exception):
    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable
call_lock = asyncio.Lock()

async def reserve(kind, model):
    if not ai_ready(): raise AIUnavailable(ai_reason())
    async with call_lock:
        async with Session() as db:
            total = await db.scalar(select(func.count()).select_from(Usage).where(Usage.created_at > utcnow() - timedelta(days=1)))
            if total >= int(os.getenv('MAX_DAILY_AI_CALLS', '100')):
                raise AIUnavailable('The demo daily request limit is reached. Try again tomorrow.')
            row = Usage(kind=kind, model=model, status='started')
            db.add(row)
            await db.commit()
            return row.id

async def finish(id, response=None, status='ok'):
    async with Session() as db:
        row = await db.get(Usage, id)
        row.status = status
        row.tokens = int(getattr(getattr(response, 'usage_metadata', None), 'total_token_count', 0) or 0)
        await db.commit()

async def _invoke_once(kind, contents, config=None):
    model = EMBED_MODEL if kind == 'embedding' else MODEL
    id = await reserve(kind, model)
    try:
        async with genai.Client(api_key=os.environ['GEMINI_API_KEY'], http_options=types.HttpOptions(timeout=25000, retry_options=types.HttpRetryOptions(attempts=1))).aio as client:
            if kind == 'embedding':
                response = await client.models.embed_content(model=model, contents=contents, config=config)
            else:
                response = await client.models.generate_content(model=model, contents=contents, config=config)
        await finish(id, response)
        return response
    except asyncio.CancelledError:
        await finish(id, status='cancelled')
        raise
    except Exception as exc:
        code = getattr(exc, 'code', None)
        await finish(id, status='quota' if code == 429 else 'failed')
        if code == 429: raise AIUnavailable('Google’s free quota is exhausted. Wait and retry; no paid fallback is enabled.') from None
        if code in {500, 502, 503, 504}: raise AIUnavailable('Google is temporarily busy or unavailable. Wait a moment and retry your question.', retryable=True) from None
        if code == 404: raise AIUnavailable('This Google account cannot access the selected model. Check the configured model before retrying.') from None
        raise AIUnavailable('Gemini could not answer. Check the API key and model access, or retry later.') from None

async def invoke(kind, contents, config=None):
    for attempt in range(2):
        try: return await _invoke_once(kind, contents, config)
        except AIUnavailable as exc:
            if attempt or not exc.retryable: raise
            await asyncio.sleep(0.75)

async def embed(texts, task='RETRIEVAL_DOCUMENT'):
    response = await invoke('embedding', texts, types.EmbedContentConfig(output_dimensionality=768, task_type=task))
    values = [e.values for e in response.embeddings or []]
    if len(values) != len(texts) or any(len(v) != 768 for v in values): raise AIUnavailable('Gemini returned incomplete search data. Re-index the document.')
    return values
