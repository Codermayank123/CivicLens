# CivicLens feature audit

Status at 15 November 2026. `Complete` means implemented and locally exercised; `Provider-gated` requires approved credentials or contractual onboarding; `Planned` is not represented as an available feature.

| Area | Status | Evidence / constraint |
|---|---|---|
| Authentication, JWT refresh, RBAC | Complete | Citizen, officer, field-staff and admin roles are implemented. |
| Complaint reporting, media validation, history, comments | Complete | MongoDB-backed lifecycle, signed managed-media checks and audit events. |
| Assignment, field task and citizen verification | Complete | Live test completed `submitted → assigned → in_progress → resolved → closed`. |
| Dashboards, maps, department/category APIs | Complete | Role pages use protected API routes; Leaflet map uses configured tile URL. |
| Offline queue | Complete | IndexedDB queue and online sync manager are present. |
| Email verification and password reset | Complete locally | Mock/SMTP/Resend adapters; real delivery requires provider configuration. |
| Public landing indicators | Complete | `/api/v1/public/platform` exposes aggregate counts and sanitized resolutions only. |
| AI text + evidence verification | Provider-gated | The AI service now supports OpenAI-compatible text/vision verification, video frame sampling when OpenCV is installed, duplicate/suspicion signals, and human-review flags. Local mode remains explicitly mock and never rejects a submission. |
| UIDAI / DigiLocker verification | Provider-gated | Development identity flow only. UIDAI authorization and DigiLocker requester approval are external prerequisites. |
| SMS OTP / staff MFA | Planned | No SMS provider or second-factor implementation is currently enabled. |
| In-app/email notifications | Complete locally | Durable MongoDB notifications are emitted across complaint transitions; the frontend refreshes the inbox live and SMTP/Resend delivery is provider-gated. |
| Civic Hero rewards and challenges | Complete | Idempotent validated point ledger, tiers, leaderboards, badges, challenge submissions, reviews, and hashed certificates are MongoDB-backed. |
| Civic heatmap, accountability, neighbourhood alerts | Complete | Privacy-safe hotspot aggregation, department metrics, nearby active complaint lookup, and community support are exposed through live APIs and role views. |
| Production deployment | Conditional | Production settings reject mock AI, insecure secrets, local MongoDB, local storage and unapproved identity registration. |

## Audit conclusion

Core civic workflows are functional locally. Provider-gated and planned capabilities must remain visibly unavailable until their external prerequisites and end-to-end tests are complete.
