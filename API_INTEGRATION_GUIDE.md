# API integration guide

## Local endpoints

- Frontend: `http://127.0.0.1:5173`
- Backend OpenAPI: `http://127.0.0.1:8000/docs`
- AI service OpenAPI: `http://127.0.0.1:8001/docs`
- Public aggregate indicators: `GET /api/v1/public/platform`

The frontend base URL is `VITE_API_URL`. Protected endpoints use `Authorization: Bearer <access token>`.

## Provider onboarding

1. MongoDB: create a least-privilege database user and a TLS connection URI, then set `MONGODB_URL` and `MONGODB_DB_NAME`.
2. Storage: configure a private S3-compatible bucket, least-privilege access key, bucket CORS, and signed media URL settings. Set `STORAGE_BACKEND=s3` for production.
3. Email: set `EMAIL_PROVIDER=resend` with `RESEND_API_KEY`, or provide SMTP host, port, user and password. Verify `EMAIL_FROM` in the chosen provider.
4. AI: point `AI_SERVICE_URL` to a deployed AI service and set `AI_MOCK_MODE=false` only after authenticated model calls, validation and human-review thresholds are tested.
5. UIDAI: production Aadhaar authentication/e-KYC cannot be enabled from an ordinary API key. Apply through the authorized ecosystem, use the test/sandbox materials where eligible, retain consent records, and keep citizen registration disabled until the approved flow passes end-to-end. See [UIDAI Developer Section](https://www.uidai.gov.in/en/ecosystem/authentication-devices-documents/developer-section.html).
6. DigiLocker: register the organization as a requester/entity, implement the documented OAuth 2.0 authorization and bearer-token flow, verify issuer/document policy and HMAC integrity, and store only consented minimum data. See [DigiLocker Entity Resources](https://entity.digilocker.gov.in/web/resources) and the [Requester API specification](https://entity.digilocker.gov.in/assets/img/Requester%20-%20Entity%20Locker%20API%20Specification_28_11_24.pdf).

SMS OTP, WebSocket chat and production AI vision are not presently implemented; do not add credentials or UI claims for them as if they were active.
