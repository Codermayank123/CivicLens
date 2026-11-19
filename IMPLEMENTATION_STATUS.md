# CivicLens — Implementation Status (2026-11-19)

## Features implemented / fixed

1. **Demo login** — Seeded and verified all four accounts (`Demo@12345`):
   - `citizen@example.com` → citizen
   - `officer@example.com` → officer
   - `fieldstaff@example.com` → field_staff
   - `admin@example.com` → admin
2. **AI auto-triage UX** — Removed manual category selection from citizen complaint submission. Category, department, urgency, and confidence are assigned automatically from AI (with officer review when uncertain/unavailable).
3. **AI client timeout** — Backend AI HTTP timeout raised from 4s to configurable `AI_CLIENT_TIMEOUT_SECONDS` (default 60s). Short timeout was a root cause of false “provider unavailable” results.
4. **AI relevance logic** — Low/missing confidence no longer forces `is_relevant=false`; uncertain cases route to human review instead.
5. **Provider 503 retries** — OpenAI-compatible provider retries temporary Gemini 503 / timeout up to 3 times before failing closed.
6. **Confidence honesty** — Missing confidence stays `null` / `unavailable` (not fabricated `0%`).
7. **Dark mode** — Brand CSS tokens updated; navbar and login adapted for light/dark; high-contrast remains removed from UI controls.
8. **Branding** — Unique SVG CivicLens mark (lotus + lens) with palette Royal Plum / Ivory / Terracotta / Forest / Gold / Charcoal and tagline “Your Voice. Our Collective Progress.”
9. **Seed** — Added `other` (`Needs Officer Review`) category for AI fallback routing.
10. **Tests** — Forced `EMAIL_PROVIDER=mock` / `SMS_PROVIDER=mock` in pytest so live Brevo credentials from `.env` cannot break auth tests.

## Bugs fixed

| Bug | Root cause | Fix |
|---|---|---|
| Demo login unreliable | Password hashes could drift | Seed upserts demo accounts with `Demo@12345` |
| AI always unavailable / null confidence | Backend timeout 4s + Gemini 503 demand | 60s timeout + retries + honest unavailable state |
| Manual category required | Old CreateComplaint UI | Auto-triage only; no category dropdown |
| Auth tests failed with 503 | Live Brevo from `.env` | Autouse mock email/SMS in conftest |
| TS error on `department_name` | Type incomplete | Extended `ComplaintCategory` |

## Files modified (this session)

- `backend/app/config.py`
- `backend/app/services/ai_client.py`
- `backend/seeds/seed_data.py`
- `backend/tests/conftest.py`
- `ai_service/app/providers/openai_compatible.py`
- `ai_service/app/main.py`
- `frontend/src/pages/CreateComplaint.tsx`
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/components/layout/Navbar.tsx`
- `frontend/src/components/brand/CivicLensMark.tsx`
- `frontend/src/styles/index.css`
- `frontend/src/types/index.ts`

## Tests executed and results

| Suite | Result |
|---|---|
| AI service pytest | **4 passed** |
| Backend `test_auth.py` + `test_ai.py` | **6 passed** |
| Frontend Vitest | **3 passed** |
| Frontend `tsc --noEmit` | **passed** |
| Frontend production build | **passed** (2422 modules) |
| Live demo login (4 roles) | **all OK** |
| Live `/api/v1/ai/suggest` | Provider returned busy/unavailable after retries (Gemini HTTP 503 high demand). CivicLens correctly returned `confidence: null`, `confidence_status: unavailable`, `provider_unavailable: true`, human-review message — **no fake score**. |

## Build status

- Frontend production build: **success**
- Services started locally: backend `:8000`, AI `:8001`, frontend `:5173`

## Remaining issues / external credentials

1. **Gemini provider capacity** — Configured model `gemini-3.8-flash` is correct per Google’s API, but currently returns HTTP 503 (“high demand”). CivicLens retries then fails closed to human review. Real successful inference depends on Google API availability; no silent mock fallback in real mode.
2. **Email OTP in non-test environments** — `.env` uses Brevo; live registration OTP requires a valid Brevo API key/sender that is accepted (recent tests saw HTTP 403 from Brevo when not mocked).
3. **SMS OTP** — Requires a configured SMS provider; mock is used in automated tests.
4. **Government identity verification** — Production registration / UIDAI-authorized verification remains gated until credentials and legal authorization exist.
5. **Hero image size** — `civiclens-heritage-hero.png` (~3 MB) exceeds PWA precache limit; optimize for mobile performance.
6. **Multilingual coverage** — Navigation/common strings are translated; some complaint-form helper copy remains English and should be expanded in i18n.

## Honest readiness note

CivicLens is **not** production-ready for public citizen data until: Gemini (or approved AI provider) returns stable non-503 responses under load, Brevo/SMS delivery is verified end-to-end, and government-ID verification authorization is complete. Demo login, complaint workflows, dark mode branding, and AI failure handling are working as designed.
