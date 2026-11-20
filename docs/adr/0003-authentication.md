# ADR 0003 — Authentication and authorization

**Status:** Accepted · **Date:** 2026-10-06

## Context
Two clients (SPA dashboard, native mobile app) on different origins call one API.
Roles are `owner` and `customer`. Granular RBAC is planned after the MVP. Password reset
must work on mobile without deep-link setup.

## Decision

### Tokens
- **Access token:** JWT (HS256), 15 minutes, sent as `Authorization: Bearer <token>`.
  Claims: `sub` (user id), `role`, `exp`, `iat`, `type: "access"`.
- **Refresh token:** opaque random string (32 bytes, URL-safe), 30 days, stored only as
  a SHA-256 hash in `refresh_tokens`.
- **Rotation:** every `/auth/refresh` revokes the used refresh token and issues a new pair.
  A revoked or expired refresh token returns `401 REFRESH_TOKEN_INVALID`.
- **Logout** revokes the given refresh token. **Password reset** revokes all of the user's
  refresh tokens.

### Token storage on clients
- Mobile: both tokens in `expo-secure-store`.
- Dashboard: access token in memory, refresh token in `localStorage`.
  **Known risk:** an XSS bug could steal the refresh token. Mitigations: short access TTL,
  rotation, no `{@html}` with user content, strict CSP when deployed. Revisit with
  httpOnly cookies when the API and dashboard share a parent domain.

### Passwords
- `pwdlib` with Argon2. Minimum 8 characters, maximum 128.
- If the deploy target cannot run Argon2 (see ADR 0006 spike), add a second hasher in
  `pwdlib` and rehash on next login. Do not change the algorithm silently.

### Password reset
- `POST /auth/password/forgot` always returns `202`, whether the email exists or not
  (no account enumeration).
- A 6-digit numeric code is emailed, valid 15 minutes, max 5 attempts.
- In development, emails are printed to the API log instead of being sent.
  The production email provider is an open decision (new ADR before deploy).

### Authorization
- One FastAPI dependency, `require_role(*roles)`, guards every protected route.
  Route handlers never compare `user.role` themselves.
- Owner routes live under `/owner/*`. Customer routes (`/cart/*`) require `customer`.
- Login is shared (`POST /auth/login`). The dashboard refuses non-owner users on the client,
  but security relies on `/owner/*` returning `403` for customers.

## Alternatives considered
- **Session cookies.** Better XSS resistance, but cross-origin cookies complicate local
  development and the mobile client. Deferred.
- **Reset link with deep link.** Requires app link configuration and a web fallback page.
  A code is simpler and works in Expo Go.
- **Third-party auth (Clerk, Supabase Auth, Neon Auth).** Rejected: building auth is part of
  what this portfolio demonstrates.

## Consequences
- Moving to RBAC later means changing `require_role` into `require_permission` in one place.
- No rate limiting in the MVP. Brute force on login and reset is mitigated only by the
  5-attempt limit on reset codes. Listed in the roadmap.
