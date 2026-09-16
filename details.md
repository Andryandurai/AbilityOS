# AbilityOS — Complete Project Details

### An Operating System for Human Abilities

**Track:** BME × Assistive Technology
**Challenge:** One Small Change

> "Technology that adapts to the person — not the other way around."

---

**Document purpose.** This file is written so a new developer, teammate, judge,
evaluator, researcher, or future AI coding assistant can understand the entire
AbilityOS project by reading only this file. It documents the repository **as it
actually exists today** — every model name, API endpoint, adaptation ID, barrier
ID, threshold, environment variable, and command below was verified directly
against the source code while writing this document, not copied from the
original concept documentation. Where the original concept ("AbilityOS —
Complete Project Documentation", the hackathon specification this project was
built against) describes something broader than what is implemented, that gap is
called out explicitly and classified as **Implemented**, **Partially
Implemented**, **Simulated**, **Optional**, or **Future Scope**.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Core Idea](#3-core-idea)
4. [Who AbilityOS Is For](#4-who-abilityos-is-for)
5. [Key Differentiation](#5-key-differentiation)
6. [Project Scope](#6-project-scope)
7. [Complete System Workflow](#7-complete-system-workflow)
8. [Ability Profile](#8-ability-profile)
9. [Task Understanding](#9-task-understanding)
10. [Environment Understanding](#10-environment-understanding)
11. [Barrier Detection Engine](#11-barrier-detection-engine)
12. [Adaptation Engine](#12-adaptation-engine)
13. [AI Decision Engine](#13-ai-decision-engine)
14. [Safety Validation](#14-safety-validation)
15. [Adaptive UI / Kiosk](#15-adaptive-ui--kiosk)
16. [Voice and Haptic Interfaces](#16-voice-and-haptic-interfaces)
17. [Interaction Sessions](#17-interaction-sessions)
18. [Feedback System](#18-feedback-system)
19. [Analytics and Evaluation](#19-analytics-and-evaluation)
20. [Learning Signal](#20-learning-signal)
21. [Complete Technical Architecture](#21-complete-technical-architecture)
22. [Frontend Architecture](#22-frontend-architecture)
23. [Backend Architecture](#23-backend-architecture)
24. [Database Architecture](#24-database-architecture)
25. [API Architecture](#25-api-architecture)
26. [AI Workflow](#26-ai-workflow)
27. [Data Flow](#27-data-flow)
28. [Security](#28-security)
29. [Privacy](#29-privacy)
30. [Accessibility](#30-accessibility)
31. [Error Handling and Fallbacks](#31-error-handling-and-fallbacks)
32. [Technology Stack](#32-technology-stack)
33. [Repository Structure](#33-repository-structure)
34. [Phase-by-Phase Implementation](#34-phase-by-phase-implementation)
35. [Current MVP](#35-current-mvp)
36. [Running the Project](#36-running-the-project)
37. [Environment Configuration](#37-environment-configuration)
38. [Database Setup](#38-database-setup)
39. [Demo Mode](#39-demo-mode)
40. [Testing](#40-testing)
41. [Deployment](#41-deployment)
42. [Limitations](#42-limitations)
43. [Impact and Benefits](#43-impact-and-benefits)
44. [Future Scope](#44-future-scope)
45. [Research Opportunities](#45-research-opportunities)
46. [PPT-Ready Project Summary](#46-ppt-ready-project-summary)
47. [Important Developer Rules](#47-important-developer-rules)
48. [Final Project Summary](#48-final-project-summary)

---

## 1. Project Overview

Most technology assumes everyone interacts with an interface the same way.
AbilityOS introduces a software reasoning layer that considers three things
together — **PERSON + TASK + ENVIRONMENT** — and identifies the specific
mismatch preventing comfortable, independent interaction. It then selects the
smallest useful intervention and applies it. **The task itself never changes —
only the interaction does.**

**Worked example (the project's primary demo scenario, fully implemented):** A
person with reduced interaction precision (`dexterity: reduced-precision`)
approaches a ticket kiosk. The kiosk's primary control is 120×40 pixels — below
the system's 88px comfortable-target-size threshold. AbilityOS detects
`small_tap_targets`, scores `increase_target_size` as the best candidate
adaptation, an independent safety rule validates it, the kiosk's buttons
actually enlarge (`button_scale: 1.8`), and the person completes the same
ticket-purchase task with an easier interaction. AbilityOS then records whether
that actually helped — completion, errors, assistance requested, and a
self-reported ease rating.

Every step of that example is real, working code in this repository, not a
mockup — see [§34](#34-phase-by-phase-implementation) and [§35](#35-current-mvp)
for exactly what runs live versus what remains a fixture or future scope.

## 2. Problem Statement

- Standard interfaces are designed around an assumed "average" user; a
  functional mismatch (not a disability in the abstract, but *this* task in
  *this* environment) is often the actual barrier.
- Built-in accessibility features are typically **static** — a global
  "large text" or "high contrast" OS toggle, applied everywhere, all the time,
  whether the current task needs it or not.
- Accessibility settings are usually configured **manually**, often by a
  caregiver, and rarely per-task.
- Different applications implement accessibility inconsistently — there is no
  shared reasoning layer a new app can plug into.
- Functional ability is not fixed: it varies by task, by environment, and even
  within a session (fatigue is one of AbilityOS's own tracked dimensions — see
  [§8](#8-ability-profile)).
- A person may only need an adaptation for *one* specific task, not every
  interaction — turning on every accessibility feature at once adds
  interaction cost (more steps, more choices, more cognitive load) for no
  benefit when the barrier being solved doesn't call for it.
- Manual reconfiguration is a real, recurring burden, often falling on a
  caregiver rather than the person themselves.

AbilityOS's response to this is documented in [§3](#3-core-idea): detect the
*specific* mismatch, and apply only what resolves it.

## 3. Core Idea

> **"Find the smallest change that makes the task independently achievable."**

AbilityOS does not enable every accessibility feature it has available. If
enlarging a button resolves the barrier, the system does not also switch the
person to voice control — voice control has its own interaction cost and risk
that would be introduced for no additional benefit. This is enforced
numerically, not just as a design philosophy: every candidate adaptation is
scored with the same formula (implemented exactly as-is in
`backend/adaptations/services/scoring.py`):

```
Adaptation Score =  Accessibility Benefit
                   + Task Relevance
                   + User Preference
                   + Confidence
                   − Interaction Cost
                   − Risk
```

All six weights are `1.0` in the current implementation
(`backend/adaptations/services/config.py`) — a deliberate choice documented in
that file's own docstring: the "smallest useful intervention" behavior comes
from the catalogue's own cost/risk *values* being genuinely larger for a more
disruptive adaptation, not from artificially weighting cost or risk higher than
benefit. A hand-tuned multiplier would let the scoring formula silently override
what the adaptation catalogue itself says about a given intervention.

## 4. Who AbilityOS Is For

Framed functionally, matching the Ability Profile's own non-diagnostic design
(see [§8](#8-ability-profile)):

- People with reduced dexterity or interaction precision (temporary or
  permanent) using touch interfaces.
- People who need higher contrast or larger text to read a screen comfortably.
- People who are more comfortable with fewer simultaneous choices or a guided,
  step-by-step flow.
- People who rely on visual information because audio alone isn't reliable for
  them.
- People experiencing temporary fatigue that reduces precision or attention
  (the system models this as a first-class, temporary dimension — see the
  `fatigue` dimension in [§8](#8-ability-profile)).
- Organizations operating public-facing kiosks, terminals, or digital services
  who want a reusable accessibility reasoning layer instead of hand-building
  accessibility logic per application.

## 5. Key Differentiation

| AbilityOS | Typical accessibility feature |
|---|---|
| Reasons over person + task + environment together | Applies globally regardless of context |
| Selects the *smallest* sufficient adaptation, numerically scored | Often an all-or-nothing toggle |
| Independently safety-validates any AI-assisted decision before it reaches the UI | AI (where present) often has direct UI control |
| Measures whether the adaptation actually helped (Phase 7) | Rarely measures outcome at all |
| Functional, non-diagnostic profile | Sometimes tied to a stated disability/diagnosis |
| Deterministic fallback — works fully with zero AI configured | Often depends on a single vendor's ML pipeline |

## 6. Project Scope

**In scope for this hackathon prototype** (all of [§34](#34-phase-by-phase-implementation)'s
8 phases): one demo task (ticket purchase), one primary kiosk environment
fixture, five barrier types, a 12-entry fixed adaptation catalogue, an optional
LLM-assisted decision layer with a deterministic fallback, an independent safety
validator, a real adaptive kiosk UI, session/event tracking, a short feedback
loop, and an accessibility-outcomes analytics dashboard.

**Explicitly out of scope** (see [§44](#44-future-scope)): production
authentication/deployment infrastructure, real camera-based (live) computer
vision, OS-level or device-level integration, multiple tasks/environments beyond
the seeded demo set, and any form of automatic profile/recommendation learning
loop beyond the single-session Learning Signal described in [§20](#20-learning-signal).

## 7. Complete System Workflow

```
PERSON
  │
  ▼
ABILITY PROFILE  (functional, consented, non-diagnostic)
  │
  ▼
TASK  (what the person is trying to accomplish)
  │
  ▼
ENVIRONMENT  (the interface/device facts right now)
  │
  ▼
BARRIER DETECTION  (deterministic mismatch detection)
  │
  ▼
ADAPTATION ENGINE  (deterministic scoring of every candidate)
  │
  ▼
AI DECISION ENGINE  (optional — ranks/selects from the same scored candidates)
  │
  ▼
SAFETY VALIDATION  (independent — re-checks everything, AI or not)
  │
  ▼
APPROVED ADAPTATION
  │
  ▼
ADAPTIVE KIOSK  (the interface actually changes)
  │
  ▼
USER INTERACTION  (the same task, an easier interaction)
  │
  ▼
OUTCOME  (completion, errors, assistance — server-authoritative)
  │
  ▼
FEEDBACK  (a short, subjective, three-question screen)
  │
  ▼
ANALYTICS  (aggregated, real, never fabricated)
  │
  ▼
LEARNING SIGNAL  (structured evidence, not an ML model — see §20)
```

Every arrow above is a real, working transition in this codebase. The exact
REST calls behind each arrow are documented in [§25](#25-api-architecture).

## 8. Ability Profile

**Status: Implemented.** Model: `abilities.AbilityProfile`
(`backend/abilities/models.py`). Controlled vocabulary source of truth:
`backend/abilities/constants.py`.

The Ability Profile is **functional, consented, and explicitly non-diagnostic**
— it never asks about or stores a medical condition. It stores nine dimensions,
each an independent question about how someone interacts *right now*, not a
label about who they are:

| Dimension | Allowed values (first = "no barrier" baseline) | What it affects |
|---|---|---|
| `vision` | `typical`, `low-contrast-sensitive`, `large-text-needed` | Triggers the `low_contrast` barrier rule |
| `hearing` | `typical`, `partial`, `relies-on-visual` | Triggers the `audio_only_alert` barrier rule |
| `dexterity` | `typical`, `reduced-precision`, `single-tap-only` | Triggers the `small_tap_targets` barrier rule |
| `reach` | `full`, `limited-upper`, `seated` | Descriptive; no barrier rule currently keys on it |
| `mobility` | `typical`, `limited`, `stationary` | Descriptive; no barrier rule currently keys on it |
| `speech` | `typical`, `limited`, `unavailable` | Descriptive; relevant to voice-input adaptations' applicability |
| `cognition` | `typical`, `prefers-fewer-choices`, `needs-step-by-step` | Triggers the `too_many_choices` barrier rule |
| `fatigue` | `fresh`, `moderate`, `high` | Triggers the `fatigue_degraded_precision` barrier rule |
| `reaction_speed` | `typical`, `slower`, `needs-extended-time` | Descriptive; no barrier rule currently keys on it |

Each dimension's stored value is `{level, confidence, source}` — `confidence`
is a `0.0–1.0` float, and `source` is one of `manual` (a person edited it
directly — highest trust), `inferred`, `session_signal` (system-observed,
lower trust tier), or `default` (never edited). "Manual beats inferred beats
default" is enforced in `abilities/services/profile_service.py` — a
higher-trust value is never silently overwritten by a lower-trust write.

A profile also stores `preferred_modality` (`visual` / `voice` / `haptic` /
`mixed`) and a free-form `preferences` JSON field (present in the model, not
exercised by any specific UI flow beyond storage/retrieval today).

**Note on Phase 7's retired auto-mutation:** an earlier pass had a mechanism
that automatically nudged a dimension's `confidence` up or down after every
session's feedback. This was removed in Phase 7 specifically because it was
found to silently feed back into future adaptation scoring — see
`docs/PHASE_7.md` §3 for the full reasoning. The Ability Profile today is only
ever changed by an explicit person-initiated edit (`PATCH
/api/users/{id}/ability-profile/`) — never automatically.

## 9. Consent

**Status: Implemented.** Model: `users.ConsentRecord`
(`backend/users/models.py`). Service: `users/services/consent_service.py`.

Consent exists because the Ability Profile, while non-diagnostic, is still
personal functional data, and nothing in AbilityOS is allowed to use it for
adaptation without an explicit, checkable grant. `ConsentRecord` stores
`granted` (bool), `scope` (a JSON list — currently the single value
`interaction_adaptation`), and `granted_at`. `is_consented_for_adaptation(user)`
(`users/services/consent_service.py`) is checked before any barrier-detection
or adaptation-recommendation call proceeds — an unconsented request is
rejected with HTTP 409 (session-based) or 403 (standalone), never silently
allowed through.

A person can view and update their own consent via `GET`/`POST
/api/users/{id}/consent/`. Demo personas are seeded with consent already
granted (Phase 2's own explicit requirement, so the hackathon demo doesn't
start blocked) — but the Consent screen in the actual UI flow
(`frontend/src/pages/ConsentPage.jsx`) is still a real step that performs a
real `POST`, not a decorative pass-through.

## 10. Task Understanding

**Status: Implemented (single demo task).** Models: `tasks.Task`,
`tasks.TaskStep` (`backend/tasks/models.py`). Service:
`tasks/services/task_service.py`.

Task Understanding answers exactly one question: **"What is the person trying
to accomplish?"** It does **not** determine accessibility barriers — that is
exclusively [§11](#11-barrier-detection-engine)'s job, kept as a deliberately
separate concern.

The one seeded demo task is `purchase_ticket` ("Buy a ticket"), with four
ordered steps (`TaskStep`, each carrying its own `controls` JSON list):

1. `select_destination` — choose a destination (4 controls: Central Station,
   Airport, Hospital, University)
2. `select_ticket_type` — choose Single or Return
3. `select_quantity` — a quantity stepper (`quantity_minus`/`quantity_plus`)
4. `confirm_purchase` — the `buy_ticket` control

There is no separate `TaskControl` model — a control is a plain dict
(`{id, type, label, interaction_type}`) inside `TaskStep.controls`
(a `JSONField`), not its own database table. `GET /api/tasks/` lists tasks;
`POST /api/tasks/analyze/` returns the full `TaskDescriptor` (name,
description, steps, controls) for a given `task_id` — a deterministic
database lookup, never an LLM call.

## 11. Environment Understanding

**Status: Implemented via a JSON fixture (MVP); real-time computer vision is
implemented as an optional path but is not the demo default.** Model:
`environments.Environment` (`backend/environments/models.py`). Service:
`environments/services/analyzer.py`.

An `Environment` row stores `environment_id`, `name`, `source`
(`fixture` / `vision`), and a `data` JSON blob: screen dimensions, a `controls`
list (each with pixel `width`/`height`), `contrast` (a 0–1 ratio), `noise_level`,
`lighting`, `visible_choice_count`, and whether an `audio_alert` exists with or
without a `visual_alert_mirror`.

**Current MVP path (what the demo actually uses):** `kiosk_standard`, a JSON
fixture at `backend/fixtures/kiosk_standard.json`, loaded by
`EnvironmentAnalyzer.analyze_fixture()` — a deterministic lookup, not a live
sensor read.

**Optional, not the demo path:** `ai_engine/services/vision_service.py`
implements an OpenCV/OCR-based screenshot analysis path, gated behind
`VISION_ENABLED=false` by default and guarded so a missing OpenCV install never
breaks the fixture path. This is real, callable code — but it analyzes a
*submitted screenshot*, not a live camera feed, and is not what the seeded demo
exercises. **Real-time, camera-based environment sensing is Future Scope**, not
implemented — see [§44](#44-future-scope).

## 12. Barrier Detection Engine

**Status: Implemented, fully deterministic — no ML, no LLM.**

Barrier detection answers: `AbilityProfile + TaskDescriptor + EnvironmentDescriptor
→ Detected Barriers`. The **live, production path** the real kiosk actually
uses is `backend/barriers/services/detection.py`. Five barrier types are
currently implemented, each a threshold comparison:

| Barrier ID (`Barrier.barrier_type`) | Ability dimension | Detection rule | Example evidence text |
|---|---|---|---|
| `small_tap_targets` | `dexterity` | Smallest primary control dimension `< 88px` (`COMFORTABLE_TARGET_PX`), and the profile's dexterity level has nonzero severity | *"Primary control is 120x40px, below the 88px comfortable target size for dexterity level 'reduced-precision'."* |
| `low_contrast` | `vision` | Environment `contrast < 0.6` (`COMFORTABLE_CONTRAST`), and vision level has nonzero severity | *"Screen contrast ratio 0.52 is below the 0.60 comfortable threshold for vision level 'large-text-needed'."* |
| `too_many_choices` | `cognition` | `visible_choice_count > 4` (`COMFORTABLE_CHOICE_COUNT`), and cognition level has nonzero severity | *"8 simultaneous choices exceed the 4-choice comfortable limit for cognition level 'needs-step-by-step'."* |
| `audio_only_alert` | `hearing` | The task/environment raises an audio alert with no `visual_alert_mirror`, and hearing level is `partial` or `relies-on-visual` | *"Task raises an audio-only alert with no visual/haptic mirror; hearing level is 'relies-on-visual'."* |
| `fatigue_degraded_precision` | `fatigue` | Fatigue level is `moderate`/`high` **and** dexterity is otherwise `typical` (this rule only fires when fatigue is the *only* reason precision is reduced) | *"Session fatigue is 'moderate'; effective precision/attention is temporarily reduced below baseline."* |

Severity is a `0.0–1.0` float computed per-rule from how far past the
threshold the measurement falls (e.g. for tap targets, how far below 88px the
smallest offending control is) combined with the profile dimension's own base
severity for that level. `confidence` is carried through directly from the
triggering dimension's stored confidence. Detected barriers are sorted
severity-descending and persisted as `Barrier` rows scoped to the session.

**Architectural note — two barrier engines coexist by design, not by
accident.** A second, structurally similar rule engine
(`backend/barriers/services/rules.py` + `detector.py`) exists purely to power
the **standalone**, non-session Phase 4 demo endpoint
(`POST /api/barriers/detect/` called with `{user_id, task_id, environment_id}`
instead of `{session_id}`). It uses a slightly different barrier-type spelling
for one case (`low_contrast_text` vs. the live engine's `low_contrast`) and a
narrower trigger condition for that specific rule. Both engines are exercised
by the real test suite; the table above describes the one that actually powers
every real kiosk session (`InteractionOrchestrator.detect_barriers()` →
`barriers.services.detection.detect_and_save()`).

## 13. Adaptation Engine

**Status: Implemented.** Model: `adaptations.Adaptation`
(`backend/adaptations/models.py`). Scoring:
`backend/adaptations/services/scoring.py` (formula in [§3](#3-core-idea)).
Seeded via `backend/tasks/management/commands/seed_demo.py`.

The catalogue is **fixed and pre-approved** — nothing, including the AI
Decision Engine, can select an adaptation outside this list. All 12 current
entries:

| `name` (adaptation ID) | Display name | Resolves barrier type(s) | `ui_effects` | Risk | Requires confirmation |
|---|---|---|---|---|---|
| `increase_target_size` | Increase target size | `small_tap_targets`, `fatigue_degraded_precision` | `button_scale: 1.8`, `spacing_scale: 1.2` | Low | No |
| `increase_spacing` | Increase spacing | `small_tap_targets`, `fatigue_degraded_precision` | `spacing_scale: 1.6` | Low | No |
| `increase_contrast` | Increase contrast | `low_contrast` | `contrast: high`, `text_scale: 1.3` | Low | No |
| `simplify_navigation` | Simplify navigation | `too_many_choices` | `choice_limit: 4`, `flow: simplified` | Medium | No |
| `reduce_choice_count` | Reduce choice count | `too_many_choices` | `choice_limit: 3` | Medium | No |
| `step_by_step_flow` | Step-by-step guided flow | `too_many_choices` | `flow: guided`, `choice_limit: 1`, `progress_indicator: true` | Medium | No |
| `voice_instruction` | Voice instructions | `too_many_choices`, `low_contrast` | `voice_prompts: true` | Medium | No |
| `text_to_speech` | Text-to-speech for on-screen content | `low_contrast` | `tts: true` | Medium | No |
| `caption_audio` | Caption / mirror audio alerts | `audio_only_alert` | `banner_alert: true`, `haptics: true` | Low | No |
| `haptic_confirmation` | Haptic confirmation | `audio_only_alert`, `small_tap_targets` | `haptics: true` | Low | No |
| `alternative_voice_input` | Alternative voice input | `small_tap_targets` | `voice_input: true` | **High** | **Yes** |
| `confirmation_before_irreversible_action` | Confirm before irreversible action | `small_tap_targets`, `fatigue_degraded_precision` | `confirm_step: true` | Low | No |

Every adaptation is **reversible in the sense that it is presentation-only** —
`Adaptation.ui_effects` is restricted to a fixed key allowlist
(`ALLOWED_UI_EFFECT_KEYS` in `adaptations/services/config.py`) that a safety
rule enforces (see [§14](#14-safety-validation)); none of them can alter task
data or business logic. `alternative_voice_input` is the one high-risk entry —
switching a person's entire input modality is judged significant enough to
require an explicit confirmation step before it's ever applied, even though the
rule engine already approved it.

**Candidate generation and scoring** (`adaptations/services/scoring.py`,
`rank_candidates_for_barrier()`): for a given barrier, every enabled adaptation
whose `resolves_barrier_types` includes that barrier type is scored with the
formula in [§3](#3-core-idea) and ranked. This always runs — with or without
an AI provider configured — because the AI (when present) only ever ranks
*this same, already-scored* candidate pool; it never invents its own.

## 14. AI Decision Engine

**Status: Implemented, fully optional.** Orchestration:
`backend/ai_engine/services/decision_engine.py` (session-based),
`backend/adaptations/services/recommender.py` (standalone Phase 5 demo path).
Provider client: `backend/ai_engine/services/llm_client.py`. Schemas
(Pydantic): `backend/ai_engine/services/schemas.py`.

**What the AI does:**
- Reasons over the barriers already deterministically detected (facts only —
  no raw Ability Profile, no free text about the person).
- Ranks/selects from the exact, pre-scored candidate pool
  `adaptations/services/scoring.py` already computed for that barrier.
- Returns a short natural-language rationale for its choice.

**What the AI explicitly does not do** (enforced in code, not just by
convention):
- It cannot diagnose a user — it never receives anything beyond the barrier's
  own functional evidence.
- It cannot invent an ability profile, a barrier, or an adaptation — its JSON
  response is validated against a Pydantic schema, and any
  `selected_adaptation_id` (or any entry in a ranked list) that isn't in the
  candidate pool it was given is discarded.
- It cannot override the safety validator — see [§14](#14-safety-validation);
  every AI choice is independently re-checked afterward, with no exception.
- It cannot directly modify the UI — its output is a data selection consumed
  by the same code path a deterministic fallback also produces; nothing in the
  frontend ever calls the AI directly.

**Provider abstraction** (`llm_client.py`): a single `call(system_prompt,
user_prompt)` function. `AI_PROVIDER` is `openai`, `anthropic`, or `none`
(default). With `openai`, it calls the Chat Completions API with
`response_format={"type": "json_object"}`; with `anthropic`, the Messages API.
If the configured provider's Python SDK isn't installed, the API key is
missing, the call times out, or any exception occurs, `LLMUnavailableError` is
raised and the caller falls back to deterministic scoring — **the whole
system, including every core reasoning stage, works correctly with
`AI_PROVIDER=none`**, which is the default and what the seeded demo runs with.

**The hybrid architecture, in one line: "The LLM proposes; the rule engine
disposes."**

```
Deterministic scoring (always runs)
        │
        ▼
AI provider configured? ──No──► use the top-scored candidate directly
        │ Yes
        ▼
LLM call (JSON response, schema-validated)
        │
   valid & in candidate pool? ──No──► discard, use top-scored candidate
        │ Yes
        ▼
Selected candidate (source = "ai")
        │
        ▼
Safety Validation (independent — §14)
```

## 15. Safety Validation

**Status: Implemented, independent of the AI by construction.**

Two validators exist, matching the "two engines coexist" pattern noted in
[§12](#12-barrier-detection-engine):

**Live path** (`backend/adaptations/services/rules.py`,
`validate_adaptation()`), used by every real session:
1. The adaptation must be `enabled` in the catalogue.
2. The adaptation must be allowed for the current `task_id`
   (`Adaptation.is_allowed_for_task()`).
3. If `risk_level == "high"` or `requires_confirmation` is set, the result is
   `approved=True, requires_confirmation=True` — approved, but gated behind an
   explicit confirmation step before application, never silently auto-applied.

**Standalone path** (`backend/adaptations/services/validator.py`,
`AdaptationSafetyValidator`), used by the Phase 5 standalone demo endpoint —
9 named, independently testable rules: (1) exists in the catalogue, (2) is
active/enabled, (3) explicitly supports the detected barrier type, (4) is
compatible with the relevant ability dimension, (5) is allowed for the task,
(6–7) does not alter the task itself and only uses an allowlisted `ui_effects`
key, (8) high risk → requires confirmation, (9) if the top candidate fails, the
recommender automatically tries the next-highest-scored candidate rather than
failing outright.

```
AI decision (or deterministic top pick)
        │
        ▼
Safety Validator  (independent — re-checks from scratch, trusts nothing)
        │
   ┌────┴────┐
Approved   Rejected
   │            │
   ▼            ▼
Adaptive UI   Next-best candidate tried, or the standard interface if none pass
```

**Fallback behavior, all real code paths:**
- AI unavailable/invalid → deterministic scoring's top candidate.
- Adaptation fails validation → the recommender tries the next-best scored
  candidate for that barrier.
- No candidate passes at all → `selected_adaptation: null`, reason
  `"no_safe_adaptation"` — the standard (unadapted) kiosk is used; the system
  never fabricates an approval to avoid an empty result.

## 16. Adaptive UI / Kiosk

**Status: Implemented.** Component: `frontend/src/components/KioskView.jsx`.
The kiosk simulates a public "City Transit" ticket-purchase terminal — the same
component renders both the **standard** and **adaptive** experience; nothing
is a separate screen or a canned screenshot swap.

The kiosk reads **only** the specific `ui_effects` keys the backend actually
returned (never an Ability Profile value, never a barrier type directly — see
[§28](#28-security)'s "frontend never independently decides" rule):

| `ui_effects` key | What the kiosk actually does |
|---|---|
| `button_scale` | Scales tap targets via a CSS custom property; also removes the reduced-dexterity "missed tap" simulation once a control is comfortably sized |
| `spacing_scale` | Scales gaps between controls |
| `contrast: "high"` | Switches to a high-contrast palette |
| `text_scale` | Scales all kiosk text |
| `flow: "guided"`/`"simplified"` | One-question-at-a-time flow with a visible "Step X of Y" indicator and a "← Back" control, instead of everything on one screen |
| `choice_limit` | Paired with `flow` — bounds visible options per step |
| `voice_prompts` / `tts` | Speaks the current step/result via the Web Speech API (one-shot, on request — see [§17](#17-voice-and-haptic-interfaces)) |
| `banner_alert` | Mirrors the kiosk's audio purchase alert as an on-screen banner |
| `haptics` | Fires a device vibration alongside a successful tap or the purchase result |
| `confirm_step` | Inserts an explicit "Yes, buy / Cancel" step before the (otherwise irreversible) purchase |
| `voice_input` | Present in `ui_effects` for `alternative_voice_input`; there is **no actual speech-recognition input implemented** — this is documented, intentional safe degradation (the adaptation still applies and is shown as active; the interaction itself is unchanged) rather than a fabricated capability |
| `progress_indicator` | Its visible effect is already produced by `flow: "guided"`'s step counter; no separate handling needed |

An unrecognized key is silently ignored by construction — `KioskView` only
ever reads the keys above — which is how "unknown adaptation fails safe" is
guaranteed without a special-case check.

**Standard vs. adaptive comparison** ("View Original" / "View Adaptive"
toggle, `DemoPage.jsx`): re-renders the identical `KioskView` with an empty
`appliedEffects` object for "Original." It is the same component, the same
detected barriers, the same safety-validated result — never a second code path
or a bypass of backend validation.

An **Adaptation Indicator** banner (`✓ Interface personalized for easier
interaction`) appears only when `appliedEffects` is non-empty — respectful,
functional language, never a diagnostic or medical term.

## 17. Voice and Haptic Interfaces

**Status: Implemented as one-shot, on-demand browser APIs — not continuous,
not recorded.**

- **Text-to-speech**: `window.speechSynthesis` (Web Speech API), wrapped in
  try/catch. Speaks the current guided-flow step name or the purchase result,
  once, when `voice_prompts`/`tts` is active. **No speech recognition (voice
  input) is implemented** — `alternative_voice_input`'s `voice_input` effect
  key exists in the catalogue but has no corresponding input-capture code (see
  [§16](#16-adaptive-ui--kiosk)).
- **Haptics**: `navigator.vibrate()` (Vibration API), wrapped in try/catch,
  fired on a successful tap or the purchase result when `haptics` is active.
- **Fallback**: if either browser API is unavailable (unsupported browser, no
  vibration hardware), the call silently no-ops — the kiosk interaction
  continues normally with only the visual/haptic-absent path.
- **Privacy**: nothing in this codebase records or transmits microphone audio,
  camera video, or any continuous sensor stream. There is no "listening" state
  anywhere in the kiosk.

## 18. Interaction Sessions

**Status: Implemented.** Model: `feedback.InteractionSession`
(`backend/feedback/models.py`). Orchestrated by
`backend/api/services/orchestrator.py::InteractionOrchestrator`.

One `InteractionSession` row represents one person's one attempt at one task in
one environment. Status values and the enforced state machine:

```
started → analyzed → adapted → in_progress → completed
                                            ↘ abandoned
                                            ↘ failed
```

`completed`/`abandoned`/`failed` are **terminal** — `InteractionSession.
transition_to()` raises rather than allowing a duplicate completion or e.g.
`completed → abandoned`. Key fields: `user`, `task`, `environment`, `status`,
`ai_used` (bool), `baseline_mode` (bool — `True` = "standard" experience for
before/after comparison), `is_seed` (marks demo-seeded rows), `assistance_count`
(int), `completed_at` (server-set, once), and `ability_profile_snapshot` — a
JSON copy of the profile's dimensions **at session start**, so a historical
session stays interpretable even if the person's live profile later changes.
`completion_time_ms` is a computed property (`completed_at − created_at`), not
a separately-stored, potentially-stale field.

`Barrier` and `AdaptationResult` rows are FK'd to the session and never mutated
after creation (aside from `confirmed`/`applied` flags) — this is what already
satisfies "historical snapshot" for barriers/decisions, so no second,
duplicate snapshot field was added for them.

## 19. Interaction Events

**Status: Implemented.** Model: `feedback.InteractionEvent`
(`backend/feedback/models.py`).

A structured, bounded record of one task-relevant moment — `session` (FK),
`step`, `event_type`, `control_id`, `metadata` (a `JSONField`, capped
server-side at 10 keys / 200 characters per value), `created_at`. The ten
implemented event types: `step_started`, `control_selected`,
`control_reselected`, `validation_error`, `back_navigation`,
`confirmation_opened`, `confirmation_completed`, `assistance_requested`,
`task_completed`, `task_abandoned`. `errors_count`/`retries_count`/
`backtracks_count`/`assistance_count` are **derived** from these rows
(`analytics/services.py::session_interaction_counts()`), not separately
tracked counters that could drift.

**Deliberately not captured, anywhere in this codebase:** raw keystrokes,
microphone audio, camera/video, or any unrelated application activity.
`InteractionOrchestrator._sanitize_metadata()` enforces the size cap and drops
anything that isn't a small flat mapping.

The frontend batches events locally (`useAbilityOSDemo.queueEvent`) and
flushes them in one `POST /api/interactions/{id}/events/` call rather than one
request per tap.

## 20. Feedback System

**Status: Implemented.** Model: `feedback.Feedback`
(`backend/feedback/models.py`, `OneToOneField` to the session).

A deliberately short, three-question screen
(`frontend/src/components/FeedbackForm.jsx`), shown once the task is already
marked complete/abandoned server-side:

1. **How was the experience?** → `ease_rating`, `1`–`5`
   (`Feedback.EASE_CHOICES`: Very difficult … Very easy).
2. **Did the adapted interface help?** (only asked when an adaptation was
   actually applied) → `adaptation_helpfulness`: `helped` / `somewhat_helped`
   / `did_not_help`.
3. **Did you need help from another person?** → `assistance_requested` (bool —
   the same field the in-kiosk "Ask staff for help" control also sets; the
   feedback form's answer is the person's own self-report, reused under the
   existing field name rather than duplicated under a second one).

Plus an optional free-text comment (`optional_comment`, capped server-side at
500 characters). `ease_rating`/`adaptation_helpfulness` are validated against
their controlled vocabularies — an invalid value is rejected (HTTP 400), never
silently accepted. A second submission for the same session **updates** the
same row (`Feedback.session` is `OneToOneField`, `update_or_create` is used) —
never creates a duplicate.

`Feedback` also still carries `effort`/`confidence` (1–5 self-reported fields
from an earlier pass) — kept for backward compatibility, no longer consumed
automatically by anything (see the retired auto-mutation note in
[§8](#8-ability-profile)).

## 21. Analytics and Evaluation

**Status: Implemented.** Views: `backend/analytics/views.py`. All calculation
logic centralized in `backend/analytics/services.py` — no duplication between
a view and a frontend component.

Every number is computed from real `InteractionSession`/`InteractionEvent`/
`Feedback` rows (seed data included, but always explicitly labeled — see
[§39](#39-demo-mode)) — **never a random or hard-coded value**. Endpoints and
what each returns:

| Endpoint | What it reports |
|---|---|
| `GET /api/analytics/before-after/` | Standard (`baseline_mode=True`) vs. adaptive experience: sessions, completion rate, avg. time, avg. errors, assistance rate, avg. ease |
| `GET /api/analytics/dashboard/` | Total/completed/abandoned sessions, overall metrics, adaptation usage counts, sessions per Ability Profile |
| `GET /api/analytics/adaptations/` | Per-adaptation outcome evidence (applied sessions only) — sessions, completion rate, avg. ease, assistance rate, avg. errors, and an `observed_outcome` state |
| `GET /api/analytics/barriers/` | Per-barrier-type frequency, associated adaptations, and the same `observed_outcome` vocabulary |
| `GET /api/analytics/sessions/?limit=10` | The most recent sessions (task, mode, status, ease, assistance), each explicitly labeled `is_seed` |

Every analytics endpoint returns `{"empty": true}` with no other numeric
fields when there is no data yet — "no data" is never rendered as a fabricated
0%; the frontend shows "No interaction data yet." / "Not enough sessions yet."
instead (`docs/PHASE_7.md` §39's explicit requirement).

**Example response shape** (illustrative structure, not a claimed real
measurement):

```json
{
  "note": "Prototype demonstration metrics — computed from recorded InteractionSession/InteractionEvent/Feedback rows (seed data + live demo sessions), not a production research result.",
  "adaptations": [
    {
      "adaptation_id": "increase_target_size",
      "sessions": 8,
      "completion_rate": 0.875,
      "avg_ease": 4.4,
      "assistance_rate": 0.125,
      "observed_outcome": "positive_observed_outcome",
      "confidence": 0.94
    }
  ]
}
```

## 22. Learning Signal

**Status: Implemented — structured, deterministic evidence. This is
explicitly NOT a machine-learning model**, and nothing in this repository
consumes it to automatically change a future recommendation or a person's
Ability Profile (verify this claim yourself: search the repository for any
write to `AbilityProfile` outside `abilities/services/profile_service.py`'s
explicit, person-initiated update path — there is none).

`analytics/services.py::generate_learning_signal(session, feedback)` computes,
on demand, from already-persisted `Feedback` + `AdaptationResult` + `Barrier`
rows (never stored a second time):

```json
{
  "adaptation_id": "increase_target_size",
  "task_id": "purchase_ticket",
  "barrier_type": "small_tap_targets",
  "successful": true,
  "independence_improved": true,
  "confidence": 0.3
}
```

`successful` = the task was completed. `independence_improved` = completed,
**no** assistance requested (neither the kiosk button nor the feedback form's
self-report), and (if rated) an ease of 4 or 5. `confidence` is a fixed, low
`0.3` for any single session (`SINGLE_SESSION_CONFIDENCE` in
`analytics/config.py`) — deliberately never inflated to look like statistical
certainty from one data point. Returns `null` when there's no feedback yet or
no adaptation was applied.

At the **aggregate** level (multiple sessions), `adaptation_effectiveness()`
classifies an adaptation into one of four states —
`positive_observed_outcome`, `negative_observed_outcome`, `inconclusive`, or
`insufficient_data` (below `MIN_SESSIONS_FOR_SIGNAL = 3` sessions) — via
documented, centralized thresholds in `analytics/config.py`, with aggregate
confidence growing (capped at `0.9`) with sample size. Every threshold is a
named constant with a docstring explaining its purpose — never an inline magic
number.

## 23. Complete Technical Architecture

```
                            USER
                              │
                              ▼
                   ┌─────────────────────┐
                   │  React Frontend     │
                   │  (Vite, plain JS)   │
                   │  Adaptive UI        │
                   └──────────┬──────────┘
                              │  fetch() — JSON over HTTP
                              ▼
                   ┌─────────────────────┐
                   │  Django REST API    │
                   │  (api/urls.py,      │
                   │   api/views.py)     │
                   └──────────┬──────────┘
                              │
              ┌───────────────┴───────────────┐
              │        AbilityOS Core          │
              │  (backend/*/services/, called  │
              │   in sequence by               │
              │   InteractionOrchestrator)     │
              │                                │
              │  Ability Profile               │
              │  Task Understanding            │
              │  Environment Understanding     │
              │  Barrier Detection             │
              │  Adaptation Engine (scoring)   │
              │  AI Decision Engine (optional) │◄──── External LLM provider
              │  Safety Validation             │      (OpenAI / Anthropic API,
              └───────────────┬───────────────┘       only if configured)
                              │
                              ▼
                   ┌─────────────────────┐
                   │  Adaptive Kiosk      │
                   │  Voice / Haptic      │
                   │  (browser APIs)      │
                   └──────────┬──────────┘
                              │
                              ▼
                        USER OUTCOME
                              │
                              ▼
                   ┌─────────────────────┐
                   │  Session / Events /  │
                   │  Feedback            │
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │  Analytics           │
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │  Learning Signal      │
                   │  (computed on demand) │
                   └──────────┬──────────┘
                              │
                              ▼
                 PostgreSQL (prod) / SQLite (dev, default)
```

Optional environment sensing (OpenCV/OCR, `VISION_ENABLED=false` by default) is
a separate dependency of the Environment Understanding stage only — it is never
in the safety-critical path.

## 24. Frontend Architecture

**Status: Implemented.** React 19 (Vite), deliberately **plain JavaScript**
(JSDoc type comments in `frontend/src/constants/*.js`, no TypeScript build
step — an early, maintained architectural decision).

```
frontend/src/
├── services/api.js          One function per REST endpoint — the only file
│                             that knows about fetch()/JSON.
├── hooks/
│   ├── useProfileFlow.js     Select user → consent → profile → summary state
│   └── useAbilityOSDemo.js   The session pipeline: start → analyze → detect
│                             → recommend → apply → events → complete/abandon
│                             → feedback
├── components/
│   ├── ErrorBoundary.jsx     App-level crash guard (Phase 8)
│   ├── ConsentGate.jsx       Backend-truth consent fallback
│   ├── JourneyIndicator.jsx  Profile-flow step indicator
│   ├── BarrierCard.jsx       Standalone (Phase 4 demo) barrier display
│   ├── AdaptationDecisionPanel.jsx  Standalone (Phase 5 demo) decision display
│   ├── KioskView.jsx         The real adaptive kiosk (§16)
│   ├── ConfirmDialog.jsx     High-risk adaptation confirmation gate
│   ├── FeedbackForm.jsx      The 3-question feedback screen (§20)
│   ├── OutcomeSummary.jsx    Plain-language post-feedback summary
│   ├── DeveloperPanel.jsx    The full technical decision chain + Judge Mode
│   │                         glance strip (§30)
│   └── MetricsPanel.jsx      Before/after comparison table
├── pages/
│   ├── LandingPage.jsx, SelectUserPage.jsx, ConsentPage.jsx,
│   │   AbilityProfileEditorPage.jsx, ProfileSummaryPage.jsx,
│   │   TaskEnvironmentPage.jsx  The profile + standalone Task/Barrier/
│   │                            Adaptation demo journey
│   ├── DemoPage.jsx          The real kiosk page (wires KioskView +
│   │                         DeveloperPanel + FeedbackForm + OutcomeSummary
│   │                         + MetricsPanel together)
│   └── AnalyticsPage.jsx     The accessibility-outcomes dashboard (§21)
└── App.jsx / main.jsx        Top-level stage router + ErrorBoundary wiring
```

Data flow: `api.js` call → raw JSON → a page's local component state (via
`useState`/the two custom hooks) → passed as props to presentational
components → rendered. There is no global state management library — state is
deliberately kept close to where each page's pipeline actually runs. **The
backend is the source of truth**; the frontend never computes a barrier,
score, or safety decision itself — see [§28](#28-security)'s explicit rule.

## 25. Backend Architecture

**Status: Implemented.** Django 5.2 project (`backend/config/`) with 10
Django apps, each with a narrow, named responsibility:

| App | Responsibility |
|---|---|
| `users` | `User` (custom, extends `AbstractUser`), `ConsentRecord`, JWT login, ownership helper |
| `abilities` | `AbilityProfile`, the controlled vocabulary, profile read/write/clear |
| `tasks` | `Task`, `TaskStep`, the `seed_demo` management command |
| `environments` | `Environment`, the fixture/vision analyzer |
| `barriers` | Both barrier-detection engines (§12) |
| `adaptations` | `Adaptation`, `AdaptationResult`, scoring, both safety validators, the AI-assisted recommender |
| `ai_engine` | The provider-agnostic LLM client, prompts, Pydantic schemas, the session-based decision engine, vision service |
| `feedback` | `InteractionSession`, `InteractionEvent`, `Feedback` |
| `analytics` | All outcome-measurement calculation logic + views |
| `api` | `InteractionOrchestrator` (the one class that calls every other app's services in sequence per stage) + every REST view + the custom exception handler |

Each app follows `models.py` → `serializers.py` → `views.py` (or a service
module under `services/`) — views stay thin; the actual reasoning lives in
service functions, independently unit-testable without an HTTP client.
Permissions: `DEFAULT_PERMISSION_CLASSES = AllowAny` project-wide (a
deliberate, documented hackathon-demo choice — see [§28](#28-security)), with
ownership enforced separately for any request that *does* carry a real
authenticated identity.

## 26. Database Architecture

**Status: Implemented.** SQLite by default (zero setup); PostgreSQL via
`DATABASE_URL` (see [§37](#37-environment-configuration)). Every model below
is a real model in the current codebase — none invented.

| Model | App | Purpose | Key fields |
|---|---|---|---|
| `User` | `users` | Extends Django's `AbstractUser` | `display_name`, `is_demo_profile` |
| `ConsentRecord` | `users` | Consent grant | `user` (FK), `granted`, `scope` (JSON), `granted_at` |
| `AbilityProfile` | `abilities` | The functional profile | `user` (1:1), `label`, `dimensions` (JSON), `preferred_modality`, `preferences` (JSON) |
| `Task` | `tasks` | A task the system understands | `task_id` (slug, unique), `name`, `description`, `time_limit_seconds` |
| `TaskStep` | `tasks` | One ordered step of a task | `task` (FK), `order`, `step_id`, `name`, `controls` (JSON list) |
| `Environment` | `environments` | An interface/device descriptor | `environment_id` (unique), `source` (`fixture`/`vision`), `data` (JSON) |
| `Barrier` | `barriers` | One detected mismatch | `session` (FK), `barrier_type`, `ability_dimension`, `severity`, `confidence`, `evidence` |
| `Adaptation` | `adaptations` | One catalogue entry | `name` (slug, unique), `display_name`, `resolves_barrier_types` (JSON list), `ui_effects` (JSON), `risk_level`, `requires_confirmation`, `allowed_for_tasks` (JSON) |
| `AdaptationResult` | `adaptations` | One scored/validated decision | `session` (FK), `barrier` (FK), `adaptation` (FK), `score`, `score_breakdown` (JSON), `source` (`ai`/`fallback`), `approved`, `requires_confirmation`, `confirmed`, `applied` |
| `InteractionSession` | `feedback` | One task attempt (§18) | `user`/`task`/`environment` (FK), `status`, `baseline_mode`, `assistance_count`, `completed_at`, `ability_profile_snapshot` (JSON) |
| `InteractionEvent` | `feedback` | One structured event (§19) | `session` (FK), `step`, `event_type`, `control_id`, `metadata` (JSON) |
| `Feedback` | `feedback` | One session's feedback (§20) | `session` (1:1), `completed`, `errors`, `ease_rating`, `adaptation_helpfulness`, `optional_comment` |

**There is no separate `TaskControl` model** — controls live as JSON list
entries inside `TaskStep.controls` and `Environment.data.controls`. This is a
deliberate implementation choice (a control is a simple, fixed-shape fact, not
an entity needing its own relational identity), documented here explicitly
because an earlier conceptual outline suggested it as a possible model name.

**Textual ER diagram** (FK direction: `→` reads "belongs to"):

```
User ──1:1── AbilityProfile
User ──1:1── ConsentRecord
User ──1:N── InteractionSession

Task ──1:N── TaskStep
Task ──1:N── InteractionSession

Environment ──1:N── InteractionSession

InteractionSession ──1:N── Barrier
InteractionSession ──1:N── AdaptationResult
InteractionSession ──1:N── InteractionEvent
InteractionSession ──1:1── Feedback

Barrier ──1:N── AdaptationResult
Adaptation ──1:N── AdaptationResult
```

Indexes exist on `InteractionSession.status`, `.baseline_mode`, and
`(task, status)`, and on `InteractionEvent(session, event_type)` — added in
Phase 8 to keep analytics aggregation queries efficient without loading every
event row into application code.

## 27. API Architecture

**Status: Implemented.** Base URL: `http://localhost:4343/api`. Every endpoint
below is real — verified directly against `backend/api/urls.py` while writing
this document (no invented routes).

| Category | Method & path | Purpose |
|---|---|---|
| Foundation | `GET /health/` | Real DB query + AI-config status |
| Auth | `POST /auth/login/` | JWT login (infrastructure present; **not used by the frontend demo flow** — see [§39](#39-demo-mode)) |
| Users | `GET /users/demo/` | List the 3 seeded demo personas |
| Ability Profile | `GET`/`PATCH`/`DELETE /users/{id}/ability-profile/` | Read / edit / clear |
| Consent | `GET`/`POST /users/{id}/consent/` | Read / grant / revoke |
| Tasks | `GET /tasks/`, `POST /tasks/analyze/` | List tasks; standalone Task Understanding |
| Environment | `POST /environment/analyze/` | Dual-mode: `{session_id}` or standalone `{environment_id}` |
| Interactions | `POST /interactions/start/` | Begin a session |
| Barriers | `POST /barriers/detect/` | Dual-mode: `{session_id}` or standalone `{user_id, task_id, environment_id}` |
| Adaptations | `GET /adaptations/candidates/?barrier_type=...`, `POST /adaptations/recommend/` (dual-mode) | Candidate listing; scoring + AI + safety |
| Interactions | `POST /interactions/{id}/apply/` | Apply the approved adaptation(s) |
| Interactions | `POST /interactions/{id}/events/` | Batched step-level events (§19) |
| Interactions | `POST /interactions/{id}/complete/`, `POST /interactions/{id}/abandon/` | Explicit terminal transitions (§18) |
| Interactions | `POST /interactions/{id}/feedback/` | The 3-question feedback (§20) |
| Interactions | `GET /interactions/{id}/summary/` | Full developer-panel payload |
| Analytics | `GET /analytics/before-after/`, `/dashboard/`, `/adaptations/`, `/barriers/`, `/sessions/` | §21 |

**Authentication/authorization:** every endpoint is reachable anonymously by
design (documented hackathon-demo choice). Any request that *does* carry a
real authenticated identity is held to real ownership rules — see
[§28](#28-security). **Rate limiting:** `auth_login` (10/min), `session_start`
(30/min), `adaptation_recommend` (30/min) — every other endpoint is
unthrottled. **Error shape:** any unhandled server error returns
`{"detail": "..."}` with HTTP 500; the message is the real exception text only
when `DEBUG=true`, else a generic message (the real detail goes to the server
log instead — see [§28](#28-security)). Orchestrator-raised conflicts (e.g. an
invalid session-state transition) return HTTP 409 with `{"detail": "..."}`.

## 28. AI Workflow

See [§13](#13-ai-decision-engine) for the full narrative explanation; this
section is the condensed step sequence with actual file references:

```
1. Barriers already detected (barriers/services/detection.py)
        ↓
2. adaptations/services/scoring.py — every enabled, barrier-matching
   adaptation scored (always runs)
        ↓
3. ai_engine/services/decision_engine.py::decide() —
   is an AI provider configured (settings.AI_AVAILABLE)?
        ├─ No  → deterministic top-scored candidate
        └─ Yes → ai_engine/services/llm_client.py::call()
                     ↓
                 Pydantic-validated against ai_engine/services/schemas.py
                     ├─ invalid / unknown id / malformed → deterministic fallback
                     └─ valid → the AI's selected candidate (source="ai")
        ↓
4. adaptations/services/rules.py::validate_adaptation() (or the standalone
   9-rule validator) — independent, re-checks everything
        ├─ rejected → try the next-best deterministic candidate
        └─ approved → returned as the ApprovedAdaptation
        ↓
5. Frontend applies it — never calls the AI directly
```

## 29. Data Flow

```
User            →  AbilityProfile        (create/read, §8)
AbilityProfile  →  InteractionSession    (a snapshot is taken at session start, §18)
InteractionSession → Task, Environment   (FK attachment)
Task + Environment + AbilityProfile → Barriers      (§11)
Barriers        →  Candidate Adaptations (§12)
Candidates      →  AI Decision           (optional, §13)
AI Decision     →  Safety Validation     (§14)
Approved Adaptation → Adaptive UI        (§16)
Adaptive UI     →  Interaction Events    (§19)
Interaction Events → Outcome             (completion, errors, assistance — §18)
Outcome         →  Feedback              (§20)
Feedback        →  Analytics             (§21)
Analytics       →  Learning Signal       (§22, computed on demand, never a second stored copy)
```

## 30. Security

**Status: Implemented; scoped appropriately for a hackathon demo, not a
production deployment — see [§42](#42-limitations).**

- **Ownership**: `backend/users/services/ownership.py::assert_owner()` — a
  single, shared implementation (previously duplicated per-app; extended in
  Phase 8 to cover every session/feedback/event endpoint, which previously had
  none at all). Any request carrying a real authenticated identity may only
  touch its own ability profile, consent, or session data (403 otherwise);
  staff may touch any. Purely anonymous requests (the demo path) are
  completely unaffected.
- **AI cannot bypass safety validation**: see [§13](#13-ai-decision-engine)/[§14](#14-safety-validation)
  — every AI-selected adaptation passes through the same independent validator
  a deterministic choice does, with no code path that skips it.
- **Input validation**: ability-profile dimension values, feedback
  `ease_rating`/`adaptation_helpfulness`, and interaction-event `event_type`
  are all checked against a controlled vocabulary server-side — an invalid
  value is a 400, never silently coerced or stored.
- **AI output validation**: see [§13](#13-ai-decision-engine) — schema
  validation, candidate-pool membership checks, malformed-JSON handling.
- **Secrets**: `SECRET_KEY`, `AI_API_KEY`, `DATABASE_URL` are all
  environment-configured (`backend/.env`, gitignored); only placeholder
  `.env.example` files are committed (verified — see [§37](#37-environment-configuration)).
- **CORS**: configured via `CORS_ALLOWED_ORIGINS` (default
  `http://localhost:3434`).
- **Rate limiting**: see [§27](#27-api-architecture) — lightweight, IP-based,
  three endpoints.
- **Error responses**: never leak raw exception text outside `DEBUG` mode
  (`api/exceptions.py`); every unexpected error is logged server-side.
- **No raw SQL** beyond a single parameterless health-check query; no
  `dangerouslySetInnerHTML` anywhere in the frontend (verified via repository
  search).

## 31. Privacy

- The Ability Profile is **functional and non-diagnostic** by construction —
  it has no field for a medical condition, diagnosis, or history (see
  [§8](#8-ability-profile)'s full dimension table).
- Consent is required and checked before any barrier detection or adaptation
  recommendation runs (§9).
- Voice features are one-shot, on-demand text-to-speech only — **no audio is
  ever recorded or stored**; there is no speech-recognition/microphone-capture
  code anywhere in this repository (verified).
- No camera/video capture in the demo path; the optional vision-analysis
  service processes a submitted screenshot only, and is off by default.
- `InteractionEvent.metadata` is capped (10 keys / 200 chars per value) and
  restricted to structured, task-relevant facts — never raw input.
- `Feedback.optional_comment` is capped at 500 characters, stored only against
  the session, never exposed publicly, and never used for AI training (there
  is no AI training pipeline in this project).
- The Learning Signal never automatically edits a person's profile (§22).
- **Remaining limitation**: every endpoint is reachable anonymously by design
  (documented hackathon-demo choice) — this is not a production-grade privacy
  boundary; see [§42](#42-limitations).

## 32. Accessibility

**Status: Implemented for the application itself**, verified via a Phase 8
audit (`docs/PHASE_8.md`), not just claimed:

- Semantic HTML and a correct heading hierarchy on every page (one `<h1>` per
  top-level page, nested `<h2>`/`<h3>` beneath it — a gap on the kiosk and
  analytics pages was found and fixed in Phase 8).
- `role="status"`/`aria-live` announcements for kiosk state changes;
  `aria-pressed` on toggle buttons; `role="radiogroup"` on the feedback form's
  question groups.
- No color-only indicators — every status "pill" and outcome badge carries
  text (and often an icon), never color alone.
- Visible focus states via the shared global stylesheet.
- A skip-to-content link (`App.jsx`).
- Large, clearly-bounded touch targets once an adaptation is applied
  (`button_scale`); the kiosk's own miss-simulation exists specifically to
  make an *unaddressed* small-target barrier visibly, tangibly harder to use.
- Responsive layout (tested down to a ~400px-wide viewport per the artifact
  design conventions used elsewhere in this project's tooling; the kiosk and
  analytics grids collapse to a single column on narrow screens).
- Captions (`banner_alert`) as the visual equivalent of an audio-only alert.

## 33. Error Handling and Fallbacks

Every fallback below is real, implemented code, not aspirational:

| Condition | Fallback |
|---|---|
| AI unavailable / invalid response | Deterministic Adaptation Engine scoring (§13) |
| No adaptation passes safety validation | Standard (unadapted) kiosk interface |
| An applied adaptation's `ui_effects` includes an unrecognized key | `KioskView` ignores it by construction — no crash, no special-case check needed |
| Voice (Web Speech) API unavailable | Silent no-op; touch interaction continues normally |
| Haptic (Vibration) API unavailable | Silent no-op; visual confirmation still occurs |
| Environment vision analysis fails/unavailable | Falls back to the JSON fixture environment |
| Backend unavailable | `frontend/src/services/api.js` raises a typed `ApiError` with a clear message; pages show it, never a blank screen |
| A React component throws | `ErrorBoundary` (Phase 8) shows "Something went wrong." + "Return to AbilityOS," never a blank page |
| Unexpected backend exception | Logged server-side; client sees a generic message outside `DEBUG` (§30) |
| Invalid/duplicate session-state transition | Rejected with HTTP 409, never silently allowed |

## 34. Technology Stack

| Layer | Technology | Status |
|---|---|---|
| Backend framework | Django 5.2.17 | **Used** |
| API framework | Django REST Framework 3.18.1 | **Used** |
| Auth | `djangorestframework-simplejwt` 5.5.1 | **Used** (infrastructure; login endpoint exists but the frontend demo flow doesn't call it — see §39) |
| CORS | `django-cors-headers` 4.9.0 | **Used** |
| Config | `python-dotenv` 1.2.3, `dj-database-url` 3.1.2 | **Used** |
| AI schema validation | `pydantic` 2.13.5 | **Used** |
| Database (prod-intended) | PostgreSQL, via `psycopg2-binary` 2.9.10 | **Used when `DATABASE_URL` is set** |
| Database (dev/demo default) | SQLite (Django built-in) | **Used** |
| AI provider SDKs | `openai`, `anthropic` | **Optional** — commented out in `requirements.txt`; install only if using live AI |
| Computer vision | `opencv-python-headless`, `pytesseract` | **Optional** — commented out; `VISION_ENABLED=false` by default |
| Frontend framework | React 19.2.8 | **Used** |
| Build tool | Vite 8.3.0 | **Used** |
| Frontend language | Plain JavaScript (JSDoc types) | **Used** — deliberately not TypeScript |
| Frontend lint | `oxlint` 1.81.0 | **Used** |
| Frontend test/verification | Playwright (ad hoc, not a repo-committed test suite) | **Used for verification, not CI** |
| Redis + Celery | — | **Not used** — no async task queue in this project |
| Docker | — | **Not used** — deliberately not added (see `docs/PHASE_8.md`); manual setup is the supported path |
| Nginx / Gunicorn | — | **Not configured in this repo** — Planned/Future (standard Django deployment components, not wired up here) |

## 35. Repository Structure

Verified directly against the filesystem (noise directories — `node_modules`,
`venv`, `__pycache__`, `.git`, build output — omitted):

```
AbilityOS/
├── README.md
├── details.md                    ← this file
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── db.sqlite3                 (dev SQLite file, gitignored)
│   ├── config/                    settings.py, urls.py, wsgi.py, asgi.py
│   ├── users/                     User, ConsentRecord, JWT login, ownership
│   ├── abilities/                 AbilityProfile, constants, profile_service
│   ├── tasks/                     Task, TaskStep, seed_demo command
│   ├── environments/              Environment, analyzer, vision_service
│   ├── barriers/                  Barrier, both detection engines
│   ├── adaptations/                Adaptation, AdaptationResult, scoring,
│   │                               both safety validators, recommender
│   ├── ai_engine/                 llm_client, decision_engine, schemas,
│   │                               prompts, vision_service
│   ├── feedback/                  InteractionSession, InteractionEvent,
│   │                               Feedback
│   ├── analytics/                 services.py, config.py, views.py
│   ├── api/                       orchestrator.py, urls.py, views.py,
│   │                               exceptions.py
│   └── fixtures/                  kiosk_standard.json
├── frontend/
│   ├── package.json, vite.config.js, index.html, .oxlintrc.json
│   ├── .env.example
│   └── src/                       components/, pages/, hooks/, services/,
│                                   constants/, styles/, App.jsx, main.jsx
└── docs/
    ├── SETUP.md, DATABASE.md, ABILITY_PROFILE.md, AI_DECISION_ENGINE.md
    ├── ARCHITECTURE.md, API.md, DEMO_GUIDE.md, PHASES.md
    └── PHASE_3.md … PHASE_8.md    (per-phase implementation reports)
```

There is no `tests/` directory at the repository root — tests live alongside
the code they cover, Django-convention style (`<app>/tests.py`, plus a few
`<app>/test_<topic>.py` files where a phase's scope warranted a separate file).

## 36. Phase-by-Phase Implementation

*(Condensed here; the authoritative per-phase detail lives in `docs/PHASE_3.md`
through `docs/PHASE_8.md` and `docs/PHASES.md`.)*

### Phase 1 — Foundation & Architecture
**Objective:** stand up the Django/DRF backend, React/Vite frontend, and the
initial database schema. **Status:** Implemented. **Key files:**
`backend/config/`, `backend/manage.py`, `frontend/vite.config.js`,
`GET /api/health/`.

### Phase 2 — User, Consent & Ability Profile
**Objective:** the functional Ability Profile, consent gating, three demo
personas. **Inputs:** none (person-entered). **Outputs:** a validated
`AbilityProfile` + `ConsentRecord`. **Status:** Implemented. **Key files:**
`backend/abilities/`, `backend/users/`. **APIs:**
`/users/{id}/ability-profile/`, `/users/{id}/consent/`.

### Phase 3 — Task & Environment Understanding
**Objective:** deterministic `task_id`/`environment_id` → descriptor lookups,
facts only. **Status:** Implemented (one seeded task/environment fixture).
**Key files:** `backend/tasks/`, `backend/environments/`. **APIs:**
`/tasks/analyze/`, `/environment/analyze/`.

### Phase 4 — Barrier Detection
**Objective:** deterministic mismatch detection, five barrier types.
**Inputs:** Ability Profile + Task Descriptor + Environment Descriptor.
**Outputs:** a list of detected barriers with severity/confidence/evidence.
**Status:** Implemented. **Key files:** `backend/barriers/`. **API:**
`/barriers/detect/`.

### Phase 5 — Adaptation Engine + AI Decision Engine + Safety Validation
**Objective:** score candidates, optionally rank via AI, independently
validate. **Status:** Implemented. **Key files:** `backend/adaptations/`,
`backend/ai_engine/`. **API:** `/adaptations/recommend/`,
`/adaptations/candidates/`.

### Phase 6 — Adaptive Kiosk Experience
**Objective:** the approved adaptation actually changes the interface.
**Status:** Implemented. **Key files:**
`frontend/src/components/KioskView.jsx`, `frontend/src/pages/DemoPage.jsx`.
**API:** `/interactions/{id}/apply/`.

### Phase 7 — Feedback, Interaction Analytics & Learning Signal
**Objective:** outcome measurement — sessions, events, feedback, analytics, a
non-mutating learning signal. **Status:** Implemented (including the removal
of an earlier automatic profile-confidence mutation found to conflict with
this phase's own "never auto-change the profile" requirement — see
`docs/PHASE_7.md` §3). **Key files:** `backend/feedback/`,
`backend/analytics/`. **APIs:** `/interactions/{id}/events/`, `/complete/`,
`/abandon/`, `/feedback/`, `/analytics/*`.

### Phase 8 — Final Integration, Hardening, Deployment Readiness & Polish
**Objective:** no new feature — an audit-then-fix pass making Phases 1–7 work
as one reliable product. **Status:** Implemented. Found and fixed: a real data
bug (duplicate Analytics rows from a Django `.distinct()`/default-ordering
interaction — see `docs/PHASE_8.md`), a missing ownership check on every
session/feedback endpoint, dead/missing logging configuration, a leaky
exception handler, a missing frontend error boundary, a heading-hierarchy gap,
and stale documentation. **Key files:**
`backend/users/services/ownership.py`, `backend/analytics/services.py`,
`frontend/src/components/ErrorBoundary.jsx`, `docs/PHASE_8.md`.

## 37. Current MVP

**Primary demo scenario: the public ticket kiosk.**

```
User (one of 3 seeded personas)
  → Ability Profile (pre-filled, editable)
  → Task: "Buy a ticket" (purchase_ticket)
  → Environment: kiosk_standard (JSON fixture)
  → Barrier detected (deterministic)
  → Adaptation selected (scored, optionally AI-ranked)
  → Safety-validated
  → Adaptive Kiosk (the interface actually changes)
  → Task completion (or abandonment)
  → Feedback (3 questions)
  → Outcome (recorded, server-authoritative)
  → Analytics (real aggregation)
```

**The three seeded demo profiles** (`python manage.py seed_demo`), functional
accessibility profiles, not diagnoses:

| Username | Label | Notable dimensions | Barrier this triggers | Adaptation this selects |
|---|---|---|---|---|
| `demo_low_vision_dexterity` | Low Vision + Reduced Dexterity | `vision: large-text-needed`, `dexterity: reduced-precision` | `small_tap_targets`, `low_contrast` | `increase_target_size`, `increase_contrast` |
| `demo_hearing_difficulty` | Hearing Difficulty | `hearing: relies-on-visual`, `preferred_modality: mixed` | `audio_only_alert` | `caption_audio` |
| `demo_cognitive_load` | Cognitive Load | `cognition: needs-step-by-step`, `fatigue: moderate` | `too_many_choices`, `fatigue_degraded_precision` | `step_by_step_flow`, `increase_target_size` |

All three verified live (Playwright, headless Chromium) end-to-end through the
complete flow above as part of Phase 8's final verification pass — see
`docs/PHASE_8.md`.

**Not claimed:** broader real-world device/kiosk integration, multiple tasks
beyond `purchase_ticket`, or live camera-based environment sensing in the demo
path — see [§44](#44-future-scope).

## 38. Running the Project

**Prerequisites:** Python 3.11+, Node.js 20.19+ or 22.12+ (Vite 8's minimum —
verified against `frontend/node_modules/vite/package.json`'s `engines`
field), no database server required for the default SQLite path.

**Backend:**
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate      macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 4343
```

**Sanity check:**
```bash
curl http://localhost:4343/api/health/
```

**Frontend** (second terminal):
```bash
cd frontend
npm install
npm run dev -- --port 3434
```

Open `http://localhost:3434`. The frontend talks to the backend at
`http://localhost:4343/api` by default (`frontend/.env.local`, or the
`VITE_API_BASE_URL` fallback in `frontend/src/services/api.js`).

**Production frontend build:**
```bash
cd frontend && npm run build
```

**Backend checks:**
```bash
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
```

**Tests:** see [§40](#40-testing).

## 39. Environment Configuration

**Backend** (`backend/.env.example` — copy to `backend/.env`; every variable
has a safe default if omitted):

| Variable | Purpose | Required? | Example placeholder |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Django's cryptographic secret | No (has an insecure dev default) | `change-me-to-a-random-string-for-any-shared-deployment` |
| `DEBUG` | Django debug mode | No (defaults `true`) | `true` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | No | `localhost,127.0.0.1` |
| `DATABASE_URL` | PostgreSQL connection string | No (falls back to SQLite) | `postgres://abilityos:abilityos@localhost:5432/abilityos` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed frontend origins | No | `http://localhost:3434,http://127.0.0.1:3434` |
| `CORS_ALLOW_ALL_ORIGINS` | Allow any CORS origin | No (defaults to `DEBUG`'s value) | `false` |
| `AI_PROVIDER` | `openai` / `anthropic` / `none` | No (defaults `none`) | `none` |
| `AI_API_KEY` | The AI provider's API key | No | `your_api_key_here` |
| `AI_MODEL` | Model name for the configured provider | No | `gpt-4o-mini` |
| `VISION_ENABLED` | Enable the optional OpenCV/OCR environment path | No (defaults `false`) | `false` |

**Frontend** (`frontend/.env.example` — copy to `frontend/.env.local`):

| Variable | Purpose | Required? | Example placeholder |
|---|---|---|---|
| `VITE_API_BASE_URL` | Backend API base URL | No (defaults `http://localhost:4343/api`) | `http://localhost:4343/api` |

No real secret values appear anywhere in this document or in either
`.env.example` file (verified while writing this section).

## 40. Database Setup

```bash
cd backend
python manage.py migrate        # applies every migration, clean-database safe
python manage.py seed_demo      # idempotent — safe to re-run
```

`seed_demo` (`backend/tasks/management/commands/seed_demo.py`) is idempotent
for the task/environment/adaptation catalogue/demo-profile rows (uses
`update_or_create`); the small set of illustrative seed *sessions* (labeled
`is_seed=True`) are only created once — re-running the command after they
already exist skips that step rather than duplicating them. `python manage.py
makemigrations --check --dry-run` reports "No changes detected" against the
current codebase (verified). No destructive automatic reset exists anywhere
in this project — see [§42](#42-limitations) for the frontend's "Reset Demo"
button, which only clears local UI state, never database rows.

## 41. Demo Mode

- **Demo users**: the three personas in [§37](#37-current-mvp)'s table,
  password `demo-password` for all three (only relevant if you use the
  otherwise-unused `/api/auth/login/` endpoint directly — the demo UI flow
  selects a persona without a password).
- **Demo task**: `purchase_ticket`. **Demo environment**: `kiosk_standard`.
- **Resetting demo state**: the header's "Reset Demo" button
  (`frontend/src/App.jsx`) clears the current browser session's local
  journey state and reloads the demo-user selector — it does **not** touch
  any backend data, demo or real.
- **Demo data labeling**: `InteractionSession.is_seed` marks the small set of
  illustrative example sessions `seed_demo` creates; the Analytics "Recent
  sessions" table surfaces this explicitly (a "demo data" label per row), and
  every analytics response's `note` field states plainly that its numbers are
  "prototype demonstration metrics... not a production research result."
- **Expected results**: see [§37](#37-current-mvp)'s table — each persona
  reliably triggers a specific, different barrier and adaptation; verified
  live end-to-end for all three in Phase 8.

## 42. Testing

**Backend** — Django's built-in test runner (`unittest`-based):
```bash
cd backend
python manage.py test
```
**245 tests, all passing** as of Phase 8 (verified by running the suite while
writing this document). Coverage spans: Ability Profile validation, task/
environment understanding, barrier detection for every barrier type,
adaptation scoring/ranking, both safety validators, AI response validation and
fallback behavior (mocked LLM calls — no test depends on a real external
call), the adaptive kiosk's safe-rendering contract, session lifecycle/state
transitions, interaction events, feedback validation, outcome score/learning
signal calculation, analytics aggregation (including a regression test for
the Phase 8 `.distinct()` bug), and ownership/authorization.

**Frontend** — no Jest/Vitest unit-test harness is configured in this
repository (verified: `frontend/package.json` has no test script or test
dependency). Frontend correctness is verified via:
```bash
cd frontend
npm run build     # production build
npx oxlint src     # lint
```
plus ad hoc Playwright (headless Chromium) scripts run during development to
walk the live application end-to-end — these scripts are not committed to the
repository as a CI suite; they were used interactively for verification during
each phase (see each `docs/PHASE_*.md` for what was verified when).

**Integration/end-to-end**: the backend test suite's `api/tests.py` includes
full-stack tests that exercise the real REST API sequence (start → analyze →
detect → recommend → apply → events → complete → feedback → summary) via
Django's test client — the closest thing to a committed end-to-end test in
this repository.

## 43. Deployment

**Backend deployment readiness (implemented):** `DEBUG`, `SECRET_KEY`,
`ALLOWED_HOSTS`, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS` are all
environment-configurable with safe defaults (no code change needed to deploy
differently). Static files use Django's standard `STATIC_URL` configuration.
`python manage.py check` passes clean.

**Frontend deployment readiness (implemented):** the API base URL is
configurable (`VITE_API_BASE_URL`); `npm run build` produces a static,
deployable `dist/` bundle with no hard-coded `localhost` dependency in
production code (only in documented local-dev defaults).

**Not implemented / not present in this repository:** a `Dockerfile` or
`docker-compose.yml` (a deliberate Phase 8 decision, not an oversight — the
existing manual setup is already fast and simple for a project this size,
see `docs/PHASE_8.md`); Nginx/Gunicorn configuration; a CI/CD pipeline; a
production WSGI/ASGI deployment script beyond Django's own `manage.py
runserver` (development-only) and `config/wsgi.py`/`asgi.py` (present,
standard Django scaffolding, ready for a production WSGI server to point at,
but not wired to one in this repository).

## 44. Limitations

Documented plainly, matching README.md's own "Limitations" section:

- One seeded task (`purchase_ticket`) and one primary environment fixture; the
  barrier/adaptation catalogues cover 5 barrier types and 12 adaptations, not
  every possible accessibility need.
- Computer-vision environment analysis is implemented but optional and off by
  default — the JSON-fixture path is what the demo relies on.
- The kiosk's "struggle simulation" (missed taps on undersized controls) is a
  reasonable approximation of a dexterity barrier, not a clinically validated
  motor-impairment model.
- No real user account system, multi-device profile sync, or on-device
  learning.
- JWT login infrastructure exists but isn't consumed by the frontend demo
  flow, which selects a persona directly; no token-refresh flow exists since
  nothing currently calls the login endpoint.
- No Docker setup (deliberate — see [§43](#43-deployment)).
- Lightweight, not abuse-hardened rate limiting (three endpoints only).
- Outcome-score and adaptation-effectiveness thresholds
  (`analytics/config.py`) are reasonable, documented, hackathon-scope
  defaults — not empirically tuned against real accessibility research.
- The Learning Signal (§22) is structured evidence only — nothing in this
  repository currently consumes it to improve future recommendations; that
  loop is explicitly Future Scope (§45).
- `alternative_voice_input`'s effect key exists in the catalogue with no
  corresponding speech-recognition implementation (documented safe
  degradation, not a hidden gap).

## 45. Impact and Benefits

Framed as intended/potential benefit — this is a hackathon prototype, not a
population-level study, and no measured real-world outcome data exists in this
repository:

1. **Greater independence** — the prototype demonstrates a person completing
   the same task with a targeted adaptation rather than needing staff
   assistance, measured per-session (§20/§22).
2. **Reduced manual accessibility (re)configuration** — the adaptation is
   selected per task/environment automatically, rather than requiring a
   person or caregiver to hunt through settings.
3. **Reduced caregiver configuration burden** — a functional profile set once
   can apply across tasks, rather than being reconfigured per app.
4. **Potentially less staff assistance needed at public kiosks** — the
   `assistance_requested`/`assistance_count` metrics exist specifically to
   make this measurable, not just assumed (§19/§21).
5. **A reusable accessibility reasoning layer** — the barrier/adaptation/
   safety-validation pipeline is decoupled from any one specific kiosk UI,
   intended to be a pattern other interfaces could adopt.
6. **Better personalization without over-adapting** — the smallest-
   intervention scoring (§3) avoids adding unnecessary interaction cost.
7. **Support for both permanent and temporary functional limitations** — the
   `fatigue` dimension explicitly models a temporary, session-scoped
   reduction in precision, not only fixed traits.
8. **Potential applicability beyond this one kiosk** — public services,
   healthcare terminals, transportation interfaces, and other kiosk-like
   digital services share the same underlying person+task+environment
   structure, though no such integration exists in this repository today.

## 46. Future Scope

Explicitly **not implemented** — recorded as intentionally deferred, matching
README.md's own "Future roadmap":

1. A learning loop that actually consumes the Learning Signal to improve
   future recommendations (§22 generates the signal; nothing yet reads it
   back).
2. Real-time, camera-based environment understanding (the fixture path is the
   demo default; the vision service analyzes a submitted screenshot, not a
   live feed).
3. OS-level accessibility integration (Android/iOS accessibility services,
   Windows/desktop integration).
4. Smart home / IoT environment integration.
5. Public kiosk hardware integration (real-world terminals, not a browser
   simulation).
6. Healthcare terminal deployments.
7. Transportation interface deployments.
8. Wearable device signals.
9. AR glasses integration.
10. Robotics integration.
11. Cross-device Ability Profile (the same profile following a person between
    devices).
12. Edge AI / on-device inference.
13. Privacy-preserving on-device inference specifically (as distinct from
    edge AI generally).
14. Long-term, multi-session personalized adaptation learning beyond the
    single-session Learning Signal.
15. A developer SDK for third-party applications to consume AbilityOS
    decisions.
16. A public API product (today's API is designed for this project's own
    frontend, not third-party consumption).
17. A certified adaptive-application ecosystem.
18. Production authentication (a real login UI, token refresh, per-deployment
    account management) and infrastructure hardening beyond what's described
    in [§30](#30-security)/[§43](#43-deployment).

## 47. Research Opportunities

Framed as open questions — **not claimed to be solved by this prototype**:

- Can functional ability be estimated reliably from interaction signals alone
  (taps missed, time taken, retries), rather than only self-report?
- Can an AI decision layer reliably select the *minimum* effective
  intervention across a much larger adaptation catalogue than today's 12
  entries, without a human-curated cost/risk value for every candidate?
- Do adaptations selected for one task/environment transfer usefully to a
  different one, or does each context need independent evidence?
- Does a system like this measurably reduce caregiver-dependence over time,
  and how would that be validated outside a hackathon demo?
- What does meaningful, revocable, per-task **dynamic consent** look like in
  practice (today's consent is a single grant/revoke toggle, not scoped
  per-task)?
- How should long-term adaptation learning be validated for safety before any
  automatic profile or recommendation change is trusted — what evidence
  threshold would be enough?

## 48. PPT-Ready Project Summary

### Abstract

AbilityOS is a reasoning layer that sits between a person and the technology
they use. Standard interfaces assume an average user; AbilityOS instead
reasons over a consented, **functional** Ability Profile together with the
task someone is trying to complete and the environment they're in, to detect
the specific mismatch preventing comfortable interaction — for example,
touch targets too small for a person's dexterity level. It evaluates
candidate interventions with a deterministic scoring formula, optionally
layers constrained AI reasoning on top (the AI may only rank pre-approved
candidates, never invent one), and independently validates whatever is chosen
with a rule-based safety layer before anything reaches the interface. The
approved adaptation is then actually applied to a live, working kiosk — not a
mockup — and the outcome is measured: did the person complete the task, did
they need assistance, how easy did they find it. This is a novel combination
of functional profiling, barrier detection, hybrid AI/deterministic decision-
making, and outcome measurement in one working prototype, built for the
"One Small Change" challenge.

### Proposed Solution

**ABILITYOS** — a dynamic accessibility reasoning layer that:

1. Understands the person's functional abilities
2. Understands the task
3. Understands the environment
4. Detects the specific barrier
5. Evaluates candidate interventions
6. Uses constrained AI reasoning (optional, never authoritative)
7. Validates the decision with deterministic safety rules
8. Applies the smallest useful adaptation
9. Measures the outcome

**"Same person. Same task. Same environment. One targeted change."**

### Tech Stack

| Layer | Technology | Status |
|---|---|---|
| Frontend | React 19 (Vite) | Used |
| Backend | Django 5.2 | Used |
| API | Django REST Framework | Used |
| Database | SQLite (dev/demo) / PostgreSQL (prod-ready) | Used |
| AI | OpenAI / Anthropic (provider-agnostic client) | Optional |
| Computer Vision | OpenCV + OCR | Optional |
| Auth | JWT (`djangorestframework-simplejwt`) | Present, not exercised by the demo UI |
| Deployment | Environment-configurable Django + static frontend build | Ready; Docker/Nginx/Gunicorn not included |

### Technical Approach

1. **Functional Ability Profile** — nine non-diagnostic dimensions, consented.
2. **Task Understanding** — what is the person trying to do (facts only).
3. **Environment Understanding** — what does the interface actually look like
   right now (fixture-based in this MVP).
4. **Barrier Detection** — deterministic threshold comparison across all
   three.
5. **Candidate Adaptation Generation** — every catalogue entry that resolves
   the detected barrier type.
6. **Deterministic Scoring** — `Benefit + Relevance + Preference + Confidence
   − Cost − Risk`.
7. **AI Ranking** — optional; constrained to the same scored candidate pool.
8. **Safety Validation** — independent re-check; AI can propose, never
   directly decide.
9. **Adaptive UI** — the kiosk actually changes.
10. **Interaction Measurement** — structured events, server-authoritative
    timing.
11. **Feedback** — a short, three-question subjective screen.
12. **Learning Signal** — structured, non-mutating evidence for future work.

### Architecture Diagram (Mermaid)

```mermaid
flowchart TD
    USER([USER])
    FE[React Frontend]
    API[Django REST API]
    CORE[AbilityOS Core]
    PROFILE[Ability Profile]
    TASKU[Task Understanding]
    ENVU[Environment Understanding]
    BARRIER[Barrier Detection]
    ADAPT[Adaptation Engine]
    AI[AI Decision Engine]
    SAFETY[Safety Validation]
    KIOSK[Adaptive Kiosk]
    OUTCOME([USER OUTCOME])
    FEEDBACK[Feedback + Analytics]
    LEARN[Learning Signal]
    DB[(PostgreSQL / SQLite)]
    LLM[(External LLM Provider)]

    USER --> FE --> API --> CORE
    CORE --> PROFILE
    CORE --> TASKU
    CORE --> ENVU
    CORE --> BARRIER
    CORE --> ADAPT
    CORE --> AI
    CORE --> SAFETY
    AI -.optional call.-> LLM
    CORE --> KIOSK --> OUTCOME --> FEEDBACK --> LEARN
    CORE --> DB
    FEEDBACK --> DB
```

### Impact & Benefits

*(Intended/prototype-demonstrated benefits — not proven population-level
outcomes.)*

- Improves independent task interaction
- Reduces manual accessibility (re)configuration
- Supports both permanent and temporary functional limitations
- Can reduce unnecessary caregiver intervention
- Provides reusable accessibility reasoning logic
- Applicable to public-service kiosks and digital services generally
- Measures whether an adaptation actually helped, not just whether the UI
  changed
- A foundation for further personalized-accessibility work

### Future Scope

- OS-level accessibility integration
- Cross-device Ability Profile
- Smart home / IoT integration
- Wearables and AR glasses
- Edge AI
- Privacy-preserving on-device inference
- Long-term personalized adaptation learning
- Developer SDK / public API
- Healthcare and public-service deployments
- A broader adaptive-device ecosystem

---

## Important Developer Rules

For anyone extending this codebase:

1. Do not treat AbilityOS as a medical diagnosis system — the Ability Profile
   is functional, never diagnostic.
2. Do not invent user abilities — every dimension value must come from the
   controlled vocabulary in `abilities/constants.py`.
3. Do not invent barriers — a barrier is only ever produced by a deterministic
   rule in `barriers/services/`.
4. Do not invent adaptations — the catalogue in `Adaptation` is fixed and
   pre-approved; nothing, including the AI, may select outside it.
5. AI may only choose from approved, pre-scored candidates — never propose
   its own.
6. Safety validation must remain independent of the LLM — never let an AI
   response skip `adaptations/services/rules.py` (or the standalone
   `validator.py`).
7. The backend remains the source of truth for every piece of business data —
   users, profiles, consent, tasks, environments, barriers, decisions,
   sessions, outcomes, feedback, analytics.
8. The frontend must not duplicate business rules — it renders what the
   backend already decided, and reads only a fixed, documented set of
   `ui_effects` keys (§16).
9. Do not fabricate analytics — every number must originate from a real
   database record, or be explicitly labeled as demo/seed data.
10. Do not fabricate research results — use "observed," "prototype
    demonstrates," "intended benefit," never "proven" or "scientifically
    validated," in any documentation.
11. Do not store unnecessary personal data — no raw audio, no continuous
    video, no unrelated activity capture (§31).
12. Do not introduce surveillance features without explicit scope and
    consent review.
13. Preserve phase boundaries unless intentionally extending the
    architecture — each phase's own `docs/PHASE_*.md` documents exactly what
    that phase added and why.
14. Maintain deterministic fallbacks for every optional dependency (AI,
    vision, voice, haptics) — the system must always work with none of them
    configured.
15. Prefer the smallest effective intervention — do not "upgrade" a working
    barrier fix to a more powerful adaptation without a scoring-formula
    reason to.

## Final Project Summary

AbilityOS turns accessibility from a static collection of settings into a
decision-making layer. It understands **PERSON**, **TASK**, and
**ENVIRONMENT** together; finds the **BARRIER**; selects the **SMALLEST
USEFUL INTERVENTION**; applies the **ADAPTATION**; and measures the
**OUTCOME**.

> **"Don't adapt the person to the technology. Adapt the technology to the
> person."**
