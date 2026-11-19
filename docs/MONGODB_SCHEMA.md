# CivicLens MongoDB schema

MongoDB is the only primary datastore. IDs are application-generated UUID strings stored as the document `_id`; no API returns Mongo's internal IDs. Timestamps are UTC datetimes.

## Collections and indexes

| Collection | Purpose | Required indexes |
| --- | --- | --- |
| `users` | citizens, officers, field staff, admins | unique `email`; `department_id`; `roles`; `is_active`; `civic_points` |
| `refresh_tokens` | hashed, revocable sessions | unique `token_hash`; `user_id`; TTL `expires_at` |
| `departments` | government departments | unique `code`; unique `name` |
| `complaint_categories` | civic taxonomy | unique `slug`; `department_id` |
| `complaints` | complaint lifecycle, AI advisory verification, support count, and GeoJSON location | unique `public_id`; `2dsphere location`; status/priority/category/department/staff/creator/created_at |
| `complaint_media` | media metadata and evidence references | `complaint_id` |
| `complaint_assignments` | assignment history | `complaint_id`, `created_at` |
| `complaint_status_history` | immutable state transitions | `complaint_id`, `created_at` |
| `complaint_comments` | public/internal discussion | `complaint_id`, `created_at` |
| `complaint_verifications` | citizen feedback and rating | `complaint_id`, `verified_by` |
| `complaint_duplicates` | duplicate review records | `complaint_id`, `confirmed` |
| `ai_predictions` | advisory AI traceability | `complaint_id`, `prediction_type` |
| `notifications` | in-app notifications | `user_id + is_read`; `created_at` |
| `points_transactions` | Civic Hero point ledger with idempotent validated awards | `user_id + created_at`; `action_type`; unique sparse `user_id + action_type + reference_id` |
| `community_challenges` | challenge definitions | `is_active`; `start_date + end_date` |
| `challenge_participations` | citizen challenge enrolment | unique `challenge_id + user_id`; `user_id` |
| `challenge_submissions` | human-reviewed challenge evidence and awards | `challenge_id + user_id`; `status` |
| `certificates` | hashed digital Civic Hero certificates | `user_id + issued_at`; unique `certificate_hash` |
| `identity_verification_sessions` | short-lived provider sessions | `user_id`; `status`; TTL `expires_at` |
| `audit_logs` | append-only security audit trail | `actor_id`; `action`; `resource_type + resource_id`; `created_at` |

## Data minimization

Identity sessions store provider state, consent version, expiry, and opaque outcome fingerprints only. CivicLens does not persist Aadhaar numbers, OTPs, biometrics, or raw identity documents. Provider adapters must verify signed responses themselves before changing `identity_verified`.

## Environment separation and backups

Use a different `MONGODB_DB_NAME` and preferably a different Atlas project for development, staging, and production. Enable Atlas continuous backups or scheduled `mongodump` backups, encrypt them, test restoration into an isolated database, and record the restore date and checksum. Never run a migration that drops collections without a reviewed backup and rollback plan.
