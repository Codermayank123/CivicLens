# CivicLens UI / AI Redesign Report

Date: 2026-11-18

## Outcome

CivicLens is running locally with the existing architecture preserved:

- Frontend: `http://127.0.0.1:5173` — HTTP 200
- Backend: `http://127.0.0.1:8000` — HTTP 200
- AI service: `http://127.0.0.1:8001` — HTTP 200
- MongoDB Atlas: startup ping and index initialization succeeded in the running backend log.

The configured real AI provider was actually called. It returned HTTP 503, so CivicLens now reports provider unavailability and routes the case to human review. No fake category or confidence score is generated.

## Implemented changes

### UI and theme

- Added `frontend/src/components/visuals/CivicLensScene.tsx`, a responsive CSS 3D civic scene with depth, glass layers, map pins, floating status cards, ambient lighting, and reduced-motion support.
- Added premium dashboard styling to citizen, officer, and admin dashboards: ambient gradients, depth, hover lift, and responsive layout behavior.
- Preserved the existing heritage illustration as a visual fallback beneath the 3D scene.
- Removed the High Contrast control and document class from the active UI state. The application now has only Light and Dark themes; the saved theme or OS preference is used on first visit.
- Dark mode now applies to the full document rather than only changing the page background.
- Added translation coverage for landing, authentication, complaint, dashboard, and notification headings/descriptions. The legacy static-text bridge translates known static JSX copy without changing user-entered or API-provided content.
- Added a searchable category field and removed automatic selection of the first category. Manual category selection always remains available.

### AI triage

The verified path is:

`CreateComplaint` → backend `/api/v1/ai/suggest` → AI service `/classify-text` → configured provider.

Changes:

- Provider confidence is now optional and includes `confidence_status: available | unavailable`.
- Missing provider confidence is no longer converted to `0.5`, `0.4`, or `0.0` as if it were a model score.
- Backend fallback returns `confidence: null`, `confidence_status: unavailable`, `provider_unavailable: true`, and a human-review message.
- The frontend displays “Provider confidence unavailable” instead of displaying a fabricated percentage.
- Provider outages do not block manual complaint submission or manual category choice.
- Existing mock-provider behavior remains limited to automated test mode and is not used as a production fallback.

## Files added or materially changed

- `frontend/src/components/visuals/CivicLensScene.tsx`
- `frontend/src/styles/index.css`
- `frontend/src/store/uiStore.ts`
- `frontend/src/components/layout/Navbar.tsx`
- `frontend/src/pages/LandingPage.tsx`
- `frontend/src/pages/CreateComplaint.tsx`
- `frontend/src/pages/NotificationsPage.tsx`
- `frontend/src/pages/CitizenDashboard.tsx`
- `frontend/src/pages/OfficerDashboard.tsx`
- `frontend/src/pages/AdminDashboard.tsx`
- `frontend/src/types/index.ts`
- `ai_service/app/schemas.py`
- `ai_service/app/providers/openai_compatible.py`
- `backend/app/services/ai_client.py`
- `CIVICLENS_UI_AI_REDESIGN_REPORT.md`

Earlier environment, OTP, CORS, manifest, and language changes remain preserved in the existing dated backup directories.

## Validation results

Passed:

- Frontend type-check: passed.
- Frontend Vitest suite: 3 tests passed.
- Frontend production build: passed; Vite transformed 2,422 modules.
- AI-service pytest suite: 4 tests passed.
- Backend AI pytest subset: 3 tests passed.
- Backend health probe: HTTP 200.
- AI-service health probe: HTTP 200.
- Frontend HTTP probe: HTTP 200.
- Live backend triage probe: returned `confidence: null`, `confidence_status: unavailable`, and `provider_unavailable: true` when the provider returned 503.
- Live AI-service provider probe: returned HTTP 503 with a sanitized “temporarily unavailable” response.

The complaint integration test file was started against the Atlas-backed environment but did not finish within the allowed run window and was stopped. It is not reported as passing.

Commands:

```powershell
cd frontend
npm run type-check
npm test -- --run
npm run build

cd ..\ai_service
..\.venv\Scripts\python.exe -m pytest -q

cd ..\backend
..\.venv\Scripts\python.exe -m pytest -q tests/test_ai.py
..\.venv\Scripts\python.exe -m pytest -q tests/test_complaints.py

curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8001/health
curl.exe http://127.0.0.1:5173
```

Run Atlas-dependent commands with network access in the deployment environment. Do not replace Atlas with localhost merely to make tests pass.

## Remaining production requirements

1. Resolve the configured real AI provider’s HTTP 503 and rerun the provider integration test. The current model/provider combination is not verified as operational.
2. Run the full backend complaint integration suite to completion against an isolated test database or a controlled Atlas test database.
3. Review the existing Vite warning that the heritage hero asset is approximately 3 MB and is not precached by the PWA build; optimize or intentionally accept it before production.
4. Keep production secrets in the service-specific environment files/secrets manager. Never move AI or database secrets into Vite variables.
5. Do not claim production readiness until the real AI provider and all required external integrations return confirmed provider responses.

No secret values, API keys, database URIs, or tokens are included in this report.
