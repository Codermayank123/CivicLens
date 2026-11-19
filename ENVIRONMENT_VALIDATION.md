# CivicLens environment validation

Validated 2026-11-18. This report intentionally contains no secret values.

## Loading model

- Root `.env`: shared development defaults.
- `backend/.env`: backend secrets and MongoDB Atlas configuration; loaded after the root file.
- `ai_service/.env`: AI provider configuration; loaded after the root file.
- `frontend/.env.local`: public Vite variables only.
- Process/container environment variables have highest precedence.
- Compose loads the root file first and the matching service file second. Frontend receives only its public file/build arguments.

The original localhost/empty-credential behavior came from both Pydantic settings classes loading only the root `.env`, plus Compose explicitly interpolating root values into backend and AI containers. The loaders and Compose files now use absolute project-root-derived service paths and service-specific precedence.

## Current service status

| Service | Result | Notes |
|---|---|---|
| Backend | Corrected and running | Resolves a hosted MongoDB Atlas endpoint from `backend/.env`; real URI is never logged. JWT and media-signing secrets are separate random 64-character values. Brevo and Message Central are configured, but live delivery is pending explicit approval. |
| MongoDB Atlas | Live check passed | Redacted Motor `admin.command("ping")` returned success against the configured Atlas target. |
| AI service loading | Corrected and validated | Key is non-empty, real-provider mode is active, base URL normalizes to the Gemini OpenAI-compatible path, and both configured models are listed by the provider. |
| Real AI provider | Authentication/model-list check passed; chat currently unavailable | Authenticated `/models` returned HTTP 200 and included the configured model. A minimal chat request returned HTTP 503 during this audit, so the CivicLens adapter is not marked end-to-end verified. |
| Frontend | Corrected and built | `VITE_API_URL`, `VITE_MAP_TILE_URL`, and `VITE_APP_NAME` are in `frontend/.env.local`; no `VITE_*` private-key variable exists. |
| Compose | Parsed and reviewed | Service files are separated. Docker runtime verification was not possible because Docker CLI is not installed in this environment. |

## Genuine remaining production requirements

1. Replace the current backend JWT and media-signing secrets with unique random values of at least 64 characters.
2. Execute an approved real Brevo email test and confirm delivery.
3. Execute an approved real Message Central VerifyNow test and confirm SMS delivery and OTP verification.
4. Configure production object storage credentials/bucket/public URL and TLS-safe public URLs; the checked-in service files still contain local-development defaults where deployment overrides are required.
5. Provide the approved complete India location catalog URL if structured location routing is required.
6. Resolve the provider-side HTTP 503 and rerun a clean CivicLens adapter classification request. The credential and model-list check alone is not sufficient for production readiness.
7. Set production CORS, Redis password, TLS certificates, and deployment-specific public URLs in the deployment secret/configuration store.

The current configuration is therefore **not production-ready**. No provider credential, URL, or successful inference result has been invented.

## Redacted validation commands

From the project root:

```powershell
# Backend settings and secret-strength metadata (prints no secret values)
Push-Location backend
& '..\\.venv\\Scripts\\python.exe' -c "from app.config import get_settings; s=get_settings(); print('atlas=', 'mongodb.net' in s.MONGODB_URL, 'db=', s.MONGODB_DB_NAME, 'jwt_len=', len(s.JWT_SECRET_KEY), 'media_len=', len(s.MEDIA_SIGNING_SECRET))"

# MongoDB Atlas ping (prints no URI)
& '..\\.venv\\Scripts\\python.exe' -c "import asyncio; from motor.motor_asyncio import AsyncIOMotorClient; from app.config import get_settings; s=get_settings(); loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop); c=AsyncIOMotorClient(s.MONGODB_URL, serverSelectionTimeoutMS=8000); print('atlas_ping_ok=', bool(loop.run_until_complete(c.admin.command('ping')).get('ok'))); c.close(); loop.close()"
Pop-Location

# AI settings and provider authentication/model list (prints no key)
Push-Location ai_service
& '..\\.venv\\Scripts\\python.exe' -c "import httpx; from app.settings import AISettings; s=AISettings(); r=httpx.get(s.AI_API_BASE_URL+'/models', headers={'Authorization':'Bearer '+s.AI_API_KEY}, timeout=30); print('key_present=', bool(s.AI_API_KEY), 'status=', r.status_code, 'model=', s.AI_TEXT_MODEL)"
Pop-Location

# Tests and frontend production build
Push-Location backend; & '..\\.venv\\Scripts\\python.exe' -m pytest -q tests -p no:cacheprovider --basetemp=.pytest-tmp-local; Pop-Location
Push-Location ai_service; & '..\\.venv\\Scripts\\python.exe' -m pytest -q tests; Pop-Location
Push-Location frontend; npm run build; Pop-Location

# Compose syntax review (use Docker Compose itself where installed)
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.prod.yml config --quiet
```
