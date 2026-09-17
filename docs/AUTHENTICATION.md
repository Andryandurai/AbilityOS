# Authentication (Phase 1 — Real User Authentication)

> **Scope note:** this document covers only Phase 1: register, login, `/me`,
> logout, and the ownership fixes it required. Onboarding, the
> questionnaire, profile suggestions, and the dashboard are explicitly
> **not** part of this phase — see `docs/PHASES.md`-equivalent Phase 0
> audit for the full roadmap.

## Endpoints

| Endpoint | Method | Auth required | Purpose |
|---|---|---|---|
| `/api/auth/register/` | POST | No | Create a real, non-demo account |
| `/api/auth/login/` | POST | No | Obtain an access/refresh token pair (pre-existing, unmodified) |
| `/api/auth/me/` | GET | Yes | Return the authenticated user's own record |
| `/api/auth/logout/` | POST | Yes | Blacklist the supplied refresh token |

### Register

`POST /api/auth/register/` — `{"username", "email"?, "display_name"?, "password", "password_confirm"}`.

- Reuses `users.User` (`AbstractUser`) directly — no second user/profile model.
- Passwords are hashed via Django's `User.set_password()` (PBKDF2); the
  plaintext password is never written to the database or logged.
- Password strength is validated by the project's existing
  `AUTH_PASSWORD_VALIDATORS` (`config/settings.py`) — the same rules any
  other Django-managed password already has to satisfy.
- `username` uniqueness is enforced (an existing username is rejected).
- `email` uniqueness is enforced at the application layer
  (`RegisterSerializer.validate_email`), **not** a database `unique=True`
  constraint — the `User.email` field itself is unchanged, since the 9
  seeded demo personas carry no email at all and adding a DB constraint
  would have been an unnecessary migration for what registration alone
  needs.
- New accounts are always created with `is_demo_profile=False`, explicitly,
  regardless of what the request body contains.
- Registration does **not** eagerly create an `AbilityProfile`, grant
  consent, or assign a demo persona. `AbilityProfileView` already lazily
  creates a default profile on first access (`get_or_create_profile`) —
  registration doesn't need to duplicate that.

### Login

`POST /api/auth/login/` — unchanged from before this phase
(`users.views.LoginView`, SimpleJWT's `TokenObtainPairView` with
`AbilityOSTokenObtainPairSerializer`). Returns `{"access", "refresh",
"user": {"id", "username", "display_name", "is_demo_profile"}}`.

### Me

`GET /api/auth/me/` derives identity **only** from `request.user` — never
from a URL parameter, body field, or query string — so it can never be used
to read another account by guessing an id (verified by
`MeTests.test_me_ignores_a_spoofed_user_id_and_uses_request_user`). Returns
`id`, `username`, `email`, `display_name`, `is_demo_profile`. Never returns
a password, password hash, or any token.

### Logout

`POST /api/auth/logout/` — `{"refresh": "<refresh token>"}`, requires a
valid access token.

**What logout actually does, precisely:** SimpleJWT's `token_blacklist` app
is enabled (bundled with the already-installed `djangorestframework-
simplejwt` package — no new dependency was added) and the supplied refresh
token is blacklisted. **This does not, and cannot, invalidate the access
token that was used to call this endpoint** — SimpleJWT access tokens are
stateless JWTs verified by signature alone; there is no server-side
revocation list for them. The access token used in the same request (and
any other access token issued to this user) remains individually valid
until it naturally expires (`ACCESS_TOKEN_LIFETIME`, below). "Logged out" in
this implementation means: (1) the refresh token can never again be
exchanged for a new access token, and (2) the frontend immediately discards
both tokens from its own storage. It is not a claim that every previously
issued access token is instantly rejected everywhere.

## SIMPLE_JWT configuration

Previously absent — the library's own defaults were silently in effect.
Now explicit in `config/settings.py`:

| Setting | Value | Why |
|---|---|---|
| `ACCESS_TOKEN_LIFETIME` | 1 day | Long enough that a full demo/judging session, or a normal onboarding flow in a later phase, never silently expires mid-flow. Phase 1 deliberately does not implement a silent-refresh-on-401 interceptor (see Limitations below), so a short access token would just mean unexpected logouts. |
| `REFRESH_TOKEN_LIFETIME` | 7 days | "Stay logged in" across normal day-to-day use without re-entering credentials constantly. |
| `ROTATE_REFRESH_TOKENS` | `True` | A refresh token is single-use; a new one is issued on each use. |
| `BLACKLIST_AFTER_ROTATION` | `True` | The old refresh token is blacklisted the moment it's rotated — only meaningful because `token_blacklist` is installed. |
| `UPDATE_LAST_LOGIN` | `True` | Populates Django's existing, previously-unused `last_login` field. |
| `AUTH_HEADER_TYPES` | `("Bearer",)` | The conventional value; matches what `frontend/src/services/api.js` sends. |

## Authentication-required vs. anonymous-compatible endpoints

Only two endpoints require authentication: `GET /api/auth/me/` and
`POST /api/auth/logout/`. **`AllowAny` was never changed to
`IsAuthenticated` anywhere else.** Every endpoint that powered the
anonymous hackathon demo before this phase — the 9 demo personas, the full
barrier detection → adaptation → safety validation → kiosk → feedback →
analytics pipeline — remains fully reachable without logging in, verified
by a live, full end-to-end anonymous session (Hearing Difficulty persona,
purchase completed) during this phase's own testing.

## Ownership fixes (Phase 0 audit → Phase 1 fix)

The Phase 0 audit found two real gaps: `AbilityProfileView.get()` and
`ConsentView.get()` had no ownership check at all (only their `PATCH`/`POST`
counterparts did). Both now call the existing `assert_owner()` helper
(`users/services/ownership.py`) on `GET` too.

`assert_owner()` is a no-op unless `request.user.is_authenticated` — so this
change is invisible to the anonymous demo path (which never authenticates)
and only starts mattering now that real authentication exists: an
authenticated user's token can read their own profile/consent, but gets a
403 attempting to read another user's.

The interaction-session endpoints (`/api/interactions/{id}/...`,
`StartInteractionView`, `DetectBarriersView`, `RecommendAdaptationsView`,
etc.) were also audited: every one of them **already** called
`assert_owner(request, session.user_id, ...)` (added in the original
project's earlier hardening work, predating this phase) — no change was
needed there.

## Frontend

- **Token storage:** `localStorage`, via two dedicated hooks/functions in
  `frontend/src/hooks/useAuth.js` — chosen because this is a hackathon SPA
  with no existing cookie/session infrastructure to build on. **Documented
  tradeoff:** a token in `localStorage` is readable by any script that
  achieves XSS on this origin. Mitigations actually in place: tokens are
  never logged (console or otherwise) anywhere in the codebase, never put
  in a URL or query string, and are cleared immediately on logout.
- **Attaching the token:** centralized in `frontend/src/services/api.js` via
  a single `setAccessToken()` function and a module-level variable read by
  every request — no component attaches an `Authorization` header itself.
- **Two independent entry paths coexist** (App.jsx): the existing anonymous
  demo (9 seeded personas, unchanged) and a real account. Because
  `api.js`'s token attachment is global, entering the anonymous demo calls
  `useAuth().pauseAuthHeader()` first (clears the outgoing header only —
  never touches `localStorage`, the stored session, or calls the backend),
  and leaving it calls `resumeAuthHeader()`. This is what lets a person who
  is also logged in still browse the 9 demo personas exactly as before,
  without `assert_owner()` rejecting requests for a different user's demo
  data — verified live.
- **No React Router was introduced** — login/register are two more values
  of the existing `App.jsx` state machine (`authView`), exactly as Phase 0
  recommended deferring the routing migration to a later phase.

## Known limitations (intentionally deferred)

- **No silent refresh-on-401.** If the 1-day access token expires while a
  tab is open, the next authenticated request fails and the person must
  log in again; there is no interceptor that automatically exchanges the
  refresh token for a new access token mid-session.
- **Logout does not revoke the access token itself** — see "What logout
  actually does" above. This is a property of stateless JWTs, not an
  oversight, and is documented rather than glossed over.
- **`RegisterView`/`LoginView` do not yet drive onboarding, a
  questionnaire, profile suggestions, or a dashboard** — a logged-in user
  in this phase sees a minimal "Welcome, `<name>`" + "Log out" on the
  landing page and nothing more. That is deliberate Phase 1 scope, not a
  missing feature.
- **A real account is not yet connected to the AbilityOS reasoning
  pipeline.** Logging in does not let a person drive the kiosk as
  themselves — that connection is explicitly Phase 5 territory per the
  Phase 0 plan.
