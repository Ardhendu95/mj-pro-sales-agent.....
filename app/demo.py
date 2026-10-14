import asyncio
import json
import os
import secrets
from contextlib import asynccontextmanager
from datetime import timedelta, date
from typing import Literal
from uuid import UUID
from fastapi import FastAPI, Depends, Header, HTTPException, UploadFile, File, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select, func, text
from .settings import ROOT, MODEL, ai_ready, ai_reason
from .models import Session, engine, Conversation, Message, Lead, Ticket, Document, Audit, Plan, Usage, Unanswered, AdminSession, utcnow
from .security import digest, password_valid, require_admin, rate_limit
from .conversation_agent import answer, plans, summarize, WELCOME
from .gemini import AIUnavailable, invoke
from .search import reindex
from .seed import seed
from .knowledge import parse_file

locks = {}
@asynccontextmanager
async def lifespan(app):
    async with Session() as db:
        await db.execute(text('SELECT 1'))
        await seed(db)
    yield
    await engine.dispose()

app = FastAPI(title='mjPROConnect demonstration', lifespan=lifespan)

@app.middleware('http')
async def protection(request, call_next):
    if request.method not in {'GET','HEAD','OPTIONS'}:
        if request.headers.get('origin') and request.headers['origin'] != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail':'Open the demonstration on its own address.'},status_code=403)
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail':'Cross-site requests are blocked.'},status_code=403)
        if int(request.headers.get('content-length','0')) > 5_200_000:
            return JSONResponse({'detail':'Upload a file smaller than 5 MB.'},status_code=413)
    response = await call_next(request)
    response.headers.update({'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'"})
    return response

@app.exception_handler(AIUnavailable)
async def ai_error(request, exc): return JSONResponse({'detail':str(exc),'code':'ai_unavailable','actions':['retry','callback']},status_code=503)

async def db_session():
    async with Session() as db: yield db

def serialize(row):
    return {c.name:(getattr(row,c.name).isoformat() if hasattr(getattr(row,c.name),'isoformat') else getattr(row,c.name)) for c in row.__table__.columns if c.name not in {'token_hash','embedding'}}

async def own(db,cid,token):
    row = await db.get(Conversation,cid)
    if not row or not secrets.compare_digest(row.token_hash,digest(token)): raise HTTPException(404,'Conversation unavailable. Start a new chat.')
    return row

class Login(BaseModel):
    username: str = Field(max_length=100)
    password: str = Field(max_length=200)
class ChatInput(BaseModel):
    message: str = Field(min_length=1,max_length=2000)
    request_id: UUID
    @field_validator('message')
    @classmethod
    def clean(cls,v):
        if not v.strip(): raise ValueError('Enter a message.')
        return v.strip()
class LeadInput(BaseModel):
    submission_id: UUID
    name: str = Field(min_length=1,max_length=100)
    company: str = Field(min_length=1,max_length=150)
    category: str = Field(min_length=1,max_length=200)
    buyers: str = Field(default='',max_length=300)
    experience: str = Field(default='',max_length=300)
    email: str = Field(default='',max_length=200)
    phone: str = Field(default='',max_length=30)
    callback: str = Field(default='',max_length=200)
    consent: bool
    @model_validator(mode='after')
    def valid(self):
        import re
        if not self.consent: raise ValueError('Consent is required.')
        if not all(v.strip() for v in [self.name,self.company,self.category]): raise ValueError('Fill in the required fields.')
        if not self.email and not self.phone: raise ValueError('Enter an email or phone number.')
        if self.email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',self.email): raise ValueError('Enter a valid email.')
        if self.phone and not re.fullmatch(r'\+?[\d ()-]{7,30}',self.phone): raise ValueError('Enter a valid phone number.')
        return self
class DocInput(BaseModel):
    title: str = Field(min_length=1,max_length=200)
    text: str = Field(min_length=10,max_length=300000)
    source: str = Field(min_length=1,max_length=500)
    effective_date: date
    approved: bool = False
    confidential: bool = False
    replaces: str | None = None
class DocState(BaseModel):
    approved: bool
    confidential: bool
    active: bool
class StatusInput(BaseModel): status: Literal['pending','in_progress','resolved']

@app.get('/api/health')
async def health(db=Depends(db_session)):
    await db.execute(text('SELECT 1'))
    ready = await db.scalar(select(func.count()).select_from(Document).where(Document.active.is_(True),Document.approved.is_(True),Document.confidential.is_(False),Document.index_generation!=''))
    return {'status':'ok','mode':'gemini','model':MODEL,'ai_configured':ai_ready(),'ai_message':ai_reason(),'storage':engine.dialect.name,'indexed_documents':ready,'free_project_confirmation':os.getenv('GOOGLE_FREE_PROJECT_CONFIRMED')=='true','admin_configured':bool(os.getenv('ADMIN_PASSWORD_HASH'))}

@app.post('/api/admin/login')
async def login(body:Login,request:Request,response:Response,db=Depends(db_session)):
    rate_limit('login:'+request.client.host,5)
    if not secrets.compare_digest(body.username,os.getenv('ADMIN_USERNAME','admin')) or not await asyncio.to_thread(password_valid,body.password): raise HTTPException(401,'Check your username and password.')
    token=secrets.token_urlsafe(32)
    db.add(AdminSession(token_hash=digest(token),expires_at=utcnow()+timedelta(hours=8)))
    await db.commit()
    response.set_cookie('demo_admin',token,httponly=True,samesite='strict',secure=request.url.scheme=='https',max_age=28800,path='/api/admin')
    return {'signed_in':True}

@app.post('/api/admin/logout')
async def logout(response:Response,sid=Depends(require_admin),db=Depends(db_session)):
    row=await db.get(AdminSession,sid)
    row.active=False
    await db.commit()
    response.delete_cookie('demo_admin',path='/api/admin')
    return {'signed_out':True}

@app.get('/api/plans')
async def public_plans(db=Depends(db_session)): return await plans(db)

@app.post('/api/conversations',status_code=201)
async def create(request:Request,db=Depends(db_session)):
    rate_limit('new:'+request.client.host,20)
    token=secrets.token_urlsafe(32)
    c=Conversation(token_hash=digest(token));db.add(c);await db.flush()
    db.add(Message(conversation_id=c.id,role='assistant',text=WELCOME,payload={'ai_generated':False}))
    await db.commit()
    return {'id':c.id,'token':token,'message':WELCOME}

@app.get('/api/conversations/{cid}')
async def get_conversation(cid:str,x_session_token:str=Header(default=''),db=Depends(db_session)):
    c=await own(db,cid,x_session_token)
    rows=(await db.scalars(select(Message).where(Message.conversation_id==cid).order_by(Message.created_at,Message.id))).all()
    saved=await db.scalar(select(Lead.id).where(Lead.conversation_id==cid))
    return {'id':cid,'qualification':c.qualification,'callback_saved':bool(saved),'messages':[{'id':m.id,'role':m.role,'text':m.text,'request_id':m.request_id,**m.payload} for m in rows]}

@app.post('/api/conversations/{cid}/messages')
async def send(cid:str,body:ChatInput,x_session_token:str=Header(default=''),db=Depends(db_session)):
    c=await own(db,cid,x_session_token)
    rate_limit('chat:'+cid,12)
    lock=locks.setdefault(cid,asyncio.Lock())
    if lock.locked(): raise HTTPException(429,'Wait for the current reply.')
    try:
        async with lock:
            await db.refresh(c,with_for_update=True)
            rid=str(body.request_id)
            prior=await db.scalar(select(Message).where(Message.conversation_id==cid,Message.role=='assistant',Message.request_id==rid))
            if prior: return {'text':prior.text,**prior.payload}
            history=(await db.scalars(select(Message).where(Message.conversation_id==cid).order_by(Message.created_at))).all()
            if len(history)>160: raise HTTPException(429,'Start a new conversation to continue.')
            user_message=await db.scalar(select(Message).where(Message.conversation_id==cid,Message.role=='user',Message.request_id==rid))
            if user_message and user_message.text!=body.message: raise HTTPException(409,'Retry the original message or start a new request.')
            if not user_message:
                user_message=Message(conversation_id=cid,role='user',text=body.message,request_id=rid)
                db.add(user_message);await db.commit()
            # Every failure preserves the visitor message; retry reuses its request id.
            result=await asyncio.wait_for(answer(db,body.message,history,c.qualification),timeout=100)
            c.qualification=result['qualification']
            if result['plans']:
                c.interest='considering';c.reasons=['Asked about subscription options']
            db.add(Message(conversation_id=cid,role='assistant',text=result['text'],payload={k:v for k,v in result.items() if k!='text'},request_id=rid))
            if result['missing_information']: db.add(Unanswered(conversation_id=cid,question=body.message))
            await db.commit()
            return result
    except asyncio.TimeoutError: raise AIUnavailable('Gemini took too long. Retry your message or request a callback.')
    finally: locks.pop(cid,None)

@app.post('/api/conversations/{cid}/lead')
async def capture(cid:str,body:LeadInput,x_session_token:str=Header(default=''),db=Depends(db_session)):
    c=await own(db,cid,x_session_token)
    await db.refresh(c,with_for_update=True)
    lead=await db.scalar(select(Lead).where(Lead.conversation_id==cid))
    duplicate=await db.scalar(select(Lead).where(Lead.submission_id==str(body.submission_id)))
    if duplicate and duplicate.conversation_id!=cid: raise HTTPException(409,'Use a new submission identifier.')
    if lead: return {'saved':True,'message':'Your callback request is already in the local sales queue.'}
    details=body.model_dump(exclude={'submission_id','consent'})
    db.add(Lead(conversation_id=cid,details=details,submission_id=str(body.submission_id),consent_text='I agree to save these details in this local demo for sales follow-up.'))
    db.add(Ticket(conversation_id=cid))
    c.interest='high';c.reasons=['Explicit callback request with consent']
    c.summary=f"{body.company} supplies {body.category}. Target buyers: {body.buyers or 'Not provided'}. Callback preference: {body.callback or 'Not provided'}. Next action: review callback request."
    c.summary_kind='form';c.summary_sources=[{'source':'consented_callback_form','submission_id':str(body.submission_id)}]
    await db.commit()
    history=(await db.scalars(select(Message).where(Message.conversation_id==cid).order_by(Message.created_at))).all()
    if ai_ready() and any(m.role=='user' for m in history):
        try:
            summary,evidence=await asyncio.wait_for(summarize(history),timeout=25)
            if summary:
                c.summary+='\n\n'+summary;c.summary_kind='form_and_ai';c.summary_sources=c.summary_sources+evidence
                await db.commit()
        except Exception:
            c.summary_kind='form_ai_unavailable';await db.commit()
    return {'saved':True,'message':'Saved in the local sales queue. No email, call, or external notification was sent.'}

@app.get('/api/admin/dashboard',dependencies=[Depends(require_admin)])
async def dashboard(db=Depends(db_session)):
    counts={key:await db.scalar(select(func.count()).select_from(model)) for key,model in [('conversations',Conversation),('leads',Lead),('documents',Document),('unanswered',Unanswered),('ai_requests',Usage)]}
    counts['pending']=await db.scalar(select(func.count()).select_from(Ticket).where(Ticket.status!='resolved'))
    payloads=(await db.scalars(select(Message.payload).where(Message.role=='assistant'))).all()
    counts['plan_enquiries']=sum(bool(p.get('plans')) for p in payloads)
    counts['tokens']=await db.scalar(select(func.coalesce(func.sum(Usage.tokens),0)))
    rows=[]
    for c in (await db.scalars(select(Conversation).order_by(Conversation.created_at.desc()).limit(100))).all():
        lead=await db.scalar(select(Lead).where(Lead.conversation_id==c.id));ticket=await db.scalar(select(Ticket).where(Ticket.conversation_id==c.id))
        rows.append({**serialize(c),'lead':serialize(lead) if lead else None,'ticket':serialize(ticket) if ticket else None})
    unanswered=(await db.scalars(select(Unanswered).order_by(Unanswered.created_at.desc()).limit(100))).all()
    usage=(await db.scalars(select(Usage).order_by(Usage.created_at.desc()).limit(20))).all()
    return {'counts':counts,'conversations':rows,'unanswered':[serialize(q) for q in unanswered],'usage':[serialize(u) for u in usage]}

@app.get('/api/admin/conversations/{cid}',dependencies=[Depends(require_admin)])
async def transcript(cid:str,db=Depends(db_session)):
    return [serialize(m) for m in (await db.scalars(select(Message).where(Message.conversation_id==cid).order_by(Message.created_at))).all()]

@app.patch('/api/admin/tickets/{tid}',dependencies=[Depends(require_admin)])
async def status(tid:str,body:StatusInput,db=Depends(db_session)):
    ticket=await db.get(Ticket,tid)
    if not ticket: raise HTTPException(404,'Callback request not found.')
    ticket.status=body.status;await db.commit();return serialize(ticket)

@app.get('/api/admin/documents',dependencies=[Depends(require_admin)])
async def documents(db=Depends(db_session)):
    rows=(await db.scalars(select(Document).order_by(Document.created_at.desc()))).all()
    return [{**serialize(d),'history':[serialize(a) for a in (await db.scalars(select(Audit).where(Audit.document_id==d.id).order_by(Audit.created_at.desc()))).all()]} for d in rows]

@app.post('/api/admin/documents',dependencies=[Depends(require_admin)],status_code=201)
async def add_doc(body:DocInput,db=Depends(db_session)):
    values=body.model_dump(exclude={'replaces','effective_date'});values['effective_date']=body.effective_date.isoformat()
    if body.replaces:
        old=await db.get(Document,body.replaces,with_for_update=True)
        if not old: raise HTTPException(404,'Original document not found.')
        version=await db.scalar(select(func.max(Document.version)).where(Document.family==old.family))
        values.update(family=old.family,version=version+1)
        if body.approved:
            for previous in (await db.scalars(select(Document).where(Document.family==old.family))).all(): previous.active=False
    doc=Document(**values);db.add(doc);await db.flush()
    db.add(Audit(document_id=doc.id,action='new_version' if body.replaces else 'created',details={'approved':doc.approved,'confidential':doc.confidential}))
    await db.commit();return serialize(doc)

@app.patch('/api/admin/documents/{did}',dependencies=[Depends(require_admin)])
async def edit_doc(did:str,body:DocState,db=Depends(db_session)):
    doc=await db.get(Document,did,with_for_update=True)
    if not doc: raise HTTPException(404,'Document not found.')
    if body.active and body.approved:
        siblings=(await db.scalars(select(Document).where(Document.family==doc.family,Document.id!=doc.id))).all()
        for sibling in siblings: sibling.active=False
    for key,value in body.model_dump().items():setattr(doc,key,value)
    db.add(Audit(document_id=did,action='review_state_changed',details=body.model_dump()))
    await db.commit();return serialize(doc)

@app.post('/api/admin/parse',dependencies=[Depends(require_admin)])
async def parse(file:UploadFile=File()):
    content=await file.read(5_000_001)
    if len(content)>5_000_000:raise HTTPException(413,'Choose a file smaller than 5 MB.')
    try: return {'text':await asyncio.to_thread(parse_file,file.filename or '',content),'title':(file.filename or 'Document').rsplit('.',1)[0]}
    except Exception: raise HTTPException(422,'Cannot read this file. Use a text-based PDF, DOCX, XLSX, PPTX, TXT, MD or HTML file.')

@app.post('/api/admin/reindex',dependencies=[Depends(require_admin)])
async def index(db=Depends(db_session)): return {'indexed':await reindex(db)}

@app.post('/api/admin/check-ai',dependencies=[Depends(require_admin)])
async def check_ai():
    from google.genai import types
    await invoke('connection_check','Reply with OK.',types.GenerateContentConfig(max_output_tokens=32))
    return {'connected':True,'model':MODEL}

app.mount('/assets',StaticFiles(directory=ROOT/'web'),name='assets')
@app.get('/')
@app.get('/admin')
@app.get('/widget')
async def page():return FileResponse(ROOT/'web'/'index.html')
