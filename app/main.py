from __future__ import annotations
import os, re, sqlite3, json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv('CAREPILOT_DB', str(ROOT / 'carepilot.db')))
app = FastAPI(title='CarePilot AI', version='1.0.0', description='Safety-first clinic administration MVP')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=1500)
    session_id: str = Field(default='demo-session', min_length=1, max_length=80)
    patient_name: Optional[str] = Field(default=None, max_length=100)

class StatusInput(BaseModel):
    status: str

class InquiryReview(BaseModel):
    response: str = Field(min_length=1, max_length=1500)

class AppointmentInput(BaseModel):
    patient_name: str = Field(min_length=2, max_length=100)
    preferred_time: str = Field(min_length=2, max_length=100)
    reason: str = Field(min_length=2, max_length=200)


def connect():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c


def init_db():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS appointments (
          id INTEGER PRIMARY KEY AUTOINCREMENT, patient_name TEXT NOT NULL,
          preferred_time TEXT NOT NULL, reason TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Pending', source TEXT NOT NULL DEFAULT 'chat',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS conversations (
          id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
          role TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS inquiries (
          id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
          patient_name TEXT, message TEXT NOT NULL, intent TEXT NOT NULL,
          draft_response TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Needs review',
          created_at TEXT NOT NULL, reviewed_response TEXT
        );
        ''')
        count = c.execute('SELECT COUNT(*) n FROM appointments').fetchone()['n']
        if count == 0:
            now = datetime.now().isoformat(timespec='minutes')
            seed = [
              ('Aarav Sharma','2026-10-19 10:30','Routine appointment','Confirmed'),
              ('Meera Joshi','2026-10-19 12:00','General consultation','Pending'),
              ('Kabir Singh','2026-10-20 09:15','Follow-up appointment','Confirmed'),
              ('Anaya Verma','2026-10-20 15:00','Appointment query','Cancelled')]
            c.executemany('INSERT INTO appointments(patient_name,preferred_time,reason,status,created_at,updated_at) VALUES(?,?,?,?,?,?)',
                [(n,t,r,s,now,now) for n,t,r,s in seed])
        if c.execute('SELECT COUNT(*) n FROM inquiries').fetchone()['n'] == 0:
            now = datetime.now().isoformat(timespec='minutes')
            c.execute('INSERT INTO inquiries(session_id,patient_name,message,intent,draft_response,status,created_at) VALUES(?,?,?,?,?,?,?)',
              ('sample','Riya Demo','What are your clinic hours?','FAQ','Our demo clinic is open Monday–Saturday, 9 AM–5 PM. Hours are sample data; please confirm with clinic staff.','Needs review',now))

init_db()

URGENT = re.compile(r'\b(chest pain|can.t breathe|cannot breathe|difficulty breathing|severe bleeding|unconscious|stroke|suicid|emergency|overdose)\b', re.I)

def detect_intent(message: str) -> str:
    m = message.lower()
    if URGENT.search(m): return 'urgent_escalation'
    if any(w in m for w in ['cancel','cancellation']): return 'cancel'
    if any(w in m for w in ['reschedule','change my appointment','move my appointment']): return 'reschedule'
    if any(w in m for w in ['book','appointment','schedule','available slot','visit']): return 'booking'
    if any(w in m for w in ['hours','open','location','address','parking','insurance','cost','fee','clinic']): return 'faq'
    return 'general_inquiry'

def extract_time(message: str) -> str:
    # Preserve the patient's wording rather than inventing a real slot.
    patterns = [r'\b(?:today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?\b', r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b', r'\b\d{4}-\d{2}-\d{2}(?:\s+\d{1,2}:\d{2})?\b']
    for p in patterns:
        m = re.search(p, message, re.I)
        if m: return m.group(0)
    return ''

def extract_name(message: str, supplied: Optional[str]) -> str:
    if supplied and supplied.strip(): return supplied.strip()[:100]
    m = re.search(r"(?:my name is|i am|i'm|this is)\s+([A-Za-z][A-Za-z .'-]{1,70}?)(?=\s+(?:and\b|i\b|my\b|for\b|on\b|at\b)|[,.!?]|$)", message, re.I)
    if m: return m.group(1).strip().rstrip('.,!?')
    return ''

async def ai_draft(message: str, intent: str) -> tuple[str, str]:
    # Keep urgent escalation deterministic and independent of any external model.
    # This is administrative safety messaging, not clinical triage.
    if intent == 'urgent_escalation':
        return ('This may require urgent attention. I cannot assess symptoms. Please contact your local emergency number or go to the nearest emergency department now. I am flagging this message for clinic staff.', 'Local safety fallback')

    key = os.getenv('GEMINI_API_KEY','').strip()
    if key:
        prompt = ('You are a clinic administrative assistant. Do not diagnose, prescribe, or provide clinical advice. '
          'For urgent symptoms, tell the person to contact local emergency services immediately. '
          'Answer only administrative questions; if unsure, route to staff. Keep under 90 words. '
          f'Intent: {intent}\nPatient message: {message}')
        try:
            model = os.getenv('GEMINI_MODEL','gemini-2.0-flash')
            async with httpx.AsyncClient(timeout=12) as client:
                res = await client.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}',
                    json={'contents':[{'parts':[{'text':prompt}]}], 'generationConfig':{'temperature':0.2,'maxOutputTokens':180}})
                res.raise_for_status()
                data = res.json()
                text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                return text, 'Gemini'
        except Exception:
            pass
    if intent == 'faq':
        return ('Our demo clinic hours are Monday–Saturday, 9 AM–5 PM. This is sample information and may not reflect a real clinic. A staff member can confirm hours, location, fees, and insurance details.','Local fallback')
    if intent == 'booking':
        return ('I can help start an appointment request. Please share your name, preferred day/time, and a brief administrative reason for the visit. A clinic staff member must confirm availability.','Local fallback')
    if intent == 'cancel':
        return ('I can flag a cancellation request for the clinic team. Please share the patient name and appointment time so staff can identify the correct booking.','Local fallback')
    if intent == 'reschedule':
        return ('I can flag a rescheduling request. Please share the patient name, current appointment time, and preferred new time. Staff will confirm availability.','Local fallback')
    return ('Thanks for contacting the clinic. I have sent your message to the staff review queue. A team member can provide a verified response.','Local fallback')

@app.get('/')
def index(): return FileResponse(ROOT / 'static' / 'index.html')

@app.get('/api/health')
def health(): return {'status':'ok','database':'sqlite','ai_provider':'Gemini optional; safe local fallback enabled'}

@app.get('/api/dashboard')
def dashboard():
    with connect() as c:
        rows = c.execute('SELECT status,COUNT(*) n FROM appointments GROUP BY status').fetchall()
        stats = {r['status'].lower():r['n'] for r in rows}
        total = c.execute('SELECT COUNT(*) FROM appointments').fetchone()[0]
        pending_inquiries = c.execute("SELECT COUNT(*) FROM inquiries WHERE status='Needs review'").fetchone()[0]
        appointments = [dict(r) for r in c.execute('SELECT * FROM appointments ORDER BY created_at DESC LIMIT 100')]
        inquiries = [dict(r) for r in c.execute('SELECT * FROM inquiries ORDER BY created_at DESC LIMIT 100')]
    return {'total_appointments':total,'pending_appointments':stats.get('pending',0),'confirmed_appointments':stats.get('confirmed',0),'cancelled_appointments':stats.get('cancelled',0),'pending_inquiries':pending_inquiries,'appointments':appointments,'inquiries':inquiries}

@app.post('/api/chat')
async def chat(body: ChatInput):
    message = body.message.strip()
    if not message: raise HTTPException(400,'Message cannot be empty')
    intent = detect_intent(message)
    name = extract_name(message, body.patient_name)
    now = datetime.now().isoformat(timespec='seconds')
    with connect() as c:
        c.execute('INSERT INTO conversations(session_id,role,message,created_at) VALUES(?,?,?,?)',(body.session_id,'patient',message,now))
    if intent == 'urgent_escalation':
        reply, provider = await ai_draft(message,intent)
        with connect() as c:
            c.execute('INSERT INTO inquiries(session_id,patient_name,message,intent,draft_response,status,created_at) VALUES(?,?,?,?,?,?,?)',(body.session_id,name or None,message,intent,reply,'Urgent escalation',now))
            c.execute('INSERT INTO conversations(session_id,role,message,created_at) VALUES(?,?,?,?)',(body.session_id,'assistant',reply,now))
        return {'reply':reply,'intent':intent,'provider':provider,'needs_staff_review':True,'urgent':True,'appointment':None}
    appointment = None
    if intent == 'booking':
        when = extract_time(message)
        reason_match = re.search(r'(?:for|reason is|reason:|visit for)\s+(.{3,100})',message,re.I)
        reason = reason_match.group(1).strip().rstrip('.!?') if reason_match else 'Reason to be confirmed with staff'
        if name and when:
            with connect() as c:
                cur = c.execute('INSERT INTO appointments(patient_name,preferred_time,reason,status,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(name,when,reason,'Pending','chat',now,now))
                appointment = dict(c.execute('SELECT * FROM appointments WHERE id=?',(cur.lastrowid,)).fetchone())
    reply, provider = await ai_draft(message,intent)
    if intent == 'booking' and appointment:
        reply = f"Thanks, {appointment['patient_name']}. Your request for {appointment['preferred_time']} has been created as Pending. The clinic team must confirm availability. Reference: CP-{appointment['id']:04d}."
    elif intent == 'cancel':
        reply = 'Your cancellation request has been sent to clinic staff for review. I will not cancel a booking until staff verifies the correct appointment.'
    elif intent == 'reschedule':
        reply = 'Your rescheduling request has been sent to clinic staff for review. The existing booking remains unchanged until staff confirms the new time.'
    with connect() as c:
        if intent in ('faq','general_inquiry','cancel','reschedule') or (intent == 'booking' and not appointment):
            c.execute('INSERT INTO inquiries(session_id,patient_name,message,intent,draft_response,status,created_at) VALUES(?,?,?,?,?,?,?)',(body.session_id,name or None,message,intent,reply,'Needs review',now))
        c.execute('INSERT INTO conversations(session_id,role,message,created_at) VALUES(?,?,?,?)',(body.session_id,'assistant',reply,now))
    return {'reply':reply,'intent':intent,'provider':provider,'needs_staff_review':intent in ('faq','general_inquiry','cancel','reschedule') or (intent=='booking' and not appointment),'urgent':False,'appointment':appointment}

@app.post('/api/appointments')
def create_appointment(body: AppointmentInput):
    now = datetime.now().isoformat(timespec='seconds')
    with connect() as c:
        cur = c.execute('INSERT INTO appointments(patient_name,preferred_time,reason,status,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
            (body.patient_name.strip(),body.preferred_time.strip(),body.reason.strip(),'Pending','staff dashboard',now,now))
        row = dict(c.execute('SELECT * FROM appointments WHERE id=?',(cur.lastrowid,)).fetchone())
    return {'appointment':row,'message':f"Request created as Pending. Reference CP-{row['id']:04d}."}

@app.patch('/api/appointments/{appointment_id}')
def update_appointment(appointment_id: int, body: StatusInput, x_admin_passcode: Optional[str] = Header(default=None)):
    if body.status not in {'Pending','Confirmed','Cancelled'}: raise HTTPException(400,'Status must be Pending, Confirmed, or Cancelled')
    required = os.getenv('ADMIN_DEMO_PASSCODE','').strip()
    if required and required != 'change-this-before-deploying' and x_admin_passcode != required:
        raise HTTPException(401,'Admin passcode required')
    now = datetime.now().isoformat(timespec='seconds')
    with connect() as c:
        cur = c.execute('UPDATE appointments SET status=?,updated_at=? WHERE id=?',(body.status,now,appointment_id))
        if not cur.rowcount: raise HTTPException(404,'Appointment not found')
        row = dict(c.execute('SELECT * FROM appointments WHERE id=?',(appointment_id,)).fetchone())
    return {'appointment':row,'message':f"Appointment status updated to {body.status}"}

@app.post('/api/inquiries/{inquiry_id}/send')
def send_inquiry(inquiry_id: int, body: InquiryReview):
    now = datetime.now().isoformat(timespec='seconds')
    with connect() as c:
        row = c.execute('SELECT * FROM inquiries WHERE id=?',(inquiry_id,)).fetchone()
        if not row: raise HTTPException(404,'Inquiry not found')
        c.execute("UPDATE inquiries SET status='Responded', reviewed_response=? WHERE id=?",(body.response.strip(),inquiry_id))
        c.execute('INSERT INTO conversations(session_id,role,message,created_at) VALUES(?,?,?,?)',(row['session_id'],'staff',body.response.strip(),now))
    return {'status':'Responded','message':'Reviewed response marked as sent in demo mode.'}

@app.get('/api/conversations/{session_id}')
def conversation(session_id: str):
    with connect() as c:
        rows = c.execute('SELECT role,message,created_at FROM conversations WHERE session_id=? ORDER BY id',(session_id,)).fetchall()
    return {'messages':[dict(r) for r in rows]}
