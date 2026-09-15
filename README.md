# AbilityOS — An Operating System for Human Abilities

> "AbilityOS understands what a person can comfortably do, understands the task they
> are trying to perform, identifies the barrier between the person and the task, and
> chooses the smallest useful intervention to make the task easier and more
> independent."

Track 04 — BME × Assistive Technology · Challenge theme: **One Small Change**

## The problem

People are often fully capable of completing an everyday task — buying a ticket,
using a kiosk — but the interface in front of them creates a functional mismatch:
targets too small for their dexterity, contrast too low for their vision, too many
choices at once for their cognitive load. The person didn't fail the task; the
interface failed the person.

## The solution

AbilityOS is a decision-making layer that sits between a person and the technology
they use. It keeps a consented, **functional** (never diagnostic) Ability Profile,
watches what task someone is trying to complete, compares that against the current
environment, detects the specific barrier standing in the way, and applies the
smallest adaptation that removes it — without changing what the task actually is.
It then measures whether that adaptation actually helped, rather than assuming a UI
change is automatically an improvement.

This repository is a working hackathon prototype of that loop, built end-to-end: a
Django/DRF backend that really runs barrier detection and adaptation scoring, an AI
Decision Engine that reasons on top of it (with a deterministic fallback so a missing
API key never breaks the demo), a React kiosk frontend where applying an adaptation
actually changes the interface, and an outcome-measurement layer that turns a
completed session into structured evidence rather than a claimed success.

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2 + Django REST Framework, `djangorestframework-simplejwt` (JWT auth infrastructure), `django-cors-headers` |
| Database | PostgreSQL (`DATABASE_URL`) or SQLite (zero-setup local/demo default) |
| AI Decision Engine | Provider-agnostic LLM client (OpenAI/Anthropic-compatible), Pydantic response validation; fully optional |
| Frontend | React 19 (Vite), deliberately plain JavaScript (JSDoc types, no TypeScript build step) |
| Testing | Django's built-in test runner (`unittest`-based), Playwright for live frontend verification (no Jest/Vitest configured) |
| Linting | `oxlint` (frontend) |

## Prerequisites

- Python 3.11+ (developed and tested against 3.11)
- Node.js 20.19+ or 22.12+ (Vite 8's minimum — see `frontend/node_modules/vite`'s
  `engines` field) / npm
- No database server required for local/demo use (SQLite); PostgreSQL only if you
  set `DATABASE_URL`

## What's real here

Every part of the pipeline below is a live code path, not a canned demo:

- **Barrier detection** is deterministic (threshold comparisons against the Ability
  Profile, task and environment) — see `backend/barriers/services/detection.py`.
- **Adaptation scoring** implements the `Benefit + Relevance + Preference + Confidence
  − Cost − Risk` formula from the spec — see `backend/adaptations/services/scoring.py`.
- **The AI Decision Engine** calls a real LLM provider if one is configured
  (`AI_PROVIDER`/`AI_API_KEY`), validates its JSON response, and rejects anything that
  picks an adaptation outside the candidate list. With no provider configured, it
  runs the deterministic scoring path instead — a legitimate decision path, not a
  degraded stub. See `backend/ai_engine/`.
- **The kiosk frontend** genuinely renders larger buttons / higher contrast / a
  step-by-step wizard depending on which adaptation was approved, and — before an
  adaptation is applied — undersized controls have a real chance of registering a
  missed tap for a reduced-dexterity profile, producing real error/time metrics.
- **The before/after metrics** are aggregated from real `InteractionSession`/
  `Feedback` rows (seed data is clearly labelled `is_seed`), not hardcoded numbers.
- **Outcome measurement** (Phase 7) tracks real step-level interaction events,
  collects a short post-task feedback screen, and computes a deterministic,
  documented outcome score and per-adaptation/per-barrier effectiveness — no AI
  required, and nothing here ever auto-edits a person's Ability Profile.

## Repository layout

```
AbilityOS/
├── backend/          Django + DRF backend (see backend/requirements.txt)
│   ├── config/        settings, urls
│   ├── users/          accounts + consent
│   ├── abilities/      the Ability Profile model
│   ├── tasks/          task/step registry + seed_demo management command
│   ├── environments/   the kiosk environment descriptor (JSON fixture or vision)
│   ├── barriers/       deterministic barrier detection
│   ├── adaptations/    the adaptation catalogue, scoring formula, safety rules
│   ├── ai_engine/      LLM client, prompts, schema validation, fallback, vision
│   ├── feedback/       InteractionSession + Feedback models
│   ├── analytics/      before/after + dashboard aggregation
│   ├── api/            orchestrator service + REST endpoints tying it together
│   └── fixtures/       kiosk_standard.json environment fixture
├── frontend/          React (Vite) kiosk + developer panel + analytics dashboard
└── docs/              setup, architecture, phase summaries, API, database, ability profile, task/environment, barrier detection, adaptation + AI decision engine, adaptive kiosk, outcome analytics, hardening + deployment readiness, demo guide
```

## Quick start

### 1. Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate      macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 4343
```

This runs on **SQLite by default** — no database server required. To use PostgreSQL
instead, copy `backend/.env.example` to `backend/.env` and set `DATABASE_URL` (see
[docs/DATABASE.md](docs/DATABASE.md)). Full step-by-step instructions, including
troubleshooting, are in [docs/SETUP.md](docs/SETUP.md).

Sanity-check the backend on its own before starting the frontend — `GET /api/health/`
runs a real query against the database and reports the result, not just "the process
is alive":

```bash
curl http://localhost:4343/api/health/
```

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3434` (configured in `vite.config.js`). The frontend talks to
the backend at `http://localhost:4343/api` by default (set in `frontend/.env.local`)
— override with `VITE_API_BASE_URL` there if you run the backend on a different port.

### 3. Run the demo

Open `http://localhost:3434` — you'll land on the AbilityOS landing page first (its
status line confirms the frontend can actually reach the backend and database).
Click **Explore AbilityOS** to enter the profile journey:

**Select a demo user → Consent → Ability Profile → Profile Summary → Task &
Environment → (header nav) Kiosk Demo**

Three seeded personas are available (`python manage.py seed_demo`, password
`demo-password` for all three if you ever need to log in directly):

| Persona | Notable ability values |
|---|---|
| Demo User — Low Vision | `vision: large-text-needed`, `dexterity: reduced-precision` |
| Demo User — Hearing Difficulty | `hearing: relies-on-visual`, `preferred_modality: mixed` |
| Demo User — Cognitive Load | `cognition: needs-step-by-step`, `fatigue: moderate` |

Pick one, agree to the consent screen, review/edit the Ability Profile form (every
option shown is a real, validated value — see
[docs/ABILITY_PROFILE.md](docs/ABILITY_PROFILE.md)), save, and click **Continue to
Task & Environment** to see the Task Understanding and Environment Understanding
engines run for real (facts only — no barrier judgement yet, see
[docs/PHASE_3.md](docs/PHASE_3.md)). Click **Detect Barriers** then **Recommend
Adaptation** to see the Adaptation Engine and Safety Validator decide and approve
a real adaptation (no rendering yet at that point, see [docs/PHASE_5.md](docs/PHASE_5.md)),
then **Open Adaptive Kiosk** to actually see it applied — the same real kiosk the
header's **Kiosk Demo** link reaches directly, including the adaptation indicator
and a View Original/View Adaptive comparison toggle (see
[docs/PHASE_6.md](docs/PHASE_6.md)). Complete (or leave without finishing) the
task to see a short feedback screen and a plain-language outcome summary, then
open **Analytics** in the header for the accessibility outcomes dashboard —
standard vs. adaptive comparison, per-adaptation/per-barrier observed outcomes,
and recent sessions (see [docs/PHASE_7.md](docs/PHASE_7.md)). See
[docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) for the full judge-facing walkthrough,
including switching profiles to show the same engine producing a different
adaptation.

## Environment variables

All variables are optional — see `backend/.env.example` and `frontend/.env.example`
for the full list with defaults. The two worth knowing about:

| Variable | Effect when unset |
|---|---|
| `DATABASE_URL` (backend) | Falls back to a local SQLite file. |
| `AI_PROVIDER` / `AI_API_KEY` (backend) | AI Decision Engine uses the deterministic scoring fallback instead of an LLM call. |

## AI configuration and fallback

AbilityOS deliberately never puts an LLM in sole control of the interface (see
[docs/AI_DECISION_ENGINE.md](docs/AI_DECISION_ENGINE.md)). To enable live LLM
reasoning, set in `backend/.env`:

```
AI_PROVIDER=openai   # or anthropic
AI_API_KEY=sk-...
AI_MODEL=gpt-4o-mini
```

With nothing configured, every decision is still made — via the deterministic
Adaptation Engine formula — and the developer panel clearly labels which path was
used ("Deterministic fallback" vs "AI decision engine").

## Running tests

```bash
cd backend
python manage.py test
```

237 tests cover Ability Profile validation, task/environment understanding, barrier
detection for every barrier type, adaptation scoring/ranking, the safety rule
engine, AI response validation and fallback behaviour, the adaptive kiosk's
safe-rendering contract, the full orchestrated workflow via the real REST API, and
(Phase 7) session lifecycle/state transitions, interaction events, feedback
validation, outcome score/learning signal calculation, and analytics aggregation.
See [docs/API.md](docs/API.md) for the endpoint reference these tests exercise.

## Database

PostgreSQL is the intended production database (`DATABASE_URL`); SQLite is the
zero-setup default for local development and the hackathon demo. See
[docs/DATABASE.md](docs/DATABASE.md) for the schema and entity relationships.

## Project structure deep-dive

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the module breakdown and how the
12 conceptual modules from the spec map onto the 10 Django apps + React frontend.

## Privacy

AbilityOS is **not** a medical diagnosis platform and does not behave like one:

- The Ability Profile stores functional statements ("dexterity:
  reduced-precision"), never a diagnosis, condition name, or medical history.
- Voice/audio features (`speechSynthesis`) are one-shot, on-demand text-to-speech
  only — nothing in this codebase records or listens to a microphone.
- Step-level interaction events (`InteractionEvent`) capture structured,
  task-relevant facts only (which control, which step, what happened) — never raw
  keystrokes, audio, video, or unrelated application activity; metadata is capped
  in size server-side.
- Optional feedback comments are capped at 500 characters, stored only against
  the session, never exposed publicly, and never used for AI training (there is
  no AI training pipeline in this project).
- The Learning Signal (Phase 7) is exposed as evidence for a person to read — it
  never automatically edits an Ability Profile or silently changes a future
  recommendation. See [docs/PHASE_7.md](docs/PHASE_7.md) for the full mechanism.
- Every endpoint is reachable anonymously by design, a documented choice for the
  login-free hackathon demo (see `backend/config/settings.py`'s `REST_FRAMEWORK`
  comment) — but any request that *does* carry a real authenticated identity is
  held to real ownership rules (a user can't read or write another user's
  profile, consent, session, or feedback; see `users/services/ownership.py`).

## Limitations

This is a hackathon MVP, not a production system:

- One task (`purchase_ticket`) and one environment fixture are seeded; the barrier/
  adaptation catalogues cover 5 barrier types and 12 adaptations, not every possible
  accessibility need.
- Computer-vision environment analysis (OpenCV/OCR) is implemented but optional and
  off by default (`VISION_ENABLED=false`) — the JSON-fixture path is what the demo
  relies on.
- The "struggle simulation" (missed taps on undersized controls) is a reasonable
  approximation of a dexterity barrier, not a clinically validated motor-impairment
  model.
- Everything runs on a single seeded set of demo personas; there is no real user
  account system, multi-device profile sync, or on-device learning.
- JWT login infrastructure exists (`POST /api/auth/login/`) but isn't consumed by
  the frontend demo flow, which selects a persona directly — a real deployment
  would wire a login screen and a token-refresh flow (neither exists today, since
  nothing currently calls the login endpoint).
- No Docker setup — the existing manual setup (SQLite + `pip install` + `npm
  install`) is already a fast, zero-infrastructure path for a judge running this
  once; Docker was deliberately not added for a project this size.
- No rate limiting beyond three lightweight, IP-based throttles (login, session
  start, adaptation recommendation) — sufficient for a demo, not abuse-hardened
  for production traffic.
- The outcome score and adaptation-effectiveness thresholds (`analytics/config.py`)
  are reasonable, documented, hackathon-scope defaults, not empirically tuned
  against real accessibility research.

## Future roadmap

Explicitly **not** implemented, and out of scope for this hackathon prototype:

- A learning loop that uses the Learning Signal to actually improve future
  recommendations (Phase 7 generates the signal; nothing yet consumes it).
- Real camera-based environment understanding (the vision pipeline exists behind
  `VISION_ENABLED` but isn't the demo path).
- Real-world kiosk hardware integration, wearable signals, or IoT/environment
  sensors.
- Cross-device adaptation (the same profile following a person between devices).
- A developer SDK for third-party kiosks/apps to consume AbilityOS decisions.
- A richer accessibility profile (more dimensions, finer-grained levels) informed
  by real user research.
- Longitudinal, multi-session adaptation learning beyond the single-session
  Learning Signal.
- A mobile accessibility layer.
- Production authentication (a real login UI, token refresh, per-deployment
  account management) and infrastructure hardening beyond what's described above.

## Attribution

Built against the "AbilityOS — Complete Project Documentation" hackathon
specification (Track 04, BME × Assistive Technology, "One Small Change").
