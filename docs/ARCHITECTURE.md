# Architecture

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
| Feedback + learning update | `POST /api/interactions/{id}/feedback/` | `record_feedback()` |
| Developer panel summary | `GET /api/interactions/{id}/summary/` | `summary()` |

## Django apps ↔ spec's 12 conceptual modules

| Spec module | Django app / file |
|---|---|
| User & Consent Management | `users/` (`User`, `ConsentRecord`) |
| Ability Profile Manager | `abilities/` (`AbilityProfile`) |
| Task Understanding Engine | `tasks/` (`Task`, `TaskStep`) |
| Environment Understanding Engine | `environments/` (`Environment`) + `ai_engine/services/vision_service.py` |
| Barrier Detection Engine | `barriers/services/detection.py` |
| AI Decision Engine | `ai_engine/services/decision_engine.py`, `llm_client.py`, `schemas.py`, `prompts.py` |
| Adaptation Engine | `adaptations/services/scoring.py` + `Adaptation` catalogue |
| Adaptive UI Renderer | `frontend/src/components/KioskView.jsx` |
| Voice Interface | `KioskView.jsx` (`speak()` via Web Speech API) |
| Haptic Feedback Layer | `KioskView.jsx` (`vibrate()` via the Vibration API) |
| Feedback & Learning Engine | `feedback/` + `AbilityProfile.update_dimension_confidence()` |
| Analytics / Evaluation Module | `analytics/views.py` |

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
├── hooks/useAbilityOSDemo.js   drives the pipeline (start → analyze → ... → apply)
├── components/
│   ├── ConsentGate.jsx      Part 27 consent step
│   ├── ProfileSwitcher.jsx  switch between the 3 demo personas
│   ├── KioskView.jsx        the simulated kiosk — real adaptive rendering
│   ├── DeveloperPanel.jsx   judge-facing "why" panel (Part 14/39)
│   ├── ConfirmDialog.jsx    high-risk adaptation confirmation gate
│   └── MetricsPanel.jsx     before/after table
├── pages/
│   ├── DemoPage.jsx         wires the above together
│   └── AnalyticsPage.jsx    Part 22 dashboard
└── App.jsx / main.jsx
```

`KioskView` computes its rendering from three real inputs: the environment's control
sizes/contrast (from the backend), the detected barriers, and the merged `ui_effects`
of whichever adaptations were approved and applied. Nothing about the "before" vs.
"after" appearance is hardcoded — it is the same component rendering different props.
