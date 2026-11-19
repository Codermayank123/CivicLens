# Testing report

## Automated checks

- Backend: `pytest backend/tests -q --disable-warnings --maxfail=1 --basetemp=backend/.tmp/pytest-run` — 28 passed.
- Backend static import check: `ruff check backend/app backend/seeds backend/tests --select F` — passed.
- Frontend: lint, type-check, Vitest (3 tests) and production build — passed before the final heritage-page addition; rerun commands listed below after any further change.

## Live integration test

Performed against local MongoDB and `http://127.0.0.1:8000` on 15 November 2026:

1. Health/readiness and public platform endpoint responded successfully.
2. Refreshed development citizen, officer and field-staff accounts authenticated.
3. Complaint `POT-736332` was assigned by an officer, moved to `in_progress`, then `resolved` by field staff.
4. The reporting citizen approved the resolution; final status was `closed`.

## Repeat commands

```powershell
$env:DEBUG='true'; & .\.venv\Scripts\python.exe -m pytest backend/tests -q
& .\.venv\Scripts\ruff.exe check backend/app backend/seeds backend/tests --select F
Push-Location frontend; npm run lint; npm run type-check; npm run test -- --run; npm run build; Pop-Location
```
