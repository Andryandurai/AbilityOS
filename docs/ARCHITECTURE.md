# Architecture

## Top-level system

```
React Frontend
      │
      ▼
Django REST Framework
      │
      ▼
AbilityOS Core            (barrier detection, adaptation scoring, safety rules)
      │
      ▼
PostgreSQL                (SQLite fallback for local development)
      │
      ▼
External LLM / Vision services     (optional — AI Decision Engine, computer vision)
```

`AbilityOS Core` is not a separate service or deployable — it's the collective name
for the app-level services under `backend/*/services/` (barrier detection,
adaptation scoring, the AI decision engine, the safety rule engine) that
`InteractionOrchestrator` calls in sequence. See below for exactly how.

## The product loop

The technical "core loop" below implements this conceptual chain — every arrow is
a real, working transition in this codebase, not aspirational:

```
Ability Profile   (abilities.AbilityProfile — functional, never diagnostic)
      │
      ▼
Task              (tasks.Task / TaskStep — what the person is trying to do)
      │
      ▼
Environment        (environments.Environment — fixture or vision-derived facts)
      │
      ▼
Barrier            (barriers.services.detection — deterministic mismatch detection)
      │
      ▼
Adaptation         (adaptations.services.scoring + optional AI — candidate selection)
      │
      ▼
Safety             (adaptations.services.rules — independent re-validation)
      │
      ▼
Kiosk              (frontend/src/components/KioskView.jsx — the approved
      │              adaptation actually renders)
      ▼
Outcome            (feedback.InteractionSession/InteractionEvent — completion,
      │              errors, assistance, all server-authoritative)
      ▼
Learning Signal     (analytics.services.generate_learning_signal — structured,
                      non-mutating evidence; see docs/PHASE_7.md)
```

## The core loop

```
USER (React kiosk)
  │  fetch()
  ▼
DJANGO REST API  (api/urls.py, api/views.py)
  │  delegates each call to...
  ▼
InteractionOrchestrator  (api/services/orchestrator.py)
  │
  ├── AbilityProfileService   →  abilities.models.AbilityProfile
  ├── TaskService             →  tasks.models.Task / TaskStep
  ├── EnvironmentService      →  environments.models.Environment
  │                                (JSON fixture, or ai_engine.services.vision_service)
  ├── BarrierService          →  barriers.services.detection.detect_barriers()
  ├── AI Decision Engine      →  ai_engine.services.decision_engine.decide()
  │       ├── adaptations.services.scoring   (deterministic ranking, always runs)
  │       ├── ai_engine.services.llm_client   (optional, provider-agnostic)
  │       └── ai_engine.services.fallback     (used when AI unavailable/invalid)
  ├── Safety Rule Engine       →  adaptations.services.rules.validate_adaptation()
  └── FeedbackService          →  feedback.models.Feedback
  ▼
PostgreSQL / SQLite
```

Every stage in the table below is one REST call from the frontend and one method on
`InteractionOrchestrator` — there is no hidden logic inside a Django view.

| Stage | Endpoint | Orchestrator method |
|---|---|---|
| Start session | `POST /api/interactions/start/` | `start()` |
| Environment understanding | `POST /api/environment/analyze/` | `analyze_environment()` |
| Barrier detection | `POST /api/barriers/detect/` | `detect_barriers()` |
| Candidate generation + AI reasoning + safety validation | `POST /api/adaptations/recommend/` | `recommend_adaptations()` |
| Apply approved adaptation(s) | `POST /api/interactions/{id}/apply/` | `apply()` |
| Step-level interaction tracking (Phase 7) | `POST /api/interactions/{id}/events/` | `record_event()` / `record_events()` |
| Explicit completion (Phase 7) | `POST /api/interactions/{id}/complete/` | `complete()` |
| Explicit abandonment (Phase 7) | `POST /api/interactions/{id}/abandon/` | `abandon()` |
| Feedback | `POST /api/interactions/{id}/feedback/` | `record_feedback()` |
| Developer panel summary | `GET /api/interactions/{id}/summary/` | `summary()` |

## Django apps ↔ spec's 12 conceptual modules

| Spec module | Django app / file |
|---|---|
| User & Consent Management | `users/` (`User`, `ConsentRecord`, `users/services/consent_service.py`) |
| Ability Profile Manager | `abilities/` (`AbilityProfile`, `abilities/constants.py`, `abilities/services/profile_service.py`) |
| Task Understanding Engine | `tasks/` (`Task`, `TaskStep`) |
| Environment Understanding Engine | `environments/` (`Environment`) + `ai_engine/services/vision_service.py` |
| Barrier Detection Engine | `barriers/services/detection.py` |
| AI Decision Engine | `ai_engine/services/decision_engine.py`, `llm_client.py`, `schemas.py`, `prompts.py` |
| Adaptation Engine | `adaptations/services/scoring.py` + `Adaptation` catalogue |
| Adaptive UI Renderer | `frontend/src/components/KioskView.jsx` |
| Voice Interface | `KioskView.jsx` (`speak()` via Web Speech API) |
| Haptic Feedback Layer | `KioskView.jsx` (`vibrate()` via the Vibration API) |
| Feedback & Learning Engine | `feedback/` (`InteractionEvent`, `Feedback`) + `analytics/services.py`'s on-demand, non-mutating learning signal — see [PHASE_7.md](PHASE_7.md) for why the earlier automatic `AbilityProfile.update_dimension_confidence()` hook was retired |
| Analytics / Evaluation Module | `analytics/views.py` + `analytics/services.py` (Phase 7: outcome score, adaptation/barrier effectiveness) |

The Safety Rule Engine (`adaptations/services/rules.py`) is the one addition beyond
this list, called out separately in the spec's Part 7/26 — it is what actually
enforces "the LLM proposes, the rule engine disposes."

## Why a hybrid AI approach

`ai_engine/services/decision_engine.py` never lets the LLM's output reach the
frontend unchecked:

1. `adaptations/services/scoring.py` deterministically ranks every candidate
   adaptation for every detected barrier — this always runs, AI or not.
2. If an AI provider is configured, the LLM is asked to pick one candidate **id**
   per barrier from that pre-scored list, plus a short rationale.
3. The response is parsed through a Pydantic schema (`ai_engine/services/schemas.py`).
   Any decision whose `selected_adaptation` isn't in that barrier's candidate set is
   discarded and replaced with the deterministic top-scored pick for that barrier
   only — a partially-wrong AI response never sinks the whole session.
4. Whatever was chosen (AI or fallback) still passes through
   `adaptations/services/rules.py`, which independently re-checks it's enabled,
   allowed for this task, and flags high-risk adaptations for explicit confirmation.

See [AI_DECISION_ENGINE.md](AI_DECISION_ENGINE.md) for the full contract.

## Frontend structure

```
frontend/src/
├── services/api.js        one function per REST endpoint
├── hooks/useAbilityOSDemo.js   drives the pipeline (start → ... → apply → events →
│                                complete/abandon → feedback)
├── components/
│   ├── ConsentGate.jsx      Part 27 consent step
│   ├── KioskView.jsx        the simulated kiosk — real adaptive rendering + Phase 7
│   │                        event firing
│   ├── FeedbackForm.jsx     Phase 7 short, user-facing feedback screen
│   ├── OutcomeSummary.jsx   Phase 7 plain-language outcome summary
│   ├── DeveloperPanel.jsx   judge-facing "why" panel, extended in Phase 7 with the
│   │                        Outcome/Assistance/Feedback/Learning Signal chain
│   ├── ConfirmDialog.jsx    high-risk adaptation confirmation gate
│   └── MetricsPanel.jsx     before/after table
├── pages/
│   ├── DemoPage.jsx         wires the above together
│   └── AnalyticsPage.jsx    Phase 7 accessibility outcomes dashboard
└── App.jsx / main.jsx
```

`KioskView` computes its rendering from three real inputs: the environment's control
sizes/contrast (from the backend), the detected barriers, and the merged `ui_effects`
of whichever adaptations were approved and applied. Nothing about the "before" vs.
"after" appearance is hardcoded — it is the same component rendering different props.
