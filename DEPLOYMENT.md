# CivicLens deployment (without Docker)

CivicLens is deployed as separate frontend and backend services. The primary database is MongoDB Atlas or another private hosted MongoDB service. Redis is optional and disabled by default.

## Backend

Deploy the `backend` directory to a Python 3.11+ service such as Render, Railway, Fly.io, or an equivalent managed VM. Install with `pip install -e .` and run:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set `PYTHONPATH` to the backend directory if the hosting platform does not run from that directory. Use a private network path to MongoDB and S3-compatible storage. Do not expose MongoDB, Redis, or the storage bucket publicly.

Required production settings include:

- `APP_ENV=production`, `DEBUG=false`
- unique 64+ character `JWT_SECRET_KEY` and `MEDIA_SIGNING_SECRET`
- TLS MongoDB URI and production `MONGODB_DB_NAME`
- `STORAGE_BACKEND=s3` with least-privilege bucket credentials
- HTTPS `BACKEND_CORS_ORIGINS` and `BACKEND_PUBLIC_URL`
- `AI_MOCK_MODE=false` and configured real AI service
- `EMAIL_PROVIDER=smtp` or `resend`
- `CITIZEN_REGISTRATION_ENABLED=false` until the identity provider is authorized and verified end to end

The backend validates unsafe production settings at startup. `GET /health` is a liveness check. `GET /health/ready` checks MongoDB, storage, and Redis only when `REDIS_ENABLED=true`.

## AI service

Deploy `ai_service` separately with the same Python version and run:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Keep it private to the backend. Configure an OpenAI-compatible endpoint, API key, text model, and vision model. The mock provider is for local development and tests only.

## Frontend

Deploy `frontend` to Vercel, Netlify, Cloudflare Pages, or an equivalent static host:

```text
npm ci
npm run build
```

Set `VITE_API_URL` to the public backend `/api/v1` URL and configure the frontend host in `BACKEND_CORS_ORIGINS`.

## S3 migration

1. Create a private bucket with server-side encryption, versioning, and a lifecycle policy.
2. Set S3 credentials in the backend environment.
3. Run `backend/scripts/migrate_local_uploads_to_s3.py` against a backup copy first.
4. Verify object counts, content hashes, and signed URL access before switching `STORAGE_BACKEND=s3`.
5. Keep the local upload directory until the migration has been restored and validated.

## MongoDB backups and rollback

Use Atlas continuous backups or encrypted scheduled `mongodump` backups. Restore into a new database name, run the application smoke tests, and switch the backend connection string only after validation. Keep migrations additive; do not drop collections or fields blindly. The collection/index contract is in [docs/MONGODB_SCHEMA.md](docs/MONGODB_SCHEMA.md).

## Release checklist

- Run backend pytest, frontend Vitest, TypeScript build, and API smoke tests.
- Confirm MongoDB indexes exist and TTL indexes are active.
- Confirm signed media URLs reject expired or tampered signatures.
- Confirm staff/admin MFA and identity-provider readiness gates are addressed before enabling those features.
- Review audit logs, CORS, security headers, rate limits, secret rotation, and backup restore evidence.
- Deploy backend and frontend separately, then monitor `/health/ready` and error alerts.
