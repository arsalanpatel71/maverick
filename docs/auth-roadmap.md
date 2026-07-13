# Auth Roadmap

> Planned features — not yet built. Both require external services before any code can be written.

---

## 1. Password Reset via Email

### What it does
User clicks "Forgot password?" on the login screen → enters their email → receives a reset link → clicks link → sets new password.

### External service needed
An email delivery provider. Options:

| Service | Free tier | Notes |
|---|---|---|
| **Resend** | 3,000 emails/month | Best DX, simple API, recommended |
| **SendGrid** | 100 emails/day | Widely used, more config |
| **AWS SES** | 62,000/month (if sending from EC2) | Cheapest at scale, more setup |

**Recommended: Resend** — one API key, one `POST /emails` call, done.

### How it would work

```
1. User submits email on "forgot password" form
   POST /auth/forgot-password  { email }

2. Backend:
   - Look up user by email
   - Generate a secure random token (32 bytes, hex)
   - Store token in MongoDB with: user_id, token_hash, expires_at (15 min TTL)
   - Send email via Resend with link: https://app.com/reset-password?token=<token>
   - Always return 200 (don't leak whether email exists)

3. User clicks link → frontend shows "new password" form
   POST /auth/reset-password  { token, new_password }

4. Backend:
   - Look up token in DB, verify not expired
   - Hash new password, update user record
   - Delete token from DB (one-time use)
   - Return 200
```

### New MongoDB collection needed
`password_reset_tokens`:
- `_id` — random UUID
- `user_id` — string
- `token_hash` — SHA-256 of the raw token (never store raw)
- `expires_at` — datetime (15 min from creation)
- TTL index on `expires_at` so expired tokens are auto-deleted

### New env vars needed
```
RESEND_API_KEY=re_...
EMAIL_FROM=noreply@yourdomain.com
APP_URL=https://app.yourdomain.com   # for building the reset link
```

### New backend files needed
```
backend/
  auth/
    email.py       — Resend client, send_reset_email()
    reset_store.py — MongoDB CRUD for reset tokens
```

### New routes
```
POST /auth/forgot-password   — generate + email token
POST /auth/reset-password    — verify token + update password
```

### New frontend pages
```
/forgot-password   — email input form
/reset-password    — new password form (reads ?token= from URL)
```

---

## 2. Google SSO

### What it does
User clicks "Continue with Google" → Google OAuth2 consent screen → redirected back to app → logged in (user created automatically on first login).

### External service / approach needed

**Option A — Google OAuth2 directly (recommended for now)**
- Register app in Google Cloud Console → get `CLIENT_ID` + `CLIENT_SECRET`
- Standard OAuth2 PKCE flow
- No extra infrastructure, runs entirely in the existing FastAPI backend
- Free, no limits

**Option B — Keycloak (mentioned in request)**
- Self-hosted identity provider that proxies Google (and other providers)
- More setup: run a Keycloak Docker container, configure realm + client + Google IdP
- Overkill for a small team but gives a unified SSO layer if you later want SAML, LDAP, GitHub login, etc.
- Worth considering if the plan is to support multiple SSO providers long-term

**Recommendation: start with Google OAuth2 directly, migrate to Keycloak if needed later.**

### How Google OAuth2 would work (direct)

```
1. Frontend: user clicks "Continue with Google"
   → redirect to Google: https://accounts.google.com/o/oauth2/auth
     ?client_id=...&redirect_uri=...&scope=openid email profile&response_type=code

2. Google redirects back to backend callback:
   GET /auth/google/callback?code=...

3. Backend:
   - Exchange code for access token (POST to Google token endpoint)
   - Call Google userinfo API → get { email, name, picture, sub (google_id) }
   - Look up user by email OR google_id
     - If found: issue our JWT cookie, return
     - If not found: create new user (no password_hash needed), then issue JWT
   - Redirect to frontend /

4. User is now logged in with our normal JWT cookie — same session system as email/password
```

### How Keycloak would work (if chosen)

```
Keycloak acts as the IdP:
- All OAuth2 flows go to Keycloak (not directly to Google)
- Keycloak is configured to federate Google as a Social Provider
- Backend validates Keycloak-issued JWTs (RS256, JWKS endpoint)
- Users are managed in Keycloak realm, synced to our MongoDB on first login

Additional infra needed:
- Keycloak server (Docker: quay.io/keycloak/keycloak)
- PostgreSQL for Keycloak (separate from our MongoDB)
- Keycloak realm configured with Google IdP client_id/secret
- Our FastAPI backend configured with Keycloak's JWKS URL
```

### New env vars needed (Google OAuth2 direct)
```
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://api.yourdomain.com/auth/google/callback
```

### New backend changes needed
```
backend/
  auth/
    google.py      — exchange code, fetch userinfo, upsert user

users/store.py     — add get_by_google_id(), add google_id field to create()
```

### New routes
```
GET  /auth/google          — redirect to Google consent URL
GET  /auth/google/callback — exchange code, set cookie, redirect to frontend
```

### New frontend changes
- Add "Continue with Google" button on Login page
- Button simply links to `{API_BASE}/auth/google` — no JS OAuth logic needed (server-side flow)
- Google button should use official branding (white button, Google G icon, "Continue with Google" text per Google's guidelines)

### User model change
Add optional `google_id` field to user document:
```python
"google_id": str | None   # Google's "sub" claim, used to link returning SSO users
```
Users created via SSO have no `password_hash`. Password reset should be disabled for SSO-only accounts.

---

## Summary

| Feature | External service | Effort | Blocker |
|---|---|---|---|
| Password reset | Resend (or SendGrid/SES) | ~1 day | Need API key + verified sender domain |
| Google SSO | Google Cloud Console OAuth app | ~1 day | Need GCP project + OAuth2 client credentials |
| Google SSO via Keycloak | Keycloak + GCP | ~2–3 days | Need Keycloak infra + GCP credentials |
