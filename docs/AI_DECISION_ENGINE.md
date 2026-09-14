# AI Decision Engine

## The guiding principle

> "AI may reason about the adaptation, but it must not invent the user's ability
> profile."

Concretely, that means three separate guarantees, each enforced in code rather than
by convention:

1. **The LLM never sees more than it needs.** `decision_engine._decide_with_ai()`
   builds its prompt from only the Ability Profile dimensions behind the *detected*
   barriers (`ai_engine/services/decision_engine.py`, `relevant_dims`) — never the
   whole profile, never open-ended text about the person.
2. **The LLM can only choose from a fixed candidate list.** The prompt includes each
   barrier's pre-scored candidates by id; the response is checked against that exact
   set (`by_barrier_type` / `candidate_ids` in `decision_engine.py`). An unknown id is
   discarded, not passed through.
3. **The LLM's choice is never applied without independent validation.** Whatever it
   picks (or whatever the fallback picks) is re-checked by
   `adaptations/services/rules.py` before `AdaptationResult.approved` is ever `True`.

## The scoring formula (always runs)

```
Adaptation Score = Accessibility Benefit + Task Relevance + User Preference
                    + Confidence − Interaction Cost − Risk
```

Implemented in `adaptations/services/scoring.py`:

- **Accessibility Benefit** — the catalogue's base benefit for that adaptation,
  scaled by how severe the barrier is (`0.5 + 0.5 × severity`).
- **Task Relevance** — `1.0` if the adaptation is allowed for this task, else `0`.
- **User Preference** — `+0.2` if the adaptation's modality matches the profile's
  `preferred_modality`.
- **Confidence** — the barrier's detection confidence (i.e. how sure the profile
  signal behind it is).
- **Interaction Cost** / **Risk** — the catalogue's cost/risk values, subtracted.

This is what makes AbilityOS conservative by design: a cheap, low-risk fix
(`increase_target_size`, cost 0.10, risk 0.05) reliably outscores an expensive,
high-risk one (`alternative_voice_input`, cost 0.70, risk 0.50) even though the
latter has a slightly higher raw benefit — see
`adaptations/tests.py::test_low_cost_low_risk_adaptation_outranks_expensive_high_risk_one`.

## The AI layer (optional, on top)

When `AI_PROVIDER`/`AI_API_KEY` are set, `decision_engine.decide()`:

1. Ranks candidates deterministically first (always).
2. Sends each barrier's candidates (id, deterministic score, benefit/cost/risk) plus
   the relevant profile fields and task descriptor to the configured LLM
   (`ai_engine/services/llm_client.py` — provider-agnostic; OpenAI and Anthropic
   backends are implemented, more can be added without touching the rest of the app).
3. Parses the response as JSON and validates it against
   `ai_engine/services/schemas.py`'s Pydantic models.
4. For each barrier: if the AI's `selected_adaptation` is a valid candidate id, uses
   it (`source: "ai"`) with the AI's stated confidence and rationale. Otherwise, uses
   the deterministic top-scored candidate for that barrier (`source: "fallback"`).

## Failure modes and what happens

| Failure | Where it's caught | Result |
|---|---|---|
| No provider configured | `llm_client.is_configured()` returns `False` | Every decision uses the deterministic path; no network call attempted. |
| Provider SDK not installed | `_call_openai`/`_call_anthropic` `ImportError` | Raises `LLMUnavailableError`, caught in `decide()` → full fallback. |
| Network error / timeout / API error | `llm_client.call()`'s broad `except Exception` | Same — `LLMUnavailableError` → full fallback, `ai_error` set on the outcome. |
| Malformed JSON | `json.JSONDecodeError` in `_decide_with_ai` | Full fallback for all barriers in that call. |
| Valid JSON, unknown `selected_adaptation` | Candidate-id check in `decide()` | Fallback for *that barrier only* — other barriers can still use the AI's picks. |
| `confidence` out of `[0, 1]` or a missing field | Pydantic `ValidationError` | Same as malformed JSON. |

All of this is exercised in `backend/ai_engine/tests.py` by mocking
`llm_client.call` directly — no real API key is needed to verify the contract holds.

## Why not let the LLM render the UI directly

The frontend never receives free-form instructions from the AI. It receives an
`Adaptation` row's `ui_effects` JSON — a small, fixed vocabulary
(`button_scale`, `contrast`, `flow`, `choice_limit`, `haptics`, `voice_prompts`, ...)
defined in the catalogue, not generated per-request. This is what keeps the
adaptive UI safe to auto-apply: the set of things that can happen to the interface is
closed and reviewable, even though which one happens is decided dynamically.
