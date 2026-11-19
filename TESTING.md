# CivicLens testing

The active backend is MongoDB-only. Route tests use an async MongoDB-shaped test double so they do not create SQLite/PostgreSQL databases or require a live MongoDB server. Staging tests should run against a dedicated MongoDB database with real indexes.

## Commands

```powershell
$env:PYTHONPATH = "backend"
$env:DEBUG = "true"
..\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=backend/.tmp/pytest-run

cd frontend
npm run test -- --run
npm run type-check
npm run build
```

## Covered behavior

- registration, login, refresh-token rotation, logout, password reset, email verification, and production configuration gates;
- citizen/officer/field-staff/admin role checks and complaint object authorization;
- complaint creation, AI advisory metadata, duplicate candidates, assignment, lifecycle transitions, comments, citizen verification, reopen flow, notifications, and point awards;
- identity-provider safety boundaries, including rejection of OTP/Aadhaar payloads;
- private media signatures, file validation, local storage, S3 adapter behavior, and analytics/heatmap responses;
- frontend route guards and production compilation.

## Required staging/E2E additions before production

- Playwright flows across all four roles with a real MongoDB replica set;
- real OpenAI-compatible text and vision provider outage/timeout/rate-limit tests;
- real SMTP/Resend delivery and bounce handling;
- S3 authorization, malware scanning, and object-retention verification;
- MFA, SMS, accessibility (WCAG 2.2 AA), performance/load, dependency scanning, secret scanning, and backup restoration tests;
- UIDAI/DigiLocker authorized-provider signed-response tests in the approved sandbox.

Tests must fail closed for unavailable AI, storage, identity, or email services in production. Do not mark mock-provider tests as evidence of production readiness.
