# Database

## Engine

AbilityOS is designed for **PostgreSQL** — the JSON columns (Ability Profile
dimensions, environment data, adaptation `ui_effects`, candidate lists) are plain
Django `JSONField`s, which map to Postgres's native `jsonb`. For a zero-setup local
run, leaving `DATABASE_URL` unset falls back to **SQLite**, which supports the same
`JSONField` API (stored as text) — every model and query in this codebase works
unchanged on either backend.

To use Postgres:

```bash
# backend/.env
DATABASE_URL=postgres://abilityos:abilityos@localhost:5432/abilityos
```

```sql
CREATE DATABASE abilityos;
CREATE USER abilityos WITH PASSWORD 'abilityos';
GRANT ALL PRIVILEGES ON DATABASE abilityos TO abilityos;
```

Then `pip install psycopg2-binary` (already in `requirements.txt`) and run
`python manage.py migrate`.

## Core tables

| Model | App | Purpose |
|---|---|---|
| `User` | `users` | Account identity (extends Django's `AbstractUser`). |
| `ConsentRecord` | `users` | What a user has agreed to share/use, and when. |
| `AbilityProfile` | `abilities` | One functional profile per user — `dimensions` JSONField holds `{level, confidence, source}` per dimension (vision, hearing, dexterity, reach, mobility, speech, cognition, fatigue, reaction_speed). |
| `Task` / `TaskStep` | `tasks` | Registry of known tasks and their ordered steps/controls. |
| `Environment` | `environments` | A captured screen/physical context — `data` JSONField holds controls, contrast, choice count, audio alert flag. |
| `InteractionSession` | `feedback` | One row per person-task-environment interaction; the row everything else hangs off. |
| `Barrier` | `barriers` | A detected mismatch for a session — type, severity, confidence, evidence. |
| `Adaptation` | `adaptations` | The fixed catalogue of accessibility actions and their cost/risk/`ui_effects`. |
| `AdaptationResult` | `adaptations` | Which adaptation was selected for a given barrier within a session, its score breakdown, and whether it was approved/confirmed/applied. |
| `Feedback` | `feedback` | Outcome metrics (completion, errors, time, assistance, effort, confidence) for a session. |

## Entity relationships

```
User
 ├── ConsentRecord   (1-1)
 └── AbilityProfile  (1-1)

InteractionSession
 ├── User          (FK)
 ├── Task           (FK)
 ├── Environment    (FK, nullable)
 ├── Barrier        (1-many)
 ├── AdaptationResult (1-many — one per distinct barrier, not one per session)
 └── Feedback       (1-1)

AdaptationResult
 ├── Barrier        (FK)
 └── Adaptation     (FK, PROTECT — a catalogue entry can't be deleted while referenced)
```

The one deliberate deviation from the spec's literal ER diagram: `AdaptationResult`
is `InteractionSession` **1-to-many**, not 1-to-1. A single session can face several
distinct barriers at once (e.g. low vision *and* reduced dexterity), and each gets
its own winning adaptation — this is what produces the "increase target size +
increase contrast" combined result in the worked example (spec Part 12/15).

## Migrations

Standard Django migrations, one set per app (`backend/*/migrations/`). Run
`python manage.py migrate` after cloning; `python manage.py seed_demo` is idempotent
and safe to re-run (it uses `update_or_create`/`get_or_create` throughout).
