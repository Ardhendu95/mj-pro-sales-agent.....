"""Offline behavior checks. Mocked AI responses are never served by the demo."""
import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

# A unique file preserves test records and never opens the legacy trial database.
TEST_FILE = Path('data') / ('checks-' + uuid4().hex + '.db')
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///' + TEST_FILE.as_posix()
os.environ['GEMINI_API_KEY'] = ''
os.environ['GOOGLE_FREE_PROJECT_CONFIRMED'] = 'false'
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.models import Base, engine, Session, Document, Chunk, Plan
from app.security import password_hash, attempts
os.environ['ADMIN_PASSWORD_HASH'] = password_hash('fictional-test-password')
from app.demo import app
import app.demo as demo
import app.conversation_agent as agent
import app.search as retrieval
from app.gemini import AIUnavailable

@pytest.fixture(scope='module')
def client():
    async def create():
        async with engine.begin() as c: await c.run_sync(Base.metadata.create_all)
    asyncio.run(create())
    with TestClient(app) as c: yield c

@pytest.fixture(autouse=True)
def clean_rate_limits(): attempts.clear()

def login(c):
    r=c.post('/api/admin/login',json={'username':'admin','password':'fictional-test-password'})
    assert r.status_code==200
    assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=strict' in r.headers['set-cookie']

def new(c):
    r=c.post('/api/conversations').json()
    return r['id'],{'X-Session-Token':r['token']}

def lead():
    return {'submission_id':str(uuid4()),'name':'Demo Visitor','company':'Example Manufacturing','category':'Steel','buyers':'Industrial buyers','email':'visitor@example.invalid','callback':'Tomorrow afternoon','consent':True}

def test_callback_consent_idempotency_and_login(client):
    login(client)
    cid,h=new(client); fields=lead()
    assert client.post(f'/api/conversations/{cid}/lead',headers=h,json={**fields,'consent':False}).status_code==422
    for _ in range(2): assert client.post(f'/api/conversations/{cid}/lead',headers=h,json=fields).status_code==200
    d=client.get('/api/admin/dashboard').json()
    row=next(c for c in d['conversations'] if c['id']==cid)
    assert row['lead']['details']['company']==fields['company']
    assert row['lead']['consent_at'] and row['summary_kind']=='form'
    assert row['interest']=='high' and d['counts']['leads']==1 and d['counts']['plan_enquiries']==0
    assert client.patch('/api/admin/tickets/'+row['ticket']['id'],json={'status':'resolved'}).json()['status']=='resolved'
    assert client.patch('/api/admin/tickets/'+row['ticket']['id'],json={'status':'invented'}).status_code==422
    assert client.post('/api/admin/logout').status_code==200
    assert client.get('/api/admin/dashboard').status_code==401

def test_visitor_isolation_and_cross_site_protection(client):
    cid,h=new(client);_,other=new(client)
    assert client.get(f'/api/conversations/{cid}',headers=other).status_code==404
    assert client.get(f'/api/conversations/{cid}').status_code==404
    assert client.post('/api/conversations',headers={'Origin':'https://untrusted.invalid'}).status_code==403
    assert client.get('/api/admin/documents').status_code==401
    assert client.post(f'/api/conversations/{cid}/messages',headers=h,json={'message':'   ','request_id':str(uuid4())}).status_code==422

def test_ai_failure_preserves_message_and_retry_once(client,monkeypatch):
    cid,h=new(client);body={'message':'What can I subscribe to?','request_id':str(uuid4())}
    r=client.post(f'/api/conversations/{cid}/messages',headers=h,json=body)
    assert r.status_code==503 and 'API key' in r.json()['detail']
    assert len(client.get(f'/api/conversations/{cid}',headers=h).json()['messages'])==2
    async def supported(*args):
        return {'text':'Offline fixture answer','sources':[],'plans':[],'qualification':{'category':'Steel'},'actions':[],'missing_information':False,'ai_generated':True}
    monkeypatch.setattr(demo,'answer',supported)
    for _ in range(2): assert client.post(f'/api/conversations/{cid}/messages',headers=h,json=body).status_code==200
    messages=client.get(f'/api/conversations/{cid}',headers=h).json()['messages']
    assert [m['role'] for m in messages]==['assistant','user','assistant']
    assert client.get(f'/api/conversations/{cid}',headers=h).json()['qualification']=={'category':'Steel'}

def test_version_approval_and_embedding_privacy(client,monkeypatch):
    login(client)
    source={'source':'https://example.invalid/public','effective_date':'2026-10-11'}
    original=client.post('/api/admin/documents',json={**source,'title':'Original','text':'Approved public facts for indexing.','approved':True}).json()
    draft=client.post('/api/admin/documents',json={**source,'title':'Draft','text':'Unapproved content must not leave.','replaces':original['id']}).json()
    confidential=client.post('/api/admin/documents',json={**source,'title':'Internal','text':'Confidential content must not leave.','approved':True,'confidential':True}).json()
    sent=[]
    async def fake_embed(texts,*args):
        sent.extend(texts);return [[1.0]+[0.0]*767 for _ in texts]
    monkeypatch.setattr(retrieval,'embed',fake_embed)
    assert client.post('/api/admin/reindex').status_code==200
    assert not any('must not leave' in t for t in sent)
    state={'approved':True,'active':True,'confidential':False}
    assert client.patch('/api/admin/documents/'+draft['id'],json=state).status_code==200
    docs=client.get('/api/admin/documents').json()
    assert not next(d for d in docs if d['id']==original['id'])['active']
    assert next(d for d in docs if d['id']==draft['id'])['version']==2
    async def check():
        async with Session() as db:
            assert await retrieval.valid_sources(db,[{'id':'chunk','document_id':original['id']}])==[]
            assert await retrieval.valid_sources(db,[{'id':'chunk','document_id':confidential['id']}])==[]
    asyncio.run(check())

def test_grounded_reply_rejects_fake_sources_numbers_and_qualification(client,monkeypatch):
    async def fake_search(*args): return [{'id':'evidence','title':'Fixture','document_id':None,'source':'https://example.invalid','excerpt':'The subscription costs INR 15,000 for 6 months.'}]
    async def unchanged(db,sources): return sources
    step=0
    async def fake_invoke(kind,*args):
        nonlocal step
        step+=1
        if kind=='chat_tool':
            if step==1:return SimpleNamespace(function_calls=[SimpleNamespace(name='search_knowledge',args={'query':'cost'})],candidates=[SimpleNamespace(content=SimpleNamespace())])
            return SimpleNamespace(function_calls=[])
        return SimpleNamespace(text=json.dumps({'claims':[{'text':'INR 1 for 6 months','source_id':'evidence','evidence':'The subscription costs INR 15,000 for 6 months.'},{'text':'A guaranteed order','source_id':'invented','evidence':'Guaranteed'}],'qualification':{'company':'Invented Company'},'missing_information':True}))
    monkeypatch.setattr(agent,'search',fake_search);monkeypatch.setattr(agent,'valid_sources',unchanged);monkeypatch.setattr(agent,'invoke',fake_invoke)
    async def check():
        async with Session() as db: return await agent.answer(db,'cost',[],{})
    result=asyncio.run(check())
    # A changed numeric value must not pass by matching a substring of 15,000.
    assert 'INR 1 ' not in result['text'] and result['sources']==[] and result['qualification']=={}

@pytest.mark.parametrize('qualification,previous,expected', [
    ({}, '', 'What products or services does your company offer?'),
    ({}, 'What products or services does your company offer?', None),
    ({'category':'industrial fasteners'}, '', 'What kinds of buyers would you like to reach?'),
    ({'category':'industrial fasteners'}, 'What kinds of buyers would you like to reach?', None),
])
def test_qualification_follow_up_keeps_answer_without_repeating(client, monkeypatch, qualification, previous, expected):
    evidence = 'Suppliers can publish their profiles.'
    async def fake_search(*args):
        return [{'id':'evidence', 'title':'Fixture', 'excerpt':evidence}]
    async def unchanged(db, sources): return sources
    async def fake_invoke(kind, *args):
        if kind == 'chat_tool':
            return SimpleNamespace(function_calls=[SimpleNamespace(name='search_knowledge', args={})], candidates=[SimpleNamespace(content=SimpleNamespace())])
        return SimpleNamespace(text=json.dumps({'claims':[{'text':evidence, 'source_id':'evidence', 'evidence':evidence}]}))
    monkeypatch.setattr(agent, 'search', fake_search)
    monkeypatch.setattr(agent, 'valid_sources', unchanged)
    monkeypatch.setattr(agent, 'invoke', fake_invoke)
    history = [SimpleNamespace(id='previous', role='assistant', text=previous)] if previous else []
    async def check():
        async with Session() as db: return await agent.answer(db, 'How does it work?', history, qualification)
    result = asyncio.run(check())
    assert result['text'] == evidence + ('\n\n' + expected if expected else '')
    assert result['qualification'] == qualification and result['sources'][0]['id'] == 'evidence'


def test_import_errors_and_ui(client):
    login(client)
    assert client.post('/api/admin/parse',files={'file':('sample.md',b'Approved public text')}).json()['text']=='Approved public text'
    assert client.post('/api/admin/parse',files={'file':('bad.exe',b'bad')}).status_code==422
    assert client.post('/api/admin/parse',files={'file':('empty.pdf',b'bad')}).status_code==422
    for path in ['/','/widget','/admin','/assets/demo.css','/assets/app.js','/assets/embed.js']:
        assert client.get(path).status_code==200
    plans=client.get('/api/plans').json()
    assert [(p['amount_minor'],p['months']) for p in plans]==[(1500000,6),(2500000,12)]
    assert client.get('/api/health').json()['ai_configured'] is False

def test_summary_failure_preserves_callback(client,monkeypatch):
    login(client);cid,h=new(client)
    async def supported(*args):return {'text':'Offline fixture','sources':[],'plans':[],'qualification':{},'actions':[],'missing_information':False,'ai_generated':True}
    async def failed(*args):raise AIUnavailable('Offline failure fixture')
    monkeypatch.setattr(demo,'answer',supported)
    assert client.post(f'/api/conversations/{cid}/messages',headers=h,json={'message':'We supply valves.','request_id':str(uuid4())}).status_code==200
    monkeypatch.setattr(demo,'ai_ready',lambda:True);monkeypatch.setattr(demo,'summarize',failed)
    assert client.post(f'/api/conversations/{cid}/lead',headers=h,json=lead()).status_code==200
    row=next(c for c in client.get('/api/admin/dashboard').json()['conversations'] if c['id']==cid)
    assert row['summary_kind']=='form_ai_unavailable' and 'Steel' in row['summary']
    assert len(client.get(f'/api/conversations/{cid}',headers=h).json()['messages'])==3

def test_failed_reindex_preserves_previous_generation(client,monkeypatch):
    login(client)
    before=client.get('/api/admin/documents').json()
    indexed=next(d for d in reversed(before) if d['active'] and d['approved'] and not d['confidential'] and d['index_generation'])
    async def failed(*args):raise AIUnavailable('Offline quota fixture')
    monkeypatch.setattr(retrieval,'embed',failed)
    assert client.post('/api/admin/reindex').status_code==503
    after=next(d for d in client.get('/api/admin/documents').json() if d['id']==indexed['id'])
    assert after['index_generation']==indexed['index_generation'] and after['indexing_status']=='refresh_failed'

def test_daily_request_cap_blocks_before_google(client,monkeypatch):
    from app.gemini import reserve
    monkeypatch.setenv('GEMINI_API_KEY','fictional-not-a-live-key')
    monkeypatch.setenv('GOOGLE_FREE_PROJECT_CONFIRMED','true')
    monkeypatch.setenv('MAX_DAILY_AI_CALLS','0')
    with pytest.raises(AIUnavailable,match='daily request limit'):asyncio.run(reserve('connection_check','fictional-model'))

def test_transient_google_error_retries_once(monkeypatch):
    import app.gemini as gemini
    calls=[]
    async def once(*args):
        calls.append(1)
        if len(calls)==1:raise AIUnavailable('Busy fixture',retryable=True)
        return 'successful fixture'
    monkeypatch.setattr(gemini,'_invoke_once',once)
    assert asyncio.run(gemini.invoke('chat_answer','fixture'))=='successful fixture'
    assert len(calls)==2

def test_quota_errors_are_not_retried(monkeypatch):
    import app.gemini as gemini
    calls=[]
    async def once(*args):calls.append(1);raise AIUnavailable('Quota fixture')
    monkeypatch.setattr(gemini,'_invoke_once',once)
    with pytest.raises(AIUnavailable,match='Quota fixture'):asyncio.run(gemini.invoke('chat_answer','fixture'))
    assert len(calls)==1
