# Manual Test Plan

Run the app locally and record pass/fail with date and environment before submission.

| ID | Test | Expected result | Result |
|---|---|---|---|
| T01 | Open `/api/health` | `status: ok` | Not yet run |
| T02 | Open dashboard | Counts and seeded synthetic records load | Not yet run |
| T03 | Chat with complete booking sample | Pending appointment saved and reference shown | Not yet run |
| T04 | Refresh page / dashboard after booking | New appointment remains in database | Not yet run |
| T05 | Change pending appointment to Confirmed | Status and counts update | Not yet run |
| T06 | Ask clinic-hours FAQ | Draft response and review item appear | Not yet run |
| T07 | Edit and approve inquiry response | Inquiry status becomes Responded | Not yet run |
| T08 | Send cancellation request | Request is routed to staff; no silent cancellation | Not yet run |
| T09 | Send urgent keyword sample | Emergency guidance and urgent review record appear | Not yet run |
| T10 | Submit empty/oversized API message | Validation rejects invalid input | Not yet run |
| T11 | Start app without Gemini key | Local fallback works | Not yet run |
| T12 | Use voice input/output in supported browser | Browser speech works after permission | Not yet run |

Do not submit this table as passing until you actually run the tests. Add screenshots or a short evidence note for the key end-to-end workflow.
