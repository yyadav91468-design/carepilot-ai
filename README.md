# CarePilot AI — Clinic Operations MVP

A safety-first, AI-assisted clinic administration MVP built for the AI Healthcare Startup EIR / AI Engineer assessment. CarePilot helps a demo clinic capture appointment requests, triage routine patient messages, generate administrative response drafts, and keep staff in control of final decisions.

> **Important:** This is an assessment/demo application, not a production healthcare system. Use synthetic data only. It does not diagnose, prescribe, triage clinically, or replace emergency services. The demo clinic hours and seed records are fictional.

## What works

- Patient chat for appointment requests, FAQs, cancellation/reschedule requests, and general inquiries.
- Intent classification, lightweight extraction of patient name/time/reason, and a complete request-to-database workflow.
- Appointment records persisted to SQLite; pending requests can be confirmed/cancelled by clinic staff from the dashboard.
- Dashboard counters for total, pending, confirmed, cancelled, and inquiries needing review.
- Human review queue: AI-generated drafts can be edited, approved, and recorded as sent in demo mode.
- Urgent keyword safety path: avoids clinical advice, advises contacting local emergency services, and flags staff review. This keyword check is not a clinical detector and can miss messages.
- Optional Gemini API integration with a local fallback if no key is configured or the API fails.
- Browser speech input (where supported) and speech synthesis for reading the latest response aloud.
- Synthetic seed data, request validation, error handling, and responsive UI.

## Stack and design decisions

- **FastAPI + Pydantic:** quick, typed API surface with input validation and readable endpoint boundaries.
- **SQLite:** zero-cost, no external database required for a local demo; durable local persistence. For deployment with ephemeral storage or multiple replicas, migrate to managed PostgreSQL.
- **Vanilla HTML/CSS/JavaScript:** no build pipeline or paid frontend dependencies; fast setup and simple deployment. This is a deliberate assessment trade-off against the suggested Next.js stack.
- **Gemini (optional):** response drafting can use `GEMINI_API_KEY`; without a key, the local safe fallback keeps the demo functional. Intent detection and extraction remain transparent local logic so workflow behavior is inspectable.
- **Human-in-the-loop:** uncertain requests, cancellation/rescheduling, and FAQs are routed to a review queue. The app does not silently cancel or claim a slot is confirmed.

## Run locally

Requires Python 3.10+.

```powershell
# From the carepilot-ai folder
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Optional: add a Gemini API key to .env; leave blank for local fallback
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. API docs: <http://127.0.0.1:8000/docs>. Health check: <http://127.0.0.1:8000/api/health>.

On macOS/Linux, activate with `source .venv/bin/activate`.

## Demo walkthrough (3–5 minutes)

1. Open Overview and point out the dashboard metrics and seeded synthetic records.
2. Open Patient assistant and use **Book appointment**. It sends a full example: name, preferred time, and administrative reason.
3. Show the workflow trace: detected intent, extracted fields, database record creation, and pending status.
4. Open Appointments; confirm the new appointment. Refresh and show that the status persists.
5. Ask “What are your clinic hours?” and open Inquiry review. Edit the draft if desired and click **Approve & mark sent**.
6. Optional: send “I am having chest pain” to demonstrate the urgent safety message and staff escalation. Do not portray this as medical triage.
7. Optional: demonstrate voice input/output in a supported browser after granting microphone permission.

## API overview

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/dashboard` | Counts, appointments, inquiries |
| POST | `/api/chat` | Persist conversation; detect intent; create request or review item |
| POST | `/api/appointments` | Create pending appointment request |
| PATCH | `/api/appointments/{id}` | Update status to Pending, Confirmed, or Cancelled |
| POST | `/api/inquiries/{id}/send` | Record staff-reviewed response as sent in demo mode |
| GET | `/api/conversations/{session_id}` | Read persisted conversation history |

## Environment variables

Copy `.env.example` to `.env`.

- `GEMINI_API_KEY` — optional; if present, attempts Gemini response generation. Never commit this secret.
- `GEMINI_MODEL` — optional; defaults to `gemini-2.0-flash`.
- `ADMIN_DEMO_PASSCODE` — optional demo gate for appointment status changes. Set a strong passcode for any public demo. This is not a substitute for production authentication/RBAC.
- `CAREPILOT_DB` — optional path override for SQLite database.

## Deployment notes

Deploy as a single Python web service on Render or another platform that supports persistent disks. Build command: `pip install -r requirements.txt`. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. If the host's filesystem is ephemeral, records may reset on restart; attach persistent storage or migrate to managed PostgreSQL. Configure environment variables in the hosting dashboard. Set `ADMIN_DEMO_PASSCODE` to a strong non-default value. Do not publish API keys or real patient data.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/AI_PROMPT_LOG.md`](docs/AI_PROMPT_LOG.md).

## AI development disclosure

AI tools can accelerate scaffolding, UI iteration, endpoint design, test planning, and documentation. For this submission, keep an honest record of which tools you used, which suggestions you accepted/rejected, and the tests you personally ran. The prompt log records the AI-assisted implementation tasks, a code-review finding in the urgent-message path, the fix and regression test, and the verified local test result. Prompt records are summarized rather than verbatim exported transcripts. Run the app yourself and capture your own demo evidence before submission. Do not claim tests or debugging you did not perform.

## Known limitations and next steps

- SQLite is suitable for a single-instance demo, not multi-clinic production use.
- The demo has no full login, patient identity verification, audit policy, encryption/key management strategy, or production authorization model.
- Cancellation/rescheduling requests are routed for review; staff does not yet select an existing appointment and change its time through a dedicated workflow.
- Keyword escalation is intentionally conservative but not clinically reliable; it is not a substitute for medical triage.
- Browser speech support and microphone permissions vary by device/browser.
- Add PostgreSQL, migrations, role-based access, clinic-specific configuration, audit logging, monitoring, consent/privacy review, automated reminders, stronger tests, and a robust AI evaluation set before real use.
