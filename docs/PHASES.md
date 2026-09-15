# Development Phases

AbilityOS was built phase-by-phase, each phase implemented, tested, and approved
before the next began. This is a summary — see each phase's own document for the
full detail.

## Phase 1 — Foundation
Django + DRF backend, React (Vite) frontend, the database schema for users,
ability profiles, tasks, environments, barriers, and adaptations. `GET
/api/health/` proves the full React → Django → Database chain works. No
functionality specific to a phase report exists for Phase 1 beyond this repo's
initial commit and README.

## Phase 2 — Ability Profile
The functional, non-diagnostic Ability Profile: 9 dimensions (vision, hearing,
dexterity, reach, mobility, speech, cognition, fatigue, reaction speed), each
with a controlled vocabulary (`abilities/constants.py`), a `level`/`confidence`/
`source` per dimension, and "manual beats inferred beats default" precedence.
Consent-gating (`users.ConsentRecord`) before any profile is used for adaptation.
Three seeded demo personas. See `docs/ABILITY_PROFILE.md`.

## Phase 3 — Task Understanding + Environment Understanding
Deterministic `task_id` → `TaskDescriptor` and `environment_id` →
`EnvironmentDescriptor` lookups (`tasks/`, `environments/`) — facts only, no
barrier judgement yet. Optional computer-vision environment analysis
(`VISION_ENABLED`), off by default; the JSON-fixture path is what the demo uses.
See `docs/PHASE_3.md`.

## Phase 4 — Barrier Detection
Deterministic, threshold-based mismatch detection between the Ability Profile,
task, and environment (`barriers/services/`) — five barrier types
(`small_tap_targets`, `low_contrast`, `too_many_choices`, `audio_only_alert`,
`fatigue_degraded_precision`), each rule documented with its exact threshold. No
ML, no LLM — a barrier either is or isn't present by the rules. See
`docs/PHASE_4.md`.

## Phase 5 — Adaptation Engine + AI Decision Engine + Safety Validation
A fixed, pre-approved catalogue of 12 adaptations. Deterministic scoring
(`Benefit + Relevance + Preference + Confidence − Cost − Risk`,
`adaptations/services/scoring.py`). An optional, provider-agnostic AI Decision
Engine that can only select from the pre-scored candidate pool — its output is
schema-validated and any invalid/hallucinated response falls back to the
deterministic top pick. An independent Safety Rule Engine
(`adaptations/services/rules.py`) re-validates whatever was chosen — "the AI
proposes, the rule engine disposes." See `docs/PHASE_5.md` and
`docs/AI_DECISION_ENGINE.md`.

## Phase 6 — Adaptive Kiosk
The approved adaptation actually changes the kiosk: real CSS/behavior changes
driven by `Adaptation.ui_effects`, an Adaptation Indicator using respectful,
non-medical language, a demonstration-only View Original/View Adaptive toggle
that never bypasses backend safety validation, and a Developer/System panel
showing the full decision chain. Unknown/invalid adaptations fail safe (standard
kiosk renders). See `docs/PHASE_6.md`.

## Phase 7 — Feedback, Interaction Analytics & Adaptive Learning
Outcome measurement: an explicit session lifecycle and state machine,
structured step-level `InteractionEvent`s (never raw input), a short
user-facing feedback screen, a deterministic Outcome Score and Learning Signal
(no AI, no auto-mutation of the Ability Profile), and an accessibility-outcomes
analytics dashboard (standard vs. adaptive comparison, per-adaptation/
per-barrier observed outcomes). See `docs/PHASE_7.md`.

## Phase 8 — Integration, Hardening & Deployment Readiness
No new product feature — this phase makes Phases 1–7 work as one coherent,
reliable, demonstrable product: a repository-wide audit, centralized ownership
checks extended to every session/feedback endpoint, hardened error handling
(no raw exception leakage outside `DEBUG`), corrected logging configuration,
lightweight rate limiting, a frontend error boundary, an accessibility pass,
`.env.example` verification, and updated/rewritten documentation (this file,
`docs/DEMO_GUIDE.md`, `README.md`, `docs/ARCHITECTURE.md`). See
`docs/PHASE_8.md` for the full audit and the changes it produced.
