# The Ability Profile

## Purpose

The Ability Profile answers one question: **"What can this person comfortably
do right now?"** — never "what condition does this person have?" AbilityOS is
not a diagnostic tool. Every dimension is phrased functionally:

| Never stored | Stored instead |
|---|---|
| "User has Parkinson's disease." | `dexterity: reduced-precision` — "Precise touch is difficult." |
| "User has hearing loss." | `hearing: relies-on-visual` — "User relies on visual alerts." |
| "User has a cognitive disorder." | `cognition: prefers-fewer-choices` — "User prefers fewer simultaneous choices." |

This distinction is enforced structurally, not just by convention: the
`level` field for every dimension can only be one of a small, fixed set of
functional descriptions (`backend/abilities/constants.py`) — there is no
free-text field anywhere a diagnosis could be typed in.

## Reusability beyond the kiosk

Nothing in the schema below is ticket-kiosk-specific. `AbilityProfile` +
`TaskDescriptor` + `EnvironmentDescriptor` is designed to produce a barrier
list for *any* interface — a phone, a website, a smart-home panel, a
healthcare terminal, a transit gate — because the profile only describes the
person, never the task or the device.

## Dimensions

| Dimension | Allowed levels | What it represents |
|---|---|---|
| `vision` | `typical`, `low-contrast-sensitive`, `large-text-needed` | How reliably the person reads on-screen content at a given size/contrast. |
| `hearing` | `typical`, `partial`, `relies-on-visual` | How reliably the person receives audio notifications. |
| `dexterity` | `typical`, `reduced-precision`, `single-tap-only` | How precisely the person can tap, drag or perform fine gestures. |
| `reach` | `full`, `limited-upper`, `seated` | How comfortably the person can reach physical/on-screen controls. |
| `mobility` | `typical`, `limited`, `stationary` | How easily the person can move between physical steps of a task. |
| `speech` | `typical`, `limited`, `unavailable` | How reliably the person can use voice input. |
| `cognition` | `typical`, `prefers-fewer-choices`, `needs-step-by-step` | How many simultaneous choices/steps the person can comfortably process. |
| `fatigue` | `fresh`, `moderate`, `high` | How ability is currently trending during this session. |
| `reaction_speed` | `typical`, `slower`, `needs-extended-time` | How quickly the person can respond to a time-limited prompt. |

Note that **not every dimension's baseline is `typical`** — `reach`'s
no-barrier default is `full` and `fatigue`'s is `fresh`, because those words
describe that dimension's own comfortable state. A fresh profile is
initialized with each dimension's own baseline
(`abilities.models.default_dimensions()`), not one hardcoded string.

`preferred_modality` is a separate top-level field (not a `dimensions`
entry): `visual`, `voice`, `haptic`, or `mixed` — the interaction channel
the person prefers when several would work equally well.

## Confidence and source

Every dimension entry is `{level, confidence, source}`:

- **confidence** — `0.0` to `1.0`. Rejected outside that range
  (`abilities/services/profile_service.py::validate_dimension_payload`).
- **source** — one of `manual`, `inferred`, `default`, `session_signal`.
  - `manual`: a person explicitly set this (the Ability Profile editor
    always writes `manual` — Phase 2 section 8).
  - `default`: never explicitly set; this is a fresh profile's baseline.
  - `inferred` / `session_signal`: reserved for a future inference
    pipeline. **Phase 2 does not implement real inference** — there is no
    code path today that writes these sources from live interaction
    signals. `abilities.services.profile_service.apply_inferred_update()`
    exists so the priority rule below is architecturally in place and
    tested, ready for a later phase to call it for real.

## Manual beats inferred beats default

A person's own edit must never be silently overwritten by a future
inference guess. `apply_inferred_update()` checks the *existing* source's
priority before writing:

```
manual (3) > inferred (2) = session_signal (2) > default (1)
```

If the stored value's priority is higher than the incoming write's, the
write is dropped — the person's explicit choice wins. Proven directly at
the service layer in `abilities/tests.py::ProfileServiceTests` (no live
inference feature exists yet to exercise this through the API).

## Consent

No profile is used for adaptation without consent. `ConsentRecord` (`users`
app) tracks `granted`, `scope`, `granted_at`. Scope is a list of strings;
the only scope AbilityOS currently checks is `interaction_adaptation`.
`InteractionOrchestrator.start()` — the very first step of running the
kiosk demo — calls `users.services.consent_service.is_consented_for_adaptation()`
and refuses (HTTP 409) to start a session without it. Viewing or editing
your own profile never requires consent; only *using* it to adapt an
interaction does.

## Manual override via the API

`PATCH /api/users/{id}/ability-profile/` is the one write path a real
person goes through. It always tags what it writes as `source: "manual"`
regardless of what the caller sends — a person editing their own profile
is, by definition, the most trustworthy source there is.

## Privacy

- No medical history, diagnosis, or continuous surveillance data is ever
  collected.
- `DELETE /api/users/{id}/ability-profile/` ("Clear Profile") resets every
  dimension to its default and clears preferences — the user account
  itself is never touched.
- Consent can be revoked at any time (`POST .../consent/` with
  `{"granted": false}`), independent of clearing the profile.

## Future inference

Phase 2 deliberately does not pretend to have machine-learning inference.
The architecture is ready for it — `apply_inferred_update()`, the
`inferred`/`session_signal` sources, and the priority rule all exist — but
no barrier-detection or interaction-monitoring code writes to a profile
today. A future phase adding real inference only needs to call that
existing function; the safety rule (never overwrite a manual value) is
already enforced at the point of writing, not left to the inference code
to remember.
