# Bug report and remediation log

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| CL-001 | High | Demo accounts were insert-only, so an old password hash could leave the published local credentials unusable. | Seed now updates only the four named development accounts and preserves MongoDB's immutable `_id`. |
| CL-002 | Medium | The authenticated notification bell targeted `/notifications`, but no route existed. | Added a protected notifications page using the existing notification API. |
| CL-003 | Medium | The landing page used decorative figures instead of service data. | Added a privacy-safe public aggregate endpoint and connected the landing page to it. |
| CL-004 | Medium | A startup environment variable `DEBUG=release` prevents Pydantic from parsing settings. | Local runner explicitly starts development with `DEBUG=true`; use `true` or `false` only. |
| CL-005 | Medium | Field-staff assignment queried the wrong suspension field. | Corrected the MongoDB predicate to `is_suspended`. |

No unresolved critical defect was found in the locally tested complaint lifecycle. External-service readiness is tracked in `FEATURE_AUDIT.md`.
