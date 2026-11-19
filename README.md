# DocTapp backend

The backend runs Django REST Framework with email-based authentication and
rotating, blacklistable SimpleJWT refresh tokens.

## Run with Docker

```shell
docker compose up --build
docker compose exec backend python manage.py migrate
docker compose exec backend pytest
```

## Authentication API

Registering publicly always creates an active `PATIENT`; `DOCTOR` and
`ASSISTANT` accounts must be created or approved by an administrator.

```shell
curl -X POST http://localhost:8000/api/v1/accounts/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"patient@example.com","password":"SecurePass123!","first_name":"Ada","last_name":"Patient"}'
```

```json
{
  "id": "uuid",
  "email": "patient@example.com",
  "first_name": "Ada",
  "last_name": "Patient",
  "phone_number": "",
  "role": "PATIENT",
  "account_status": "ACTIVE",
  "profile_image": null,
  "created_at": "2026-11-14T20:48:12+0600"
}
```

Login returns `access` and `refresh` tokens:

```shell
curl -X POST http://localhost:8000/api/v1/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"patient@example.com","password":"SecurePass123!"}'
```

Send the access token as `Authorization: Bearer <access>` to `GET /api/v1/accounts/me/`,
`PATCH /api/v1/accounts/me/`, and `POST /api/v1/accounts/change-password/`.
Refreshing at `/api/v1/accounts/token/refresh/` rotates the refresh token.
Posting the refresh token to `/api/v1/accounts/logout/` blacklists it.

Password recovery uses `/api/v1/accounts/password-reset/` and
`/api/v1/accounts/password-reset/confirm/`. The request endpoint returns the
same response whether or not the email exists.

OpenAPI is available at `/api/schema/`, with Swagger UI at `/api/docs/`.

## Patient, doctor, and hospital APIs

- `GET/PATCH /api/v1/patients/me/`
- `GET /api/v1/patients/{id}/` (own profile only)
- `GET /api/v1/doctors/`
- `GET /api/v1/doctors/{id}/`
- `GET/PATCH /api/v1/doctors/me/`
- `GET/POST /api/v1/doctors/me/assistants/`
- `DELETE /api/v1/doctors/me/assistants/{id}/`
- `GET /api/v1/assistants/me/doctors/`
- `GET/POST /api/v1/hospitals/`
- `GET/PATCH/DELETE /api/v1/hospitals/{id}/`
- `GET/POST /api/v1/chambers/`
- `GET/PATCH/DELETE /api/v1/chambers/{id}/`

Doctor listings expose only profiles with `APPROVED` verification. Patient
profiles are private and object ownership is enforced server-side. Doctor
assistant relationships are active-only and scoped to the associated doctor;
revoking a relationship removes the assistant's access immediately.

Doctor search supports `search`, `ordering`, and filters such as `specialty`,
`experience_years`, `consultation_fee`, `hospital`, and `location`. Doctor and
hospital/chamber writes cannot select or change ownership or verification
fields outside the authorized workflow.

## React Native connectivity

The backend listens on port `8000` and Docker publishes it to the host. Set
the React Native app's API base URL according to the device target:

```text
# iOS Simulator
http://localhost:8000/api/v1

# Android Emulator
http://10.0.2.2:8000/api/v1

# Physical device on the same Wi-Fi network
http://<your-computer-LAN-IP>:8000/api/v1
```

Use `GET /health/` to verify connectivity. Native React Native requests do
not require browser CORS configuration; Expo/Web requests are covered by the
development CORS settings. For a physical device, include the computer's LAN
IP in `DJANGO_ALLOWED_HOSTS` and ensure port `8000` is allowed through the
local firewall.

Recommended client token behavior:

1. Store the access and refresh tokens in secure device storage.
2. Send `Authorization: Bearer <access-token>` on protected requests.
3. On a `401`, call `/accounts/token/refresh/`, replace both stored tokens,
   and retry the original request once.
4. If refresh fails, clear tokens and navigate to login.
5. On sign-out, call `/accounts/logout/` with the current refresh token, then
   clear local storage regardless of the response.
