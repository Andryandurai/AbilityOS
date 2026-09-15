# API Reference

Base URL: `http://localhost:4343/api` (override with `VITE_API_BASE_URL` on the
frontend). Every endpoint is reachable anonymously — this is a deliberate,
documented choice for the login-free hackathon demo (see
`backend/config/settings.py`'s `REST_FRAMEWORK` comment) — but **every** endpoint
that reads or writes a specific user's data (ability profile, consent, and — as
of Phase 8 — every session/feedback/event endpoint below) enforces real ownership
for any request that *does* carry an authenticated identity: an authenticated
user may only touch their own data (403 otherwise); staff may touch any. See
`backend/users/services/ownership.py` (the single shared implementation — it was
previously duplicated per-app and didn't cover the session endpoints at all).

Three endpoints are rate-limited (IP-based, `ScopedRateThrottle`):
`POST /api/auth/login/` (10/min), `POST /api/interactions/start/` (30/min),
`POST /api/adaptations/recommend/` (30/min, the AI-adjacent one). Every other
endpoint is unthrottled.

Any unhandled server error returns `{"detail": "..."}` with status 500; the
message is only the raw exception text when `DEBUG=true` — in a real deployment
(`DEBUG=false`) it's a generic "Unexpected server error. Please try again." and
the real detail goes to the server log (`api` logger) instead, never the HTTP
response.

## Foundation

### `GET /api/health/`
Runs a real query against the configured database and reports the result —
not just "the process is alive". Response:
```json
{ "status": "ok", "service": "AbilityOS API", "django_version": "5.2.17",
  "database": { "engine": "sqlite", "connected": true, "error": null, "seeded_user_count": 4 },
  "ai_decision_engine": { "provider": "none", "configured": false } }
```
`status`/HTTP code is `degraded`/503 if the database query fails.

## Users, consent, ability profile

### `POST /api/auth/login/`
JWT login (`djangorestframework-simplejwt`). Body: `{"username", "password"}`.
Not required for the kiosk demo — the demo personas are selected directly by id.
Demo persona password: `demo-password`.

### `GET /api/users/demo/`
Returns the seeded demo personas: `[{"id", "username", "display_name",
"is_demo_profile"}, ...]`.

### `GET /api/users/{id}/ability-profile/`
Returns the user's `AbilityProfile`, creating a default one if none exists yet
(each dimension starts at *its own* no-barrier baseline — see
[ABILITY_PROFILE.md](ABILITY_PROFILE.md), not a single hardcoded `"typical"`).

### `PATCH /api/users/{id}/ability-profile/`
Body: `{"dimensions": {"dexterity": {"level": "reduced-precision"}}, "preferred_modality"?, "preferences"?}`.
Every dimension you send is validated against the controlled vocabulary
(`backend/abilities/constants.py`) and always tagged `source: "manual"` — a
person editing their own profile is by definition the most trustworthy source
(manual always outranks inferred/default — see ABILITY_PROFILE.md). Rejects with
`400` and a specific message for: an unknown dimension key, a level outside that
dimension's allowed values, a confidence outside `[0.0, 1.0]`, an unknown source,
or an invalid `preferred_modality`. Requires ownership if authenticated (`403`
otherwise).

### `DELETE /api/users/{id}/ability-profile/`
"Clear Profile" — resets every dimension to its default and clears
`preferences`. The user account is never deleted. Requires ownership if
authenticated.

### `GET /api/users/{id}/consent/` / `POST /api/users/{id}/consent/`
`GET` returns `{"granted", "scope", "granted_at"}`. `POST` with
`{"granted": true, "scope": ["interaction_adaptation"]}` records consent — this is
what the Consent screen's "Continue" button calls. `POST` with
`{"granted": false}` revokes it. Requires ownership if authenticated. Consent
gates *use* of a profile for adaptation, not viewing/editing it —
`POST /api/interactions/start/` returns `409` if consent hasn't been granted.

## Tasks

### `GET /api/tasks/` / `GET /api/tasks/{task_id}/`
Returns the task registry, e.g. `purchase_ticket` with its four `TaskStep`s
(`select_destination`, `select_ticket_type`, `select_quantity`, `confirm_purchase`),
each with its `controls`.

### `POST /api/tasks/analyze/` (Phase 3 — Task Understanding Engine)
Body: `{"task_id": "purchase_ticket"}`. Deterministic lookup only — no AI, no
barrier judgement. Returns the full `TaskDescriptor`:
```json
{ "task_id": "purchase_ticket", "name": "Buy a ticket", "description": "...",
  "steps": [ { "id": "select_destination", "order": 1, "name": "Select destination",
                "description": "...", "required": true, "controls": [...] }, ... ],
  "controls": [ { "id": "dest_airport", "type": "button", "label": "Airport",
                   "interaction_type": "touch" }, ... ],
  "time_limit_seconds": null }
```
`400` if `task_id` is missing, `404` for an unknown `task_id` — never silently
invents a task. See [PHASE_3.md](PHASE_3.md) for why this deliberately stops
short of any accessibility judgement.

## The core workflow

### `POST /api/interactions/start/`
Body: `{"user_id", "task_id", "environment_id"?, "baseline_mode"?}`.
`environment_id` defaults to `kiosk_standard`. `baseline_mode: true` detects barriers
as normal but skips applying any adaptation later — used for the "without AbilityOS"
comparison in the metrics panel. Returns `409` if the user hasn't granted
`interaction_adaptation` consent yet (Phase 2 consent gate).
Response: `{"session_id", "status"}`.

### `POST /api/environment/analyze/`
Two calling conventions on one endpoint:
- **Session-bound** (the orchestrator's own internal flow): `{"session_id", "image_base64"?}`.
  Without `image_base64` (or with `VISION_ENABLED=false`), attaches the session's
  fixture environment. With an image and vision enabled, runs
  `ai_engine.services.vision_service` instead. Returns the `Environment` record.
- **Standalone fixture lookup** (Phase 3 — Environment Understanding Engine):
  `{"environment_id": "ticket_kiosk_default"}`, no session required. Deterministic
  only — routes through `environments.services.analyzer.EnvironmentAnalyzer.analyze_fixture()`.
  Returns the full `EnvironmentDescriptor`:
  ```json
  { "environment_id": "ticket_kiosk_default", "environment_type": "kiosk",
    "screen": { "width": 1280, "height": 800, "dpi": 96 },
    "controls": [ { "id": "confirm_button", "x": 100, "y": 500, "width": 120,
                     "height": 45, "label": "Confirm", "type": "button" }, ... ],
    "contrast": { "level": "low", "background": "#ffffff", "foreground": "#777777" },
    "noise_level": "moderate", "lighting": "normal" }
  ```
  `400` if neither `session_id` nor `environment_id` is given, `404` for an unknown
  `environment_id`. `analyze_screenshot`/`analyze_camera` on `EnvironmentAnalyzer`
  raise `NotImplementedError` — not implemented in Phase 3, not faked either.

### `POST /api/barriers/detect/`
Two calling conventions on one endpoint:
- **Session-bound** (the orchestrator's own internal flow): `{"session_id"}`.
  Runs the pre-existing deterministic detector (`barriers/services/detection.py`)
  against the session's profile/task/environment, persisting `Barrier` rows.
  Returns `{"barriers": [{"id", "barrier_type", "ability_dimension", "severity",
  "confidence", "evidence"}, ...]}`.
- **Standalone** (Phase 4 — Barrier Detection Engine): `{"user_id", "task_id",
  "environment_id"}`, no session required. Routes through
  `tasks.services.task_service` + `environments.services.analyzer` (Phase 3) to
  fetch the descriptors, then `barriers.services.detector.BarrierDetectionService`
  (Phase 4) to compare them against the profile. Nothing is persisted — a
  stateless "what would be detected" query. Returns:
  ```json
  { "user_id": 1, "task_id": "purchase_ticket", "environment_id": "ticket_kiosk_default",
    "barriers": [
      { "barrier_type": "small_tap_targets", "ability_dimension": "dexterity",
        "severity": 0.7, "confidence": 0.8, "title": "Small touch targets",
        "description": "Several interactive controls are below the configured minimum touch target size (160x48px) for a 'reduced-precision' dexterity profile.",
        "evidence": { "controls": [{"id": "buy_ticket", "width": 120, "height": 45}, ...],
                       "threshold": {"min_width": 160, "min_height": 48},
                       "ability_value": "reduced-precision" } }
    ] }
  ```
  `400` if `user_id`/`task_id`/`environment_id` aren't all provided (and no
  `session_id` either), `403` if the user hasn't granted consent, `404` for an
  unknown `task_id`/`environment_id`. An empty `barriers: []` is a valid,
  expected result — "no mismatch detected" is not an error. See
  [PHASE_4.md](PHASE_4.md) for the rule-by-rule breakdown.

### `GET /api/adaptations/candidates/?barrier_type=small_tap_targets`
Returns the raw catalogue entries that *could* resolve a barrier type, without
running scoring/AI — useful for inspecting the catalogue independently of a session.

### `POST /api/adaptations/recommend/`
Two calling conventions on one endpoint:
- **Session-bound** (the orchestrator's own internal flow): `{"session_id"}`. For
  each detected barrier: ranks candidates, asks the AI Decision Engine (or falls
  back), validates through the safety rule engine, persists `AdaptationResult` rows.
  Returns:
  ```json
  { "ai_used": false,
    "results": [
      { "id": 7, "barrier_type": "small_tap_targets",
        "adaptation": { "name": "increase_target_size", "ui_effects": {...}, ... },
        "score": 2.75, "score_breakdown": {...},
        "rationale": "Deterministic fallback: ...",
        "source": "fallback", "approved": true,
        "requires_confirmation": false, "applied": false,
        "candidates_considered": [ ... ] }
    ] }
  ```
- **Standalone** (Phase 5 — Adaptation Engine + AI Decision Engine):
  `{"user_id", "task_id", "environment_id"}`, no session required. Runs Phase 4
  barrier detection, then `adaptations.services.recommender.AdaptationRecommender`
  on top of it — scores the full candidate pool across every detected barrier,
  optionally asks the AI Decision Engine to rank it (falling back deterministically
  on any failure/invalid response), and independently safety-validates the result.
  Nothing is persisted, and nothing about the kiosk changes — this only *returns*
  the decision. Returns:
  ```json
  { "barriers": [ { "barrier_type": "small_tap_targets", "severity": 0.7, ... } ],
    "candidates": [
      { "adaptation_id": "increase_target_size", "score": 2.765 },
      { "adaptation_id": "increase_spacing", "score": 2.425 }
    ],
    "selected_adaptation": {
      "adaptation_id": "increase_target_size", "name": "Increase target size",
      "score": 2.765, "barrier_types": ["small_tap_targets"],
      "reason": "Deterministic fallback: 'Increase target size' scored highest (2.77) using ...",
      "source": "deterministic_fallback", "validated": true,
      "requires_confirmation": false, "ai_error": null } }
  ```
  `400` if not all of `user_id`/`task_id`/`environment_id` are given (and no
  `session_id` either), `403` if consent hasn't been granted, `404` for an unknown
  `task_id`/`environment_id`. If no barriers were detected: `{"barriers": [],
  "candidates": [], "selected_adaptation": null, "reason": "No accessibility
  mismatch detected."}` — no AI call is made. If barriers exist but no adaptation
  is safe: `"selected_adaptation": null, "reason": "no_safe_adaptation"`. See
  [PHASE_5.md](PHASE_5.md) for the full scoring/validation breakdown.

### `POST /api/interactions/{id}/apply/`
Body: `{"confirmed_ids"?: [7, 8]}`. Applies every approved `AdaptationResult` that
either doesn't require confirmation or whose id is in `confirmed_ids`. In
`baseline_mode`, applies nothing regardless. Returns:

```json
{ "applied_adaptations": ["increase_target_size", "increase_contrast"],
  "ui_effects": { "button_scale": 1.8, "contrast": "high", ... },
  "baseline_mode": false }
```

### `POST /api/interactions/{id}/events/` (Phase 7)
Body: one event object, or `{"events": [...]}` for a batch — the frontend queues
events locally and flushes them in one call rather than one request per tap. Each
event: `{"event_type", "step"?, "control_id"?, "metadata"?}`.
`event_type` must be one of `feedback.InteractionEvent.EVENT_TYPE_CHOICES`
(`control_selected`, `control_reselected`, `validation_error`, `back_navigation`,
`confirmation_opened`, `confirmation_completed`, `assistance_requested`,
`task_completed`, `task_abandoned`, `step_started`) — anything else is a 400.
Recording any event on a non-terminal session also advances its status to
`in_progress`; an `assistance_requested` event increments `assistance_count`.
Rejects (400) if the session is already `completed`/`abandoned`/`failed`. Response:
```json
{ "recorded": 2, "events": [...], "status": "in_progress", "assistance_count": 0 }
```

### `POST /api/interactions/{id}/complete/` (Phase 7)
No body required. Transitions the session to `completed`, sets a server-authoritative
`completed_at`, and records a `task_completed` event. 409 if the session is already
in a terminal status (no duplicate completion — section 28). Response:
`{"status": "completed", "completed_at": "...", "completion_time_ms": 58000}`.

### `POST /api/interactions/{id}/abandon/` (Phase 7)
Body: `{"reason"?: "..."}`. Same terminal-status guard as `/complete/`. Response:
`{"status": "abandoned", "completed_at": "..."}`.

### `POST /api/interactions/{id}/feedback/`
Body: `{"completed", "errors", "time_seconds", "assistance_requested", "effort"?,
"confidence"?, "ease_rating"?, "adaptation_helpfulness"?, "optional_comment"?}`.
`ease_rating` (1-5) and `adaptation_helpfulness` (`helped`/`somewhat_helped`/
`did_not_help`) are validated against a controlled vocabulary (400 on an invalid
value); `optional_comment` is truncated to 500 characters. Records `Feedback` and —
only if the session hasn't already been moved to a terminal status via `/complete/`
or `/abandon/` — also sets it, for backward compatibility with the original
single-call flow. **Does not** modify the Ability Profile; see
[PHASE_7.md](PHASE_7.md) for why the earlier automatic confidence-nudge was retired.

### `GET /api/interactions/{id}/summary/`
Full snapshot for the developer panel: profile, task, environment, barriers,
adaptation results (with candidates considered), feedback, plus (Phase 7)
`experience_mode`, `assistance_count`, `completion_time_ms`, `interaction_counts`
(errors/retries/backtracks/assistance derived from `InteractionEvent`),
`outcome_score`, and `learning_signal`.

## Analytics

### `GET /api/analytics/before-after/`
```json
{ "note": "Prototype demonstration metrics — ...",
  "without_abilityos": { "sessions": 3, "completion_rate": 0.67, "avg_time_seconds": 83.3, "avg_errors": 4.0, "assistance_rate": 0.67 },
  "with_abilityos":    { "sessions": 4, "completion_rate": 1.0,  "avg_time_seconds": 33.0, "avg_errors": 0.25, "assistance_rate": 0.0 } }
```
Computed from real `InteractionSession`/`Feedback` rows filtered by `baseline_mode`
— never hand-typed numbers.

### `GET /api/analytics/dashboard/`
Total interactions, completed tasks, abandoned tasks, overall metrics, adaptation
usage counts, and session counts per Ability Profile. Returns `{"note", "empty":
true}` with no other fields when there are no sessions yet (Phase 7 section 39 —
"no data" is never rendered as a fabricated zero).

### `GET /api/analytics/adaptations/` (Phase 7)
Per-adaptation outcome evidence, applied sessions only:
```json
{ "note": "...", "empty": false, "adaptations": [
  { "adaptation_id": "increase_target_size", "display_name": "Increase target size",
    "sessions": 8, "completion_rate": 0.875, "avg_ease": 4.4, "assistance_rate": 0.125,
    "avg_errors": 0.5, "observed_outcome": "positive_observed_outcome", "confidence": 0.94 } ] }
```
`observed_outcome` is one of `positive_observed_outcome` / `negative_observed_outcome`
/ `inconclusive` / `insufficient_data`, computed deterministically from documented,
centralized thresholds in `backend/analytics/config.py` — never an AI judgment.

### `GET /api/analytics/barriers/` (Phase 7)
Per-barrier-type frequency, associated adaptations, and outcome success — same
`observed_outcome` vocabulary as above.

### `GET /api/analytics/sessions/?limit=10` (Phase 7)
The most recent sessions (task, experience mode, status, ease rating, assistance) for
the "Recent Sessions" table. Each row carries `is_seed` so demo-seeded rows are never
indistinguishable from a live session (section 38).
