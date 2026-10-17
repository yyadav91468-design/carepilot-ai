# AI Prompt Log and Debugging Example

This log documents AI assistance used to build and review CarePilot AI for the EIR / AI Engineer assessment. The prompt descriptions below are concise records of the tasks used during this build, not verbatim exported chat transcripts. The AI tool used in this work session was **ChatGPT (OpenAI)**. Do not claim Claude Code, Codex, or Cursor was used unless you also used it yourself.

## Prompt 1 — Build the end-to-end appointment workflow

**Prompt record (summarized):**

> Build a working healthcare administration MVP for a clinic, not a static prototype. Use FastAPI and a persistent local database. A patient should be able to request an appointment through chat by providing their name, preferred date/time, and reason. Detect the intent, extract the fields, save the request as Pending, return a reference, and show it on the staff dashboard. Never claim a slot is available or confirmed until staff confirms it. Include validation and automated tests.

**Implementation produced:**
- `app/main.py`: `/api/chat`, `detect_intent`, `extract_name`, `extract_time`, SQLite writes, and appointment status API.
- `static/index.html`, `static/app.js`, `static/styles.css`: patient chat and operations dashboard.
- `tests/test_workflow.py`: verifies a chat booking is persisted and starts as Pending, and staff can update its status.

**Engineering decisions retained:**
- SQLite keeps the demo free to run locally and avoids requiring a hosted database account.
- A booking request remains Pending; the assistant does not claim that availability has been checked.
- The workflow uses synthetic demo data only.

## Prompt 2 — Add healthcare safety and staff review

**Prompt record (summarized):**

> Review the patient-facing clinic assistant for safety. It is an administrative tool, not a diagnostic tool. Do not diagnose or prescribe. Route FAQs, general inquiries, cancellations, rescheduling, and incomplete booking requests to staff review. For urgent keyword matches, show a conservative emergency message and flag staff review. Keep generated messages identifiable and never let the system silently cancel or confirm an appointment.

**Implementation produced:**
- `detect_intent()` prioritizes urgent keyword matching.
- FAQs and uncertain requests are stored in the inquiries table for review.
- Cancellation and rescheduling messages do not alter an existing appointment automatically.
- Urgent messages are flagged for staff and receive emergency-services language, not clinical advice.
- `tests/test_workflow.py` covers FAQ review and urgent escalation.

**Important limitation:** the urgent-message detector is a simple keyword rule, not a clinically validated triage system. It can miss urgent messages and can also flag non-emergencies. Do not represent it as medical triage.

## Prompt 3 — Review the urgent-message path for failure modes

**Prompt record (summarized):**

> Inspect the urgent-message response path. Check whether urgent messages depend on an external generative model, and make the emergency escalation wording deterministic if it does. Add a regression test proving the urgent path does not call the external AI client.

**Change made:**
- In `app/main.py`, `ai_draft()` now checks `intent == 'urgent_escalation'` before checking `GEMINI_API_KEY` or constructing the HTTP client. It immediately returns the local safety message.
- Added `test_urgent_escalation_bypasses_external_ai` in `tests/test_workflow.py`. The test sets a dummy API key and replaces the HTTP client with a guard that raises if called. The test passes, proving this code path does not invoke the external client.

## Debugging / code-review example

**Observed issue:** code inspection found that `ai_draft()` checked for a configured Gemini API key before checking whether the message was an urgent escalation. If a key were configured, the urgent message would be sent to the generative model first. The model prompt asked for safe behavior, but that still made urgent messaging dependent on an external response and network availability.

**Reproduction / verification method:**
1. Set `GEMINI_API_KEY` to any non-empty test value.
2. Call `ai_draft('I am having chest pain', 'urgent_escalation')`.
3. Use a guarded/mock HTTP client that fails if instantiated. Before the fix, the function attempted the external-client branch; after the fix, it returns the local safety fallback before touching the client.

**Root cause:** the external AI configuration check ran before the urgent-intent guard.

**Fix:** moved the urgent-intent response to the start of `ai_draft()` in `app/main.py`, so it returns a deterministic local message before checking API configuration. Added a regression test to prevent the ordering from regressing.

**Verification result:** ran `python -m pytest -q` from the project root after the change: **6 passed**. The new regression test uses a dummy key and a guard client, so it verifies the urgent path does not contact the external AI client. No live Gemini API call was made or claimed.

**What I learned:** prompts alone are not a safety boundary. Safety-critical administrative messaging should have deterministic guardrails and regression tests, and external model output should not be treated as guaranteed safe.

## AI-use disclosure and evidence checklist

- [x] Identify the AI tool used in this build: ChatGPT (OpenAI).
- [x] Record meaningful implementation and review prompt summaries.
- [x] Document one code-review finding, the code change, and a regression test.
- [x] Record the actual test command and result: `python -m pytest -q` — 6 passed.
- [x] Distinguish local fallback testing from a live model API test.
- [ ] Before submission, run the application yourself and capture screenshots/video of the workflows you demonstrate.
- [ ] If you use Claude Code, Codex, Cursor, or another tool separately, add its actual prompts and outcomes rather than implying it was used here.
