# AbilityOS — An Operating System for Human Abilities

> "AbilityOS understands what a person can comfortably do, understands the task they
> are trying to perform, identifies the barrier between the person and the task, and
> chooses the smallest useful intervention to make the task easier and more
> independent."

Track 04 — BME × Assistive Technology · Challenge theme: **One Small Change**

AbilityOS is a decision-making layer that sits between a person and the technology
they use. It keeps a consented, **functional** (never diagnostic) Ability Profile,
watches what task someone is trying to complete, compares that against the current
environment, detects the specific barrier standing in the way, and applies the
smallest adaptation that removes it — without changing what the task actually is.

This repository is a working hackathon prototype of that loop, built end-to-end: a
Django/DRF backend that really runs barrier detection and adaptation scoring, an AI
Decision Engine that reasons on top of it (with a deterministic fallback so a missing
API key never breaks the demo), and a React kiosk frontend where applying an
adaptation actually changes the interface.

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
└── docs/              architecture, API, database, AI engine and demo guide
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
[docs/DATABASE.md](docs/DATABASE.md)).

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

Pick a demo Ability Profile, click **I Agree** on the consent gate, then **Start
Ticket Purchase**. See [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) for the full
judge-facing walkthrough, including switching profiles to show the same engine
producing a different adaptation.

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

50 tests cover Ability Profile validation, barrier detection for every barrier type,
adaptation scoring/ranking, the safety rule engine, AI response validation and
fallback behaviour, the full orchestrated workflow via the real REST API, and the
learning-loop confidence update. See [docs/API.md](docs/API.md) for the endpoint
reference these tests exercise.

## Database

PostgreSQL is the intended production database (`DATABASE_URL`); SQLite is the
zero-setup default for local development and the hackathon demo. See
[docs/DATABASE.md](docs/DATABASE.md) for the schema and entity relationships.

## Project structure deep-dive

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the module breakdown and how the
12 conceptual modules from the spec map onto the 10 Django apps + React frontend.

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
  account system, multi-device profile sync, or on-device learning — all explicitly
  future work (see the project spec's Part 22/23).

## Attribution

Built against the "AbilityOS — Complete Project Documentation" hackathon
specification (Track 04, BME × Assistive Technology, "One Small Change").
