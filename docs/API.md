# API Reference

Base URL: `http://localhost:4343/api` (override with `VITE_API_BASE_URL` on the
frontend). All endpoints are `AllowAny` for the hackathon demo — see
`backend/config/settings.py` `REST_FRAMEWORK` for where to tighten this for a real
deployment.

## Users, consent, ability profile

### `POST /api/auth/login/`
JWT login (`djangorestframework-simplejwt`). Body: `{"username", "password"}`.
Not required for the kiosk demo — the demo personas are selected directly by id.

### `GET /api/users/demo/`
Returns the seeded demo personas: `[{"id", "username", "display_name",
"is_demo_profile"}, ...]`.

### `GET /api/users/{id}/ability-profile/`
Returns the user's `AbilityProfile`, creating a default (all-`typical`) one if none
exists yet.

### `PATCH /api/users/{id}/ability-profile/`
Body: `{"dimensions": {"dexterity": {"level": "reduced-precision"}}, "preferred_modality"?, "preferences"?}`.
Any dimension you send is merged in and tagged `source: "manual"` (manual values
always take priority over inferred ones — Part 20).

### `GET /api/users/{id}/consent/` / `POST /api/users/{id}/consent/`
`GET` returns `{"granted", "scope", "granted_at"}`. `POST` with
`{"granted": true, "scope": ["interaction_adaptation"]}` records consent — this is
what the frontend's "I Agree" button calls.

## Tasks

### `GET /api/tasks/` / `GET /api/tasks/{task_id}/`
Returns the task registry, e.g. `purchase_ticket` with its four `TaskStep`s
(`select_destination`, `select_ticket_type`, `select_quantity`, `confirm_purchase`),
each with its `controls`.

## The core workflow

### `POST /api/interactions/start/`
Body: `{"user_id", "task_id", "environment_id"?, "baseline_mode"?}`.
`environment_id` defaults to `kiosk_standard`. `baseline_mode: true` detects barriers
as normal but skips applying any adaptation later — used for the "without AbilityOS"
comparison in the metrics panel.
Response: `{"session_id", "status"}`.

### `POST /api/environment/analyze/`
Body: `{"session_id", "image_base64"?}`. Without `image_base64` (or with
`VISION_ENABLED=false`), attaches the session's fixture environment. With an image
and vision enabled, runs `ai_engine.services.vision_service` instead. Returns the
`Environment` record.

### `POST /api/barriers/detect/`
Body: `{"session_id"}`. Runs the deterministic detector
(`barriers/services/detection.py`) against the session's profile/task/environment.
Returns `{"barriers": [{"id", "barrier_type", "ability_dimension", "severity",
"confidence", "evidence"}, ...]}`.

### `GET /api/adaptations/candidates/?barrier_type=small_tap_targets`
Returns the raw catalogue entries that *could* resolve a barrier type, without
running scoring/AI — useful for inspecting the catalogue independently of a session.

### `POST /api/adaptations/recommend/`
Body: `{"session_id"}`. For each detected barrier: ranks candidates, asks the AI
Decision Engine (or falls back), validates through the safety rule engine. Returns:

```json
{
  "ai_used": false,
  "results": [
    {
      "id": 7, "barrier_type": "small_tap_targets",
      "adaptation": { "name": "increase_target_size", "ui_effects": {...}, ... },
      "score": 2.75, "score_breakdown": {...},
      "rationale": "Deterministic fallback: ...",
      "source": "fallback", "approved": true,
      "requires_confirmation": false, "applied": false,
      "candidates_considered": [ ... ]
    }
  ]
}
```

### `POST /api/interactions/{id}/apply/`
Body: `{"confirmed_ids"?: [7, 8]}`. Applies every approved `AdaptationResult` that
either doesn't require confirmation or whose id is in `confirmed_ids`. In
`baseline_mode`, applies nothing regardless. Returns:

```json
{ "applied_adaptations": ["increase_target_size", "increase_contrast"],
  "ui_effects": { "button_scale": 1.8, "contrast": "high", ... },
  "baseline_mode": false }
```

### `POST /api/interactions/{id}/feedback/`
Body: `{"completed", "errors", "time_seconds", "assistance_requested", "effort"?, "confidence"?}`.
Records `Feedback`, sets the session's final status, and nudges the relevant Ability
Profile dimensions' confidence up (clean completion) or down (poor outcome) — the
learning loop from Part 3/5.

### `GET /api/interactions/{id}/summary/`
Full snapshot for the developer panel: profile, task, environment, barriers,
adaptation results (with candidates considered), feedback.

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
Total interactions, completed tasks, overall metrics, adaptation usage counts, and
session counts per Ability Profile.
