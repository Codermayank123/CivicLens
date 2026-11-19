# CivicLens real-provider verification report

Validated 2026-11-18. No secret values, tokens, database URIs, or generated secret values are included.

## Environment validation

Backend settings are loaded with this precedence: process environment, root `.env`, then `backend/.env`, using absolute project-root-derived paths. AI settings use the same pattern with `ai_service/.env`. Frontend uses `frontend/.env.local` and exposes only public `VITE_*` configuration.

| Setting | Result |
|---|---|
| `EMAIL_PROVIDER` | Configured: `brevo` |
| `BREVO_API_KEY` | Configured |
| `BREVO_SENDER_EMAIL` | Configured and syntactically valid |
| `BREVO_SENDER_NAME` | Configured |
| `SMS_PROVIDER` | Configured: `message_central` |
| `MESSAGE_CENTRAL_CUSTOMER_ID` | Configured |
| `MESSAGE_CENTRAL_AUTH_TOKEN` | Configured |
| `MESSAGE_CENTRAL_BASE_URL` | Configured HTTPS URL |
| OTP settings | Configured and positive |
| Frontend private Vite credentials | None detected |

The exact security variables are `JWT_SECRET_KEY` and `MEDIA_SIGNING_SECRET`. `BREVO_WEBHOOK_SECRET` is optional for local startup; without it, the webhook endpoint rejects requests rather than preventing the backend from starting. A public HTTPS deployment is required before configuring a Brevo webhook.

## Secret security

The original backend environment was backed up before rotation at `.codex-backup-real-provider-20261118/backend.env`.

- `JWT_SECRET_KEY`: separate cryptographically random secret, length 64.
- `MEDIA_SIGNING_SECRET`: separate cryptographically random secret, length 64.
- Secret values were not printed, logged, or written to this report.

## Runtime and MongoDB Atlas

The existing services are running locally:

- Backend: `http://127.0.0.1:8000` — `/health` returned HTTP 200.
- AI service: `http://127.0.0.1:8001` — `/health` returned HTTP 200.
- Frontend: `http://127.0.0.1:5173` — returned HTTP 200.

Backend startup completed MongoDB Atlas connectivity initialization and database index initialization successfully. No production records were reset, deleted, or modified.

## Brevo and Message Central status

Provider configuration was validated and the runtime provider classes resolved to `BrevoEmailProvider` and `MessageCentralProvider`.

No real email or SMS was sent. No provider acceptance, delivery, OTP arrival, or OTP verification is claimed. Live tests require explicit approval and a destination supplied by the user because they may consume provider credits.

## Registration, complaint, and resolution verification

Automated mock-provider coverage passed for:

- Email and SMS OTP registration restrictions, expiry, cooldown, attempt limits, hashing, session consumption, and duplicate prevention.
- Complaint submission, assignment, status, remarks, reopening, notification deduplication, delivery-state handling, and preferences.
- Resolution remarks, multiple evidence photographs, failed upload/database paths, signed media authorization, and attachment/link handling.

These are automated mock tests, not live provider delivery confirmations.

## AI provider investigation

- Configured provider: Gemini OpenAI-compatible endpoint.
- Configured text and vision model: `gemini-3.8-flash`.
- `/models`: HTTP 200 and authenticated successfully.
- Provider returned the model identifier as `models/gemini-3.8-flash`; the configured value does not exactly match that returned identifier.
- A chat request using the configured model returned HTTP 503; a repeat request later reached a read timeout.

The model was not changed and no fabricated classification was returned. AI end-to-end readiness remains unresolved.

## Automated test results

- Backend: 43 passed. Tests ran with process-only `EMAIL_PROVIDER=mock` and `SMS_PROVIDER=mock` overrides so no real messages could be sent.
- AI service: 4 passed.
- Frontend: type-check passed, 3 Vitest tests passed, production build passed.
- Build warning: the existing 3.01 MB heritage hero image is not precached by the PWA service worker.

## Remaining production blockers

1. Approve and execute one controlled Brevo email OTP test with a specified destination.
2. Approve and execute one controlled Message Central SMS OTP test with a specified verified Indian number.
3. Complete live registration, complaint notification, and resolution-photo workflows after provider tests succeed.
4. Resolve the AI model identifier/HTTP 503 issue without changing provider or model without approval.
5. Configure Brevo webhook authentication only after a public HTTPS backend exists.
6. Configure production object storage, HTTPS/TLS, CORS, Redis, public URLs, secret management, backups, and recovery procedures.

CivicLens is not marked production-ready.
