# CivicLens email, SMS OTP, and complaint notification integration

Implementation status: complete in code and mocked-test coverage. Brevo and Message Central credentials are configured locally; real delivery remains unverified because sending requires explicit approval.

## Implemented APIs

- `POST /api/v1/auth/register/request-otp`
- `POST /api/v1/auth/register/verify-otp`
- `POST /api/v1/auth/register`
- `PATCH /api/v1/users/me/notification-preferences`
- `POST /api/v1/notifications/webhooks/brevo`
- Existing complaint status, assignment, comment, reopen, and media APIs now drive notification delivery.

Registration stores only a password hash, session-token hash, and email OTP hash. Message Central OTPs are generated and verified by VerifyNow; only the provider verification ID is stored. Sessions expire, enforce resend cooldown and attempt limits, invalidate superseded sessions, and are consumed atomically before account creation.

## Providers

Brevo uses `POST https://api.brevo.com/v3/smtp/email` with the `api-key` header, branded HTML/text templates, and optional base64 attachments. Message Central VerifyNow uses `POST /verification/v3/send` and `GET /verification/v3/validateOtp` under `MESSAGE_CENTRAL_BASE_URL`, with `authToken` and Indian `+91` number normalization.

References: [Brevo transactional email API](https://developers.brevo.com/docs/send-a-transactional-email), [Message Central VerifyNow India API](https://www.messagecentral.com/en-in/product/verify-now/api-india).

## Environment variables

Backend-only variables:

```text
EMAIL_PROVIDER=brevo
BREVO_API_KEY=
BREVO_SENDER_EMAIL=
BREVO_SENDER_NAME=CivicLens
BREVO_WEBHOOK_SECRET=
SMS_PROVIDER=message_central
MESSAGE_CENTRAL_CUSTOMER_ID=
MESSAGE_CENTRAL_AUTH_TOKEN=
MESSAGE_CENTRAL_BASE_URL=https://cpaas.messagecentral.com
OTP_EXPIRY_MINUTES=10
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_SESSION_TTL_MINUTES=15
OTP_MAX_ATTEMPTS=5
OTP_MAX_REQUESTS_PER_WINDOW=5
ALLOW_RESOLUTION_WITHOUT_EVIDENCE=false
```

Do not place these variables in root shared configuration or any `VITE_*` file.

## Complaint notifications and evidence

Notifications are generated for submission, assignment, review/status changes, remarks/comments, rejection, resolution, and reopening. Email delivery records distinguish `accepted`, `delivered`, `opened`, `clicked`, and `failed` provider states. Brevo webhook events update delivery state. Notification preferences and deterministic dedupe keys prevent duplicate channel deliveries.

Resolution requires non-empty remarks and stored image evidence before the complaint state changes. Multiple images are supported, validated by content signature, associated with the complaint in MongoDB, and attached to resolution emails when the configured size limit allows. Otherwise the email contains the secure CivicLens tracking link. Signed media URLs remain required; unrestricted storage URLs are not exposed.

## Files changed

- Backend configuration, authentication routes/services, user preferences, verification model, notification model/service/routes, email providers/templates, SMS providers, complaint resolution/evidence handling, storage URL handling, and MongoDB indexes.
- Frontend registration OTP flow, authentication client, officer resolution upload workflow, complaint details, and complaint types.
- Environment examples, `ENVIRONMENT_VALIDATION.md`, this report, and automated backend/provider/notification/resolution tests.

## Verification commands

```powershell
# Backend automated tests
Push-Location backend
& '..\\.venv\\Scripts\\python.exe' -m pytest -q tests -p no:cacheprovider --basetemp=.pytest-tmp-local
Pop-Location

# Frontend checks
Push-Location frontend
npm run type-check
npm test -- --run
npm run build
Pop-Location

# Provider configuration presence, without printing values
& '.venv\\Scripts\\python.exe' -c "from dotenv import dotenv_values; v=dotenv_values('backend/.env'); print('brevo=', bool(v.get('BREVO_API_KEY') and v.get('BREVO_SENDER_EMAIL') and v.get('BREVO_SENDER_NAME'))); print('message_central=', bool(v.get('MESSAGE_CENTRAL_CUSTOMER_ID') and v.get('MESSAGE_CENTRAL_AUTH_TOKEN') and v.get('MESSAGE_CENTRAL_BASE_URL')))"
```

Real-provider tests must be run only after setting the backend variables in a secure deployment environment. A provider test is successful only when Brevo returns a message ID and Message Central returns a verification ID followed by a successful verification response; HTTP acceptance alone is not delivery confirmation.

## Test results

- Backend suite: 43 passed after the implementation and test updates.
- AI-service suite: 4 passed.
- Provider contract tests: Brevo payload/attachment shape, VerifyNow send/validate parameters, and provider rejection handling covered with mocks.
- Registration tests: email OTP, SMS OTP, hashed OTP/session data, expiry/attempt boundaries, account-creation restriction, and single-use session behavior covered.
- Complaint tests: resolution remarks, multiple stored photographs, failed evidence paths, signed-media authorization, notification attachments, provider failures, and duplicate notification suppression covered.
- Frontend: type-check, Vitest, and production build passed.
- Real Brevo delivery: not run; explicit approval and a destination are required.
- Real Message Central delivery: not run; explicit approval and a verified Indian destination are required.
