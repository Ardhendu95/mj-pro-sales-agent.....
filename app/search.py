import asyncio
from sqlalchemy import select
from .models import Document, Chunk, Audit, Plan, uid
from .settings import EMBED_MODEL
from .knowledge import chunks
from .gemini import embed, AIUnavailable

index_lock = asyncio.Lock()

def public_docs():
    return (Document.approved.is_(True), Document.active.is_(True), Document.confidential.is_(False))

async def reindex(db):
    if index_lock.locked(): raise AIUnavailable('Indexing is already running. Refresh its status shortly.')
    async with index_lock:
        docs = (await db.scalars(select(Document).where(*public_docs()))).all()
        completed = 0
        for doc in docs:
            await db.refresh(doc)
            if not doc.approved or not doc.active or doc.confidential: continue
            parts = chunks(doc.text)
            if len(parts) > 250: raise AIUnavailable('Split large documents into fewer than 250 passages before indexing.')
            generation = uid()
            vectors = []
            try:
                for offset in range(0, len(parts), 20):
                    # Recheck approval before every outbound batch.
                    await db.refresh(doc)
                    if not doc.approved or not doc.active or doc.confidential: break
                    vectors.extend(await embed(parts[offset:offset + 20]))
                await db.refresh(doc)
                if len(vectors) != len(parts) or not doc.approved or not doc.active or doc.confidential: continue
                for part, vector in zip(parts, vectors):
                    db.add(Chunk(document_id=doc.id, text=part, embedding=vector, generation=generation, model=EMBED_MODEL))
                doc.index_generation = generation
                doc.indexing_status = 'ready'
                db.add(Audit(document_id=doc.id, action='indexed', details={'chunks':len(parts),'model':EMBED_MODEL}))
                await db.commit()
                completed += 1
            except AIUnavailable:
                doc.indexing_status = 'refresh_failed' if doc.index_generation else 'failed'
                await db.commit()
                raise
        return completed

async def search(db, query):
    ready = await db.scalar(select(Document.id).where(*public_docs(), Document.index_generation != '').limit(1))
    if not ready: return []
    vector = (await embed([query[:2000]], 'RETRIEVAL_QUERY'))[0]
    distance = Chunk.embedding.cosine_distance(vector)
    rows = (await db.execute(select(Chunk, Document, distance.label('distance')).join(Document, Document.id == Chunk.document_id).where(*public_docs(), Chunk.generation == Document.index_generation, Chunk.model == EMBED_MODEL).order_by(distance).limit(5))).all()
    return [{'id':c.id, 'document_id':d.id, 'title':d.title, 'source':d.source, 'version':d.version, 'effective_date':d.effective_date, 'excerpt':c.text} for c,d,dist in rows if dist <= 0.55]

async def valid_sources(db, sources):
    valid = []
    for source in sources:
        if source.get('document_id'):
            doc = await db.get(Document, source['document_id'], populate_existing=True)
            if doc and doc.active and doc.approved and not doc.confidential: valid.append(source)
        else:
            plan = await db.get(Plan, source.get('id'), populate_existing=True)
            if plan and plan.active: valid.append(source)
    return valid
