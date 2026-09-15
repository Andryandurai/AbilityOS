# Phase 5 — Adaptation Engine + AI Decision Engine + Safety Validation

## Purpose

Phase 5 answers exactly one question:

> "What is the smallest approved intervention that resolves the detected
> barrier(s)?"

It never decides how that intervention actually gets rendered — no button
resizes, no CSS changes, no kiosk state changes anywhere in this phase's
code. The output is a data object (`ApprovedAdaptation`), consumed by a
later phase.

> **AI does not control the interface directly.** The LLM can only select
> from pre-approved adaptations. The rule engine independently validates
> the AI selection before anything is called "approved."

## Architecture

```
List[Barrier]  (Phase 4, in-memory, no DB coupling)
      │
      ▼
adaptations.services.scoring.rank_candidates_for_barrier()   <- REUSED UNCHANGED
      │  (per barrier: candidate adaptations + deterministic scores)
      ▼
AdaptationRecommender._decide()
      │
      ├── llm_client not configured  ──────────────► deterministic top score
      │
      └── llm_client configured ──► RECOMMENDER_SYSTEM_PROMPT + candidate pool
                 │
                 ▼
          AdaptationRecommendationResponse (Pydantic-validated)
                 │
        valid? ──┴── invalid/unknown-id/malformed ──► deterministic top score
        │
        ▼
   selected_adaptation_id
      │
      ▼
AdaptationSafetyValidator.validate()  (independent, re-checks everything)
      │
  rejected ──► try next-best deterministic candidate ──► (repeat)
      │
  approved
      │
      ▼
ApprovedAdaptation  { adaptation_id, score, reason, source, validated }
```

## A genuine, load-bearing discovery, not an assumption

`adaptations/services/scoring.py` (built in an earlier pass, already
powering the real kiosk demo) only ever accesses `barrier.barrier_type`,
`.severity`, `.confidence` via attribute lookup — it works **completely
unmodified** on Phase 4's `BarrierResult` dataclass. Same for
`ai_engine/services/fallback.py::decide_fallback()`. This phase reuses both
exactly as they are; nothing about the deterministic scoring or fallback
logic is duplicated. Verified by running the existing test suite unchanged
after this phase's work (184/184 pass).

## Adaptation Catalogue

Reuses the existing `adaptations.models.Adaptation` table (12 entries,
seeded by `seed_demo`, already powering the real kiosk pipeline) rather
than building a second, competing catalogue — per this phase's own
instruction: "If the repository already has an adaptations app, extend it
rather than duplicating it." A few of this phase's suggested id spellings
differ cosmetically from the existing catalogue's (`increase_spacing` vs.
`increase_control_spacing`, `caption_audio` vs. `captions`,
`step_by_step_flow` vs. `guided_step_by_step_flow`, etc.) — the existing
names were kept rather than renamed, since renaming a catalogue entry's
primary key would require migrating existing `AdaptationResult` foreign
keys from the seeded example sessions for a purely cosmetic gain.

`adaptations/services/catalogue.py::AdaptationCatalogueService` is the one
new addition here — a thin, named service (`get_all_active()`,
`get_for_barrier()`, `get_by_id()`) wrapping the existing model so the AI
engine and recommender never query it directly.

## Scoring

```
Score = (benefit × 1.0) + (relevance × 1.0) + (preference × 1.0)
      + (confidence × 1.0) − (cost × 1.0) − (risk × 1.0)
```

Weights are centralized in `adaptations/services/config.py`, all `1.0` —
documented as a deliberate choice: the smallest-intervention behaviour
comes from the cost/risk *values* the catalogue assigns each adaptation,
not from artificially weighting one factor over another (see the file's
docstring for the full reasoning). The raw sum scale (roughly -1.5 to 3.0
in practice) is preserved rather than rescaled to 0-5/0-100, to avoid
changing the already-tested existing scoring behaviour.

Empirically verified against the real seeded demo (`increase_target_size`
scores 2.77 vs. `alternative_voice_input`'s 1.43 for the identical
`small_tap_targets` barrier) — the smallest-intervention principle holds
because of the cost/risk terms, not a hand-tuned override.

## AI Decision Engine

New orchestration (`adaptations/services/recommender.py`), reusing the
existing, provider-agnostic `ai_engine.services.llm_client` unchanged. New
Pydantic schemas (`AdaptationRanking`, `AdaptationRecommendationResponse`
in `ai_engine/services/schemas.py`, added alongside the existing
per-barrier `AIDecisionResponse`, not replacing it) and a new prompt
(`RECOMMENDER_SYSTEM_PROMPT`/`build_recommender_prompt` in `prompts.py`).

The LLM receives: the task descriptor, the detected barriers (facts only),
and the full candidate pool with deterministic scores already computed —
never the raw Ability Profile, never anything about the person beyond what
a barrier's `evidence.ability_value` already states. It can only return an
`adaptation_id` that exists in the candidates it was given.

## Validation and hallucination defense

Every AI response is checked, in order:
1. Valid JSON?
2. Parses against `AdaptationRecommendationResponse` (required fields,
   types)?
3. `selected_adaptation_id` present in the candidate pool?
4. Every id in `ranked_adaptations` present in the candidate pool?

Any failure at any step discards the *entire* AI response and falls back
to the deterministic top-scored candidate — never a partial trust of a
malformed response. `adaptations/test_recommender.py::AIRecommenderTests`
exercises all of this with a mocked LLM (invalid JSON, missing fields, an
invented adaptation id, a hallucinated ranking entry, a timeout, no API
key) — no test in this project depends on a real external LLM call.

## Safety Validation

`adaptations/services/validator.py::AdaptationSafetyValidator` — independent
of both the scorer and the LLM, re-checking from scratch:

| # | Rule | Check |
|---|---|---|
| 1 | Exists in catalogue | `adaptation is not None` |
| 2 | Active | `adaptation.enabled` |
| 3 | Supports this barrier | `barrier.barrier_type in adaptation.resolves_barrier_types` |
| 4 | Ability-dimension compatible | the barrier's `ability_dimension` is present in the profile |
| 5 | Task-compatible | `adaptation.is_allowed_for_task(task_id)` |
| 6/7 | No unsupported behaviour / task alteration | every `ui_effects` key is on the `ALLOWED_UI_EFFECT_KEYS` allowlist |
| 8 | High-risk needs confirmation | `risk_level == "high"` → `approved=True, requires_confirmation=True` |
| 9 | No safe adaptation | the recommender tries the next-best candidate; if all fail, returns `"no_safe_adaptation"` |

If the top pick fails validation, `AdaptationRecommender` degrades to the
next-highest-scored candidate automatically (Phase 5 section 32) — the
demo never crashes because one candidate turned out unsafe.

## Deterministic fallback

Triggered by: no LLM configured, provider call fails/times out, malformed
JSON, a schema-invalid response, an unknown `selected_adaptation_id`, or
an unknown id anywhere in `ranked_adaptations`. In every case, the response
correctly labels `"source": "deterministic_fallback"` — never claims
`"ai"` for a fallback decision.

## API

`POST /api/adaptations/recommend/` — extended with the same dual-mode
pattern as Phases 3/4: `{"session_id"}` (unchanged, powers the real kiosk)
or `{"user_id","task_id","environment_id"}` (new, standalone, non-
persisting). See [API.md](API.md) for the full contract and worked
example.

## Frontend

`AdaptationDecisionPanel.jsx` — appended to the Barrier Analysis section
once barriers exist, behind its own `[Recommend Adaptation]` button:
Candidate Interventions (✓/○ + score), AI Decision (source badge +
rationale), Safety Validation (approved/requires-confirmation). Nothing
about the kiosk (`KioskView.jsx`, `DemoPage.jsx`) was touched.

## Testing

`adaptations/test_recommender.py` — 46 tests: catalogue (5), scoring
compatibility with `BarrierResult` (3), safety validator (all 9 rules,
one test each), recommender unit tests (no-barrier / no-candidate paths,
no LLM call when no barriers exist), AI engine tests (9, all mocked —
valid response, unknown adaptation, invalid JSON, missing field, bad
ranking entry, timeout, no API key, "never returns an invented
adaptation"), full API integration against all three seeded personas, and
a `RegressionTests` class re-verifying Phase 1-4 plus the pre-existing
session-based recommendation flow. **184/184 tests pass** project-wide.

## Security

The LLM prompt never receives the whole Ability Profile, medical
information, or free text about the person — only the barriers already
detected (which already state only functional facts) and the candidate
pool. `AI_API_KEY` lives only in `backend/.env`, never sent to or readable
by the frontend. `AI_AVAILABLE=False` (the default, no key configured)
never blocks startup — `AdaptationRecommender._decide()` checks
`llm_client.is_configured()` first and skips the network call entirely.

## Phase 5 Limitations

- The approved adaptation is returned but never applied — no kiosk
  re-render happens anywhere in this phase's code.
- No adaptive kiosk rendering yet (Phase 6).
- No feedback/learning yet (Phase 7) — the existing
  `AbilityProfile.update_dimension_confidence()` learning hook from the
  pre-existing pipeline is untouched and unused by this phase's new code.
- No production computer-vision pipeline (unchanged from Phase 3/4 — still
  fixture-only).
- The LLM is entirely optional; every code path here was verified with
  `AI_PROVIDER=none` (the default) using the deterministic fallback.

## Ready for Phase 6

`AdaptationRecommender.recommend()` returns exactly:

```json
{ "barriers": [...], "candidates": [...],
  "selected_adaptation": { "adaptation_id": "increase_target_size", "score": 2.77,
                            "reason": "...", "source": "deterministic_fallback",
                            "validated": true, "requires_confirmation": false } }
```

Phase 6 can consume `selected_adaptation.adaptation_id` directly against
the existing `Adaptation.ui_effects` (already a fixed, allowlisted
vocabulary — `button_scale`, `contrast`, `flow`, etc., per
`ALLOWED_UI_EFFECT_KEYS`) to render the adaptive kiosk — without this
phase having rendered anything itself.
