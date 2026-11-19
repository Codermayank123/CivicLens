# Environment variables

Copy `.env.example` to the relevant service environment. Never commit real secrets.

| Group | Required in production | Variables |
|---|---|---|
| Runtime | Yes | `APP_ENV`, `DEBUG`, `LOG_LEVEL`, `BACKEND_HOST`, `BACKEND_PORT`, `BACKEND_CORS_ORIGINS` |
| Security | Yes | `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`, `MEDIA_SIGNING_SECRET` |
| MongoDB Atlas | Yes | `MONGODB_URL` (or `MONGO_URI`), `MONGODB_DB_NAME`, pool sizes |
| Object storage | Yes | `STORAGE_BACKEND=s3`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_NAME`, `S3_REGION`, `S3_PUBLIC_URL`, `BACKEND_PUBLIC_URL` |
| Email | Yes | `EMAIL_PROVIDER=brevo`, `BREVO_API_KEY`, `BREVO_SENDER_EMAIL`, `BREVO_SENDER_NAME`, optional `BREVO_WEBHOOK_SECRET` |
| SMS / OTP | Yes | `SMS_PROVIDER=message_central`, `MESSAGE_CENTRAL_CUSTOMER_ID`, `MESSAGE_CENTRAL_AUTH_TOKEN`, `MESSAGE_CENTRAL_BASE_URL`, OTP limits |
| India locations | Yes for structured location routing | `INDIA_LOCATION_DATA_URL` pointing to an approved complete state/district/local-area JSON catalog |
| AI | Yes if AI feature is enabled | Backend: `AI_SERVICE_URL`, `AI_MOCK_MODE=false`; AI service: `AI_MOCK_MODE=false`, `AI_PROVIDER=openai_compatible`, `AI_API_KEY`, `AI_API_BASE_URL`, `AI_TEXT_MODEL`, `AI_VISION_MODEL`, `AI_REVIEW_CONFIDENCE_THRESHOLD` |
| Identity | Only after authorization | `IDENTITY_PROVIDER`, consent version and the relevant UIDAI fields |
| Frontend | Yes | `VITE_API_URL`, `VITE_MAP_TILE_URL`, `VITE_APP_NAME` |

`DEBUG` should be set to `true` or `false`; launcher labels such as `release` are treated as a safe `false`. Production validation fails closed for mock email/SMS/AI, default object-store credentials, unsafe secrets, local MongoDB and non-HTTPS public URLs.

Environment file precedence is service-specific: the root `.env` provides shared development defaults, `backend/.env` overrides backend settings, `ai_service/.env` overrides AI settings, and `frontend/.env.local` contains public Vite settings only. Operating-system/container environment variables remain highest precedence. Compose loads the root file first and the service file second; it does not merge backend or AI secrets into the frontend.

Citizen registration uses `/auth/register/request-otp`, `/auth/register/verify-otp`, then `/auth/register`. Only the final endpoint creates the user account. Email OTP is sent through Brevo’s transactional endpoint; SMS OTP uses Message Central VerifyNow’s `/verification/v3/send` and `/verification/v3/validateOtp` endpoints. Complaint notification emails are persisted with provider acceptance IDs, and Brevo webhook events can update delivery status.
