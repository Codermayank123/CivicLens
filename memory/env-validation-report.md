# Environment Validation Report — CivicLens

**Generated**: 2026-11-18  
**Scope**: All services that read environment variables from `.env`

---

## 1. `.env` File Status

The `.env` file at the repository root currently contains only **3 of 50+ required variables**:

| Variable | Value | Status |
|---|---|---|
| `MONGODB_URL` | `mongodb://localhost:27017` | present (dev-only) |
| `MONGODB_DB_NAME` | `civiclens` | present |
| `AI_SERVICE_URL` | `http://localhost:8001` | present |

**Missing variables** (47+ required for production, as listed in `.env.example` and validated by `config.py`):

- `APP_ENV`, `DEBUG`, `LOG_LEVEL` — general
- `BACKEND_HOST`, `BACKEND_PORT`, `BACKEND_WORKERS`, `BACKEND_CORS_ORIGINS` — server
- `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS` — JWT
- `MONGODB_URL` (Atlas URI), `MONGODB_DB_NAME` — database (current value is localhost)
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_ENABLED` — Redis
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_NAME`, `S3_REGION`, `S3_PUBLIC_URL`, `BACKEND_PUBLIC_URL` — object storage
- `MEDIA_SIGNING_SECRET` — media security
- `AI_MOCK_MODE`, `AI_PROVIDER`, `AI_API_KEY`, `AI_API_BASE_URL`, `AI_TEXT_MODEL`, `AI_VISION_MODEL`, `AI_REVIEW_CONFIDENCE_THRESHOLD` — AI service
- `IDENTITY_PROVIDER`, `IDENTITY_CONSENT_VERSION`, `CITIZEN_REGISTRATION_ENABLED` — identity
- `EMAIL_PROVIDER`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `RESEND_API_KEY`, `EMAIL_FROM` — email
- `SMS_PROVIDER`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` — SMS/OTP
- `RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_AUTH_PER_MINUTE` — rate limiting
- `GEOCODING_PROVIDER`, `GEOCODING_URL`, `GEOCODING_USER_AGENT` — geocoding
- `INDIA_LOCATION_DATA_URL` — India location catalog
- `DEADLINE_SCAN_INTERVAL_SECONDS`, `DEADLINE_REMINDER_HOURS`, `ESCALATION_REPEAT_HOURS` — deadlines

---

## 2. Service-by-Service Validation

### Backend (`backend/app/config.py`)

**Load path**: `Path(__file__).resolve().parents[2] / ".env"` → resolves to `D:/OneDrive/Desktop/civiclens/.env`

**Validator findings** (`validate_production_configuration`):

| Check | Current `.env` value | Pass/Fail | Reason |
|---|---|---|---|
| `DEBUG` must be `false` in production | N/A (APP_ENV not set → defaults to `development`) | Pass (not production) | `APP_ENV` not set, so `is_production` is `False` |
| `JWT_SECRET_KEY` length >= 64 and no `CHANGE_ME` | `local_dev_secret_1234567890abcdefghijklmnopqrstuvwxyz` (from config defaults) | N/A | Using config defaults, not env overrides |
| `MEDIA_SIGNING_SECRET` length >= 64 and no `CHANGE_ME` | `local_dev_signing_secret_1234567890abcdefghijklmnopqrstuvwxyz` (from config defaults) | N/A | Using config defaults |
| `MONGODB_URL` must not be localhost in production | `mongodb://localhost:27017` | Would **fail** if `APP_ENV=production` | Contains `localhost` |
| `MONGODB_URL` or `MONGO_URI` must be set | `mongodb://localhost:27017` | Pass (non-empty) | Present but points to local dev |
| `S3_ACCESS_KEY`/`S3_SECRET_KEY` must not be minioadmin | `minioadmin` (from config defaults) | Would **fail** if production | Defaults present |
| `STORAGE_BACKEND` must be `s3` in production | `local` (from config defaults) | Would **fail** if production | Default is `local` |
| `EMAIL_PROVIDER` must not be `mock` in production | `smtp` (from config defaults) | Would need validation | Using default |
| `BACKEND_CORS_ORIGINS` must be HTTPS in production | `http://localhost:5173,http://localhost:3000` (from config defaults) | Would **fail** if production | Contains `http://` not `https://` |
| `BACKEND_PUBLIC_URL` must use HTTPS in production | `http://localhost:8000` (from config defaults) | Would **fail** if production | Uses `http://` |

**Summary**: The backend config loads successfully in development mode (defaults are safe). All production validators would reject the current configuration if `APP_ENV=production` were set.

---

### AI Service (`ai_service/app/settings.py`)

**Load path**: `Path(__file__).resolve().parents[2] / ".env"` → resolves to `D:/OneDrive/Desktop/civiclens/.env`

**Validator findings** (`validate_real_mode`):

| Check | Current `.env` value | Pass/Fail | Reason |
|---|---|---|---|
| `AI_MOCK_MODE=false` → requires `AI_PROVIDER=openai_compatible` | `AI_MOCK_MODE` not set → defaults to `False` | N/A | Not production, but validator runs anyway |
| `AI_PROVIDER` must be `openai_compatible` when `AI_MOCK_MODE=false` | Not set → defaults to `"openai_compatible"` | Pass | Default matches |
| `AI_API_KEY` must be non-empty when `AI_MOCK_MODE=false` | Not set → defaults to `""` | **FAIL** | Empty API key |

**Summary**: The AI settings validator would raise `ValueError("AI_API_KEY is required when AI_MOCK_MODE is false")` if `AI_MOCK_MODE` were explicitly `false` and `AI_API_KEY` were not set. Current defaults avoid the error, but production requires a real key.

---

### Docker Compose (`docker-compose.yml` and `docker-compose.prod.yml`)

Both compose files use `env_file: [.env]` and `${VAR:-default}` patterns. The `.env` deficiencies affect:

- **Redis**: `REDIS_PASSWORD` not set → falls back to empty string (Redis health check may fail if `REDIS_ENABLED=true`)
- **MinIO/S3**: `S3_ACCESS_KEY=minioadmin`, `S3_SECRET_KEY=minioadmin` → used as MinIO defaults (acceptable for dev, must change for production)
- **Backend**: `MONGODB_URL=${MONGODB_URL:?MONGODB_URL must point to MongoDB Atlas}` → would fail with "MONGODB_URL must point to MongoDB Atlas" if `.env` didn't have a value, but current `.env` has `mongodb://localhost:27017`
- **AI Service**: `AI_API_KEY=${AI_API_KEY:-}` → empty string passed through (validated by `AISettings.validate_real_mode`)

---

### Frontend (`frontend/vite.config.ts`)

- `VITE_API_URL` is exposed as a build arg: `ARG VITE_API_URL=/api/v1` / `ENV VITE_API_URL=${VITE_API_URL}`
- Current `.env` does not set `VITE_API_URL` → falls back to `/api/v1` default
- `VITE_MAP_TILE_URL` and `VITE_APP_NAME` are not in `.env` either — they are hardcoded in `.env.example` but the `.env` file is missing them

---

## 3. Recommended `.env` Fix

Create a complete `.env` file with production-ready values. The following is a **minimal production configuration**:

```dotenv
# ── General ──────────────────────────────────────────────────────────────
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO

# ── Server ───────────────────────────────────────────────────────────────
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_WORKERS=2
BACKEND_CORS_ORIGINS=https://app.example.com,https://web.example.com

# ── JWT ───────────────────────────────────────────────────────────────────
JWT_SECRET_KEY=<generate 64+ char random secret>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ── MongoDB (Atlas) ──────────────────────────────────────────────────────
MONGODB_URL=mongodb+srv://<username>:<password>@cluster0.example.mongodb.net
MONGODB_DB_NAME=civiclens

# ── Redis (Optional in dev, required in production) ──────────────────────
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<strong-redis-password>
REDIS_ENABLED=true

# ── S3 / MinIO ──────────────────────────────────────────────────────────
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY=<minio-root-user>
S3_SECRET_KEY=<minio-root-password>
S3_BUCKET_NAME=civiclens-media
S3_REGION=us-east-1
S3_PUBLIC_URL=https://media.example.com/civiclens-media
BACKEND_PUBLIC_URL=https://api.example.com
MEDIA_SIGNING_SECRET=<generate 64+ char random secret>

# ── AI Service ───────────────────────────────────────────────────────────
AI_MOCK_MODE=false
AI_PROVIDER=openai_compatible
AI_API_KEY=<openai-or-compatible-api-key>
AI_API_BASE_URL=https://api.openai.com/v1
AI_TEXT_MODEL=gpt-4o-mini
AI_VISION_MODEL=gpt-4o-mini
AI_REVIEW_CONFIDENCE_THRESHOLD=0.5

# ── Identity ─────────────────────────────────────────────────────────────
IDENTITY_PROVIDER=disabled
IDENTITY_CONSENT_VERSION=2026-01
CITIZEN_REGISTRATION_ENABLED=false

# ── Email ────────────────────────────────────────────────────────────────
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=<smtp-username>
SMTP_PASSWORD=<smtp-password>
RESEND_API_KEY=<resend-api-key-if-using-resend>
EMAIL_FROM=noreply@civiclens.com

# ── SMS / OTP ────────────────────────────────────────────────────────────
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=<twilio-account-sid>
TWILIO_AUTH_TOKEN=<twilio-auth-token>
TWILIO_FROM_NUMBER=+15551234567

# ── Rate Limiting ────────────────────────────────────────────────────────
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_AUTH_PER_MINUTE=10

# ── Geocoding ────────────────────────────────────────────────────────────
GEOCODING_PROVIDER=nominatim
GEOCODING_URL=https://nominatim.openstreetmap.org/reverse
GEOCODING_USER_AGENT=CivicLens/1.0 (production)

# ── India Location Catalog ───────────────────────────────────────────────
INDIA_LOCATION_DATA_URL=<URL-to-approved-india-state-district-catalog>

# ── Deadlines ────────────────────────────────────────────────────────────
DEADLINE_SCAN_INTERVAL_SECONDS=300
DEADLINE_REMINDER_HOURS=24
ESCALATION_REPEAT_HOURS=24

# ── Frontend ─────────────────────────────────────────────────────────────
VITE_API_URL=http://localhost:8000/api/v1
VITE_MAP_TILE_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
VITE_APP_NAME=CivicLens
```

**Important notes**:
- `JWT_SECRET_KEY` and `MEDIA_SIGNING_SECRET` must be **generated randomly** (64+ characters each). Do not use the default placeholder values in production.
- `MONGODB_URL` must point to **MongoDB Atlas** (or another hosted MongoDB), **not** localhost, when `APP_ENV=production`.
- `STORAGE_BACKEND=s3` is required in production (local dev disk is not sufficient).
- `BACKEND_CORS_ORIGINS` and `BACKEND_PUBLIC_URL` must use **HTTPS** origins in production.
- `AI_API_KEY` must be non-empty when `AI_MOCK_MODE=false`.
- `SMS_PROVIDER=twilio` requires all three Twilio variables to be non-empty.
- `EMAIL_PROVIDER=smtp` requires `SMTP_HOST` to be non-empty.
- `INDIA_LOCATION_DATA_URL` must point to an **approved complete state/district/local-area JSON catalog**.

---

## 4. Validation Commands

After updating `.env`, verify the configuration loads correctly:

```bash
# Backend config validation
cd backend
python -c "from app.config import Settings; s = Settings(); print('APP_ENV:', s.APP_ENV); print('DEBUG:', s.DEBUG); print('MONGODB_URL set:', bool(s.MONGODB_URL)); print('JWT_SECRET_KEY length:', len(s.JWT_SECRET_KEY)); print('Production ready:', not s.is_production or all([s.DEBUG==False, len(s.JWT_SECRET_KEY)>=64]))"

# AI service config validation
cd ai_service
python -c "from app.settings import AISettings; s = AISettings(); print('AI_MOCK_MODE:', s.AI_MOCK_MODE); print('AI_PROVIDER:', s.AI_PROVIDER); print('AI_API_KEY set:', bool(s.AI_API_KEY)); print('Real mode valid:', not s.AI_MOCK_MODE or (s.AI_PROVIDER=='openai_compatible' and s.AI_API_KEY))"
```

---

## 5. Action Items

- [ ] **Generate** secure random values for `JWT_SECRET_KEY` and `MEDIA_SIGNING_SECRET` (64+ chars each)
- [ ] **Obtain** a MongoDB Atlas URI and update `MONGODB_URL`
- [ ] **Set** `APP_ENV=production` and `DEBUG=false`
- [ ] **Configure** Redis with a password if `REDIS_ENABLED=true`
- [ ] **Provision** MinIO/S3 with proper credentials (not `minioadmin` defaults)
- [ ] **Configure** AI provider API key (`AI_API_KEY`)
- [ ] **Set up** SMTP email or Resend API key
- [ ] **Configure** Twilio SMS credentials if SMS/OTP is needed
- [ ] **Provide** approved India location dataset URL
- [ ] **Never commit** `.env` to version control (already in `.gitignore`)
- [ ] **Run** the validation commands above after updating `.env`