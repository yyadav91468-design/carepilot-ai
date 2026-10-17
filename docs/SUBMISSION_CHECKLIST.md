# Final Submission Checklist

The challenge requires a live deployment URL, public GitHub repository, 3–5 minute demo video, README/architecture overview, and AI prompt log/debugging example.

## Before sharing externally

- [ ] Run the app locally and complete all manual tests in `TEST_PLAN.md`.
- [ ] Run `pytest -q` after installing `requirements-dev.txt` and record the actual output.
- [ ] Check the app at desktop and mobile widths.
- [ ] Set a strong `ADMIN_DEMO_PASSCODE` in deployment settings; never commit `.env` or API keys.
- [ ] Deploy to a host with persistent storage, or migrate to managed PostgreSQL if the host filesystem is ephemeral.
- [ ] Open the deployed `/api/health` endpoint and test a real booking through the deployed UI.
- [ ] Push source to a public GitHub repository; check `.env`, database files, and real patient information are not committed.
- [ ] Replace the AI prompt log placeholders with the actual tools/prompts used and a real debugging example.
- [ ] Record a 3–5 minute demo using only synthetic data; show chat → created request → dashboard/status update → persisted record → AI workflow/review queue.
- [ ] Include the deployed URL and repository URL in the final email/application.

## Suggested demo video outline (about 4 minutes)

- 0:00–0:25 — Introduce the clinic operations problem and CarePilot's safety-first scope.
- 0:25–1:15 — Use the patient chat to submit a complete appointment request.
- 1:15–1:55 — Show the extracted fields, workflow trace, pending status, and reference ID.
- 1:55–2:35 — Open dashboard, confirm the appointment, refresh, and show the status remains saved.
- 2:35–3:20 — Ask a clinic FAQ, edit the draft in Inquiry review, and mark it sent.
- 3:20–3:45 — Show urgent-message escalation and explain that it is not medical triage.
- 3:45–4:00 — Summarize stack, limitations, and next steps.
