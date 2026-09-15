# Phase 8 — Final Integration, Hardening, Deployment Readiness & Polish

## Objective

Phase 8 adds no new product feature. It makes Phases 1–7 work as one coherent,
reliable, demonstrable, deployment-ready product — the audit-then-fix pass every
prior phase deferred to "later." This document records what the audit found and
exactly what changed because of it.

## Architecture audit

Inspected: Django settings (secrets/CORS/DEBUG/auth), every API view, the
ownership/authorization pattern, logging configuration, the custom DRF exception
handler, frontend structure (components/pages/hooks), dependencies (both sides),
`.env.example` files and `.gitignore`, heading hierarchy across pages, and every
`.distinct()`/aggregate query in the analytics layer.

**Findings and what came of each:**

| Finding | Action |
|---|---|
| `_assert_ownership` duplicated verbatim in `abilities/views.py` and `users/views.py`; the Phase 7 session/feedback endpoints had no ownership check at all | Centralized into `users/services/ownership.py`; applied to all 9 session-touching views plus the two `user_id`-in-body standalone endpoints |
| `LOGGING["loggers"]` configured `"barriers"` (nothing there logs) but omitted `"api"` (which does — its `.info()`/`.exception()` calls were silently dropped at the root's WARNING threshold) | Fixed the logger list |
| The custom exception handler echoed raw `str(exc)` to the client on any 500, regardless of `DEBUG`, and never logged server-side | Now logs via `logger.exception()` always; only includes the raw message when `DEBUG=True`, else a generic message |
| No frontend error boundary — a crash showed a blank page | Added `ErrorBoundary.jsx`, wraps `<App/>` in `main.jsx` |
| `DemoPage.jsx`/`AnalyticsPage.jsx` had no `<h1>` (every other page does) | Promoted their top headings; renumbered `AnalyticsPage`'s sections `h3→h2` to stay correctly nested under the new `h1` |
| `docs/DEMO_GUIDE.md` predated Phase 6's "Open Adaptive Kiosk" hand-off, the View Original/Adaptive toggle, and all of Phase 7 | Rewritten to match the actual current flow |
| `docs/PHASES.md` didn't exist | Created |
| `frontend/.env.example` and `api.js`'s fallback both referenced port 8000, inconsistent with the project's actual documented port (4343) | Fixed both |
| No rate limiting on auth/session-creation/AI-adjacent endpoints | Added a lightweight, scoped `ScopedRateThrottle` (10-30/min) on exactly three endpoints |
| **A real, previously-undetected data bug**: `analytics/services.py`'s `adaptation_effectiveness()` returned a duplicate row per distinct `score` value for the same adaptation, because `.distinct()` on a `.values_list()` inherits the model's default `Meta.ordering` unless explicitly cleared — `AdaptationResult` orders by `-score` by default, so the same adaptation applied across sessions with different scores produced multiple rows | Fixed with `.order_by()` before `.distinct()` in all four affected queries (`analytics/services.py`); applied the same defensive fix to the structurally-identical `barrier_types`/`session_ids` queries in `barrier_outcomes()` even though today's seeded data didn't happen to trigger a visible duplicate there |

**Reviewed, no action taken:** no XSS risk (no `dangerouslySetInnerHTML` anywhere),
no raw SQL beyond a parameterless health-check `SELECT 1`, no secrets in git
(`.env.example` files are placeholder-only; real `.env`/`.env.local` correctly
gitignored), dependencies on both sides are minimal with no unused/duplicate
packages, `DEBUG`/`SECRET_KEY`/`ALLOWED_HOSTS`/`CORS_ALLOWED_ORIGINS`/
`DATABASE_URL` were already all env-configurable, CSRF is fine (the demo path
doesn't use session auth), the `.values().annotate()` aggregate queries in
`analytics/views.py::dashboard()` and `barrier_outcomes()`'s `associated` query
turned out **not** to share the `.distinct()` bug (verified empirically, not
assumed — Django resets grouping correctly for `.values().annotate()`, just not
for a bare `.distinct()` on `.values_list()`), and the analytics N+1 pattern (one
query per adaptation in a loop) is bounded by the fixed 12-entry catalogue and not
worth the added complexity to rewrite into a single query.

## How the ordering/distinct bug was found

Not by code review — by live Playwright verification against the real dev
database. The React console showed `"Encountered two children with the same key
... increase_target_size"` on the Analytics page. Tracing it back led to the
`.distinct()` behavior described above. The bug was then reproduced and confirmed
directly in a Django shell (`[1, 3, 1, 3, 1, 6, 9]` vs. the correct `[1, 3, 6,
9]`) before being fixed, and a regression test was added that specifically varies
`score`/`severity` per session (the previous tests all used a fixed score, which
is exactly why they didn't catch this). This is the kind of integration bug that
only surfaces with real data flowing through real code — unit tests with
uniform fixture data cannot catch it, which is itself a useful lesson recorded
here rather than only fixed silently.

## Security

- Ownership checks now cover every endpoint that reads or writes a specific
  user's data: ability profile, consent (pre-existing), and — new this phase —
  every session/feedback/event endpoint (`start`, `apply`, `events`, `complete`,
  `abandon`, `feedback`, `summary`, plus the standalone barrier/recommend
  endpoints). Anonymous requests (the demo path) are completely unaffected;
  only a request carrying a real authenticated identity is held to the rule.
- Three endpoints are rate-limited (IP-based `ScopedRateThrottle`): login
  (10/min), session start (30/min), adaptation recommendation (30/min, the
  AI-adjacent one).
- Unhandled server errors are now always logged server-side and never leak raw
  exception text to the client outside `DEBUG` mode.
- No secrets in git; `.env.example` files (both apps) contain placeholders only.

## Accessibility

- Every top-level page now has exactly one `<h1>`, with subsections correctly
  nested beneath it (fixed on `DemoPage`/`AnalyticsPage`; every other page
  already had this).
- The existing kiosk accessibility properties from Phase 6 (semantic buttons,
  `aria-pressed`, `role="status"`/`aria-live` announcements, visible focus via
  the existing global stylesheet, no color-only barrier/outcome indicators —
  every `pill` carries text, every outcome badge carries an icon + word) were
  re-verified, not rebuilt.
- The new frontend additions this phase (`ErrorBoundary`, the Judge Mode glance
  strip) use semantic `role="alert"`/`<dl>` markup consistent with the rest of
  the app.

## Error handling & safe fallback

Every fallback path described in the phase brief was already true by
construction from earlier phases and was re-verified live this phase, not
rebuilt: AI unavailable → deterministic Phase 5 fallback (labeled as such in the
Developer Panel); no approved adaptation → standard kiosk; voice/haptic APIs
wrapped in try/catch (`KioskView.jsx`); analytics unavailable would not block the
kiosk (separate component, separate data fetch); vision unavailable → JSON
fixture path. This phase's addition is the frontend error boundary (a component
crash now shows a recovery message instead of a blank page) and the
backend's hardened exception handler (a 500 is now always logged and never
leaks raw detail outside `DEBUG`).

## Demo mode

`seed_demo` (pre-existing, unmodified) remains the one command needed before a
demonstration — no manual database setup. The three personas
(`demo_low_vision_dexterity`, `demo_hearing_difficulty`, `demo_cognitive_load`)
are functional accessibility profiles, not diagnoses, exactly as Phase 2
specified. Demo/seed data is labeled `is_seed=True` at the model level and
surfaced explicitly in the Analytics "Recent sessions" table (a "demo data" pill)
— never presented indistinguishably from a live session.

## UI/UX polish

- Added a compact **Judge Mode** "at a glance" summary (WHO / WHAT / WHERE / WHY
  / CHANGE / RESULT) to the top of the Developer Panel — condenses the full
  decision chain the sections below already show in detail into one scannable
  row, verified live to render correctly and honestly (it reported "Not started
  yet" rather than fabricating a result when a test run genuinely hadn't
  completed the task).
- Fixed the port inconsistency between `frontend/.env.example`/`api.js`'s
  fallback (previously `:8000`) and the project's actual documented port
  (`:4343`).

## Deployment readiness

Already true from earlier phases, verified again this phase: `DEBUG`,
`SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS` are all
environment-configurable with safe defaults; the frontend's API base URL is
configurable (`VITE_API_BASE_URL`); the production build has no hardcoded
`localhost` dependency. `python manage.py check` and
`python manage.py makemigrations --check --dry-run` both pass clean. No Docker
setup was added — the existing manual setup (SQLite, `pip install`, `npm
install`) is already a fast, zero-infrastructure path appropriate for a project
this size; adding Docker was a deliberate no-op, not an oversight (documented in
README's Limitations).

## Files created
- `backend/users/services/ownership.py`
- `frontend/src/components/ErrorBoundary.jsx`
- `docs/PHASES.md`
- `docs/PHASE_8.md`

## Files modified
- `backend/config/settings.py` (logging fix, throttle config)
- `backend/api/exceptions.py` (logging + DEBUG-gated error detail)
- `backend/api/views.py` (ownership checks, throttle scopes)
- `backend/api/tests.py` (+8 tests)
- `backend/users/views.py` (shared ownership helper)
- `backend/abilities/views.py` (shared ownership helper)
- `backend/analytics/services.py` (the `.distinct()` bug fix)
- `backend/analytics/tests.py` (regression guards for the bug)
- `frontend/src/main.jsx` (error boundary wiring)
- `frontend/src/pages/DemoPage.jsx`, `AnalyticsPage.jsx` (heading hierarchy)
- `frontend/src/components/DeveloperPanel.jsx`, `.css` (Judge Mode glance strip)
- `frontend/src/services/api.js`, `frontend/.env.example` (port consistency)
- `README.md` (Problem/Solution, Tech Stack, Prerequisites, Privacy, Future
  Roadmap sections; updated Limitations)
- `docs/ARCHITECTURE.md` (product-loop diagram ending in Learning Signal)
- `docs/API.md` (ownership/throttling/error-response documentation)
- `docs/DEMO_GUIDE.md` (full rewrite to match the actual current flow)

## Tests executed & results

- `python manage.py test`: **245/245 passing** (237 at the end of Phase 7 + 8 new
  Phase 8 ownership/hardening tests).
- `python manage.py check`: clean.
- `python manage.py makemigrations --check --dry-run`: no changes detected.
- `npm run build`: clean.
- `npx oxlint src`: clean (only the same pre-existing warnings from before this
  phase, in files this phase didn't touch).
- Live Playwright end-to-end run of all three demo personas (Low Vision +
  Reduced Dexterity, Cognitive Load, Hearing Difficulty) through the complete
  flow — select → consent → profile → summary → analyze task/environment →
  detect barriers → recommend adaptation → open adaptive kiosk → apply → task
  interaction → feedback → outcome summary — plus the Analytics dashboard:
  **0 browser console/page errors** (down from 6 duplicate-key errors before the
  `.distinct()` fix).

## Complete demo flow (verified working end-to-end)

Landing → Select demo user → Consent → Ability Profile → Profile Summary →
Analyze Task → Analyze Environment → Detect Barriers → Recommend Adaptation →
Open Adaptive Kiosk → Start Ticket Purchase → Apply Approved Adaptation(s) →
(optional: Ask for help / View Original ↔ View Adaptive / Back / Leave without
finishing) → Complete or Abandon → Feedback → Outcome Summary → Analytics.
Every stage is a real network call to a real endpoint; nothing is a canned
transition.

## Known limitations

See README.md's "Limitations" section — the authoritative, current list. In
short: one seeded task/environment, no production auth flow (JWT exists but
unused by the frontend), no Docker, lightweight (not abuse-hardened) rate
limiting, and hackathon-scope (not empirically tuned) analytics thresholds.

## Future roadmap

See README.md's "Future roadmap" section. Nothing in that list was implemented
this phase — recorded as intentionally deferred, not forgotten.

## Phase 8 completed without replacing the core architecture.

Every fix in this document is additive or corrective — a shared ownership
helper replacing a duplicate, a query fix, missing configuration filled in, new
documentation. No Phase 1–7 model, endpoint, or component was rebuilt or
removed to produce it.
