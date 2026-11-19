# Security audit

## Implemented controls

- Argon2id password hashes, short-lived JWT access tokens and httpOnly refresh-cookie flow.
- Role-based route guards and server-side ownership/department checks.
- Security headers, CORS configuration, rate limits, request IDs and structured audit records.
- MongoDB indexes and soft deletion; evidence URLs are restricted to managed storage.
- Production configuration rejects placeholder secrets, mock services, unsafe storage and non-HTTPS public settings.

## Required before production

1. Store all secrets in a managed secret vault and rotate the local defaults.
2. Enforce HTTPS at the reverse proxy; set secure cookie attributes there.
3. Use a private S3 bucket, least-privilege IAM, malware scanning and retention rules for uploads.
4. Run dependency, SAST, secret-scanning and penetration tests in CI/release gates.
5. Complete a privacy impact assessment and formal approval for UIDAI/DigiLocker flows.
6. Add MFA for staff roles and a real-time transport authorization design before enabling chat.

This is an engineering assessment, not a compliance certification.
