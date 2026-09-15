# Phase 3 — Task Understanding + Environment Understanding

## Purpose

Phase 3 answers two questions, and *only* these two:

1. **What is the person trying to accomplish?** (Task Understanding Engine)
2. **What does the current interaction environment look like?** (Environment
   Understanding Engine)

It deliberately does **not** answer "can this person do this comfortably?" —
that requires comparing these facts against an Ability Profile, which is
Barrier Detection's job (a later phase). Task facts and environment facts
are never barriers on their own:

| Phase 3 says (a fact) | Phase 3 never says (a judgement) |
|---|---|
| "Confirm button is 120×45px." | "This button is too small for this user." |
| "Contrast is low." | "Low contrast is a problem here." |
| "8 controls are visible." | "This is too many choices." |

This separation is enforced, not just documented: every backend test in
`tasks/tests.py`/`environments/tests.py` asserts the returned descriptors
never contain the words "barrier", "too small", "cannot use", or
"inaccessible".

## Task Understanding Engine

`tasks/services/task_service.py::get_task_descriptor(task_id)` — a plain,
deterministic database lookup (`tasks.Task`/`tasks.TaskStep`, unchanged
data model from Phase 2/1, extended with `description`/`required` per step
and `time_limit_seconds` on the task). No LLM, no fuzzy matching: an exact
`task_id` either exists or it raises `TaskNotFoundError` → HTTP 404.

**Endpoint:** `POST /api/tasks/analyze/` — see [API.md](API.md).

## Environment Understanding Engine

`environments/services/analyzer.py::EnvironmentAnalyzer` — a small
interface with three methods, only one of which is implemented:

- `analyze_fixture(environment_id)` — **implemented.** Checks the database
  first (what `seed_demo` populates), falls back to reading the JSON file
  directly under `environments/fixtures/`, so the fixture works even
  before a migrate+seed. Raises `EnvironmentNotFoundError` for an unknown
  id.
- `analyze_screenshot(image_base64)` — raises `NotImplementedError`.
- `analyze_camera(frame)` — raises `NotImplementedError`.

The other two methods exist on the interface (not omitted) specifically so
a future phase can implement real computer-vision analysis without
changing this class's shape — matching the project spec's "clean interface
for future AI/CV integration without actually depending on it."

**Endpoint:** `POST /api/environment/analyze/` — see [API.md](API.md).

### Why two environment fixtures exist

`kiosk_standard` (from Phase 1/an earlier build pass) already powers the
*working* barrier-detection/adaptation pipeline, and its `contrast` field
is a plain number (`0.52`) because that's what
`barriers/services/detection.py`'s threshold comparisons expect. This
phase's documented `EnvironmentDescriptor` shape uses a richer nested
`contrast: {level, background, foreground}` object plus `lighting` and
per-control `x`/`y` — reshaping `kiosk_standard` to match would have broken
that already-working, already-tested pipeline for no benefit. Instead,
`ticket_kiosk_default` is a **second**, new fixture matching this phase's
documented schema exactly, used only by the new Task & Environment screen.
Both are real, both are seeded by `seed_demo`, neither depends on the
other.

## Schemas

See the JSDoc typedefs in `frontend/src/constants/taskEnvironment.js` for
the exact field-by-field shape both descriptors return — they mirror the
backend responses exactly (the project is plain JavaScript, not
TypeScript, an established Phase 1 choice; JSDoc gives the same
documentation value without introducing a new toolchain).

## Frontend flow

```
Profile Summary
  -> "Continue to Task & Environment"
Task & Environment (TaskEnvironmentPage.jsx)
  -> [Analyze Task]         reveals the Task Descriptor
  -> [Analyze Environment]  reveals the Environment Descriptor (enabled once
                             the task has been analyzed)
  -> "Barrier Detection — Coming in Phase 4" (shown once both are analyzed)
  -> Back to Profile Summary
```

This screen intentionally dead-ends — it never renders a barrier, an
adaptation, or any accessibility conclusion. **The already-working kiosk
demo (real barrier detection, AI decision engine, adaptive UI — built and
verified in an earlier pass on this repo) is untouched and still reachable
via the header's "Kiosk Demo" navigation** once a profile is selected; this
phase only stopped routing the primary Profile-Summary journey through it,
per this phase's explicit scope. Nothing that already worked was deleted or
hidden.

## Testing

`tasks/tests.py` (`TaskServiceTests`, `TaskAnalyzeAPITests`) and
`environments/tests.py` (`EnvironmentAnalyzerTests`,
`EnvironmentAnalyzeAPITests`) cover: known/unknown lookups, deterministic
repeatability, 400 on a malformed request, 404 on an unknown id, the
`NotImplementedError` stubs, and the "never mentions a barrier" assertion.
The full existing suite (Phase 1/2) was re-run after every change — 103/103
pass.

## Explicit limitations (by design, this phase)

- Task understanding is deterministic (database lookup) — no LLM, no
  free-text task parsing.
- Environment analysis uses a JSON fixture only. `analyze_screenshot`/
  `analyze_camera` are real interface methods that raise
  `NotImplementedError` — they are not silently stubbed to return fake
  results.
- **No barrier detection is implemented by this phase's new code path.**
  (The Task & Environment screen never computes or displays one.)
- No AI reasoning of any kind runs in this phase's new code path.
- No adaptation scoring, safety validation, feedback, or analytics were
  touched by this phase.

## Ready for Phase 4

The two descriptors this phase produces are exactly what a barrier
detector needs:

```
AbilityProfile + TaskDescriptor + EnvironmentDescriptor -> List[Barrier]
```

Neither descriptor is shaped around the ticket kiosk specifically — a
`TaskDescriptor` describes any task's steps/controls, and an
`EnvironmentDescriptor` describes any screen's layout/contrast/noise —
so the same shapes work for a phone, a website, or a healthcare terminal,
not only this demo's kiosk.
