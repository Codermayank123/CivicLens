# CivicLens — API Specification (v1)

Base URL: `http://localhost:8000/api/v1`

---

## 1. Standard Response Envelope

All API v1 responses adhere to a consistent JSON envelope:

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  },
  "message": "Operation completed successfully",
  "request_id": "a98444a1-8d2a-45c1-90be-e2bc9166f21c"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "title",
      "issue": "Title must be at least 5 characters"
    }
  },
  "request_id": "a98444a1-8d2a-45c1-90be-e2bc9166f21c"
}
```

---

## 2. Authentication Endpoints (`/auth`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register a new user | No |
| `POST` | `/auth/login` | Authenticate user and receive JWT tokens | No |
| `POST` | `/auth/refresh` | Rotate and issue new access token | No (Refresh token in cookie/body) |
| `POST` | `/auth/logout` | Revoke refresh token | Yes |
| `POST` | `/auth/verify-email` | Verify an email token without exposing the token in storage | No |
| `POST` | `/auth/forgot-password` | Request a generic password reset email | No |
| `POST` | `/auth/reset-password` | Consume a password reset token | No |
| `GET` | `/auth/me` | Fetch authenticated user profile | Yes |

---

## 3. Complaints Endpoints (`/complaints`)

| Method | Endpoint | Description | Roles Allowed |
| :--- | :--- | :--- | :--- |
| `GET` | `/complaints` | Filter and paginate complaints | Public / Authenticated |
| `POST` | `/complaints` | Create a new complaint | Citizen, Admin |
| `GET` | `/complaints/my` | Get current citizen's complaints | Authenticated |
| `GET` | `/complaints/assigned-to-me` | Get tasks assigned to field staff | Officer, Field Staff |
| `GET` | `/complaints/{id_or_public_id}`| Get complaint details | Public / Authenticated |
| `PATCH`| `/complaints/{id}/status` | Transition complaint lifecycle status | Officer, Field Staff, Admin |
| `PATCH`| `/complaints/{id}/assign` | Assign to department / staff | Officer, Admin |
| `POST` | `/complaints/{id}/verify` | Citizen verifies resolution (approves/reopens)| Creator, Admin |
| `POST` | `/complaints/{id}/reopen` | Appeal a resolved or closed complaint | Creator, Admin |
| `POST` | `/complaints/{id}/comments` | Add discussion update | Authenticated |
| `POST` | `/complaints/duplicates/check` | Check duplicate candidates | Public / Authenticated |

---

## 4. Analytics Endpoints (`/analytics`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/analytics/overview` | High-level KPIs, distributions, and 30-day trends | Admin |
| `GET` | `/analytics/heatmap` | Geospatial points with intensity coordinates | Admin |

---

## 5. Metadata & Master Data Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/departments` | List all active municipal departments |
| `GET` | `/categories` | List complaint categories with icons and parent departments |
| `GET` | `/users/staff` | List field staff and officers |
| `POST`| `/media/upload` | Upload photos and video evidence |
| `POST`| `/ai/suggest` | Real-time AI auto-triage for categories and urgency |
