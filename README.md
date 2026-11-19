# CivicLens

CivicLens is a React/Vite + FastAPI civic issue platform for reporting public problems, routing work to authorized government teams, and recording citizen-verified outcomes.

## Current architecture

- Frontend: React 18, TypeScript, Vite, React Query, Leaflet, Recharts, PWA/offline queue.
- Backend: FastAPI with Argon2id passwords, short-lived JWT access tokens, httpOnly refresh cookies, RBAC, audit logging, rate limits, and signed media URLs.
- Primary database: MongoDB only, accessed asynchronously with Motor/PyMongo. Collections and indexes are documented in [docs/MONGODB_SCHEMA.md](docs/MONGODB_SCHEMA.md).
- AI: separate FastAPI service. Development fallback is explicitly labeled mock; production startup rejects mock AI.
- Storage: local disk for development, private S3-compatible storage for production.
- Email: mock outbox for development, SMTP or Resend for delivery.
- Identity: modular provider adapter. The included development and UIDAI sandbox adapters never accept Aadhaar OTPs or raw Aadhaar numbers.

No Docker, Docker Compose, PostgreSQL, MySQL, SQLite, or relational database is required by the application runtime.

## Local development

Prerequisites: Python 3.11+, Node.js 18+, and a running MongoDB instance or MongoDB Atlas database.

```powershell
Copy-Item .env.example .env

cd backend
..\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:PYTHONPATH = (Get-Location).Path
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

In another terminal:

```powershell
cd ai_service
..\.venv\Scripts\python.exe -m pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

And for the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Set `AI_MOCK_MODE=false` and configure the AI service provider before any production deployment. Set `EMAIL_PROVIDER=smtp` or `resend` for real delivery. Keep `CITIZEN_REGISTRATION_ENABLED=false` until an authorized identity provider, legal review, credentials, and end-to-end tests are complete.

## Development accounts

Use the seed script only against a development database. Demo credentials must never be deployed. The seed data and provider boundaries are described in [docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md).

## Verification

```powershell
# Backend tests use an async MongoDB-shaped test double; no relational database is created.
$env:PYTHONPATH = "backend"
$env:DEBUG = "true"
..\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp=backend/.tmp/pytest-run

cd frontend
npm run test -- --run
npm run build
```

See [API.md](API.md), [DEPLOYMENT.md](DEPLOYMENT.md), [TESTING.md](TESTING.md), and [docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md) for operational details and explicit remaining limitations.
