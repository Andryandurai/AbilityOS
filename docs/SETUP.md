# Setup

Step-by-step installation for a fresh clone. See [ARCHITECTURE.md](ARCHITECTURE.md)
for how the pieces fit together and [API.md](API.md) for the endpoint reference.

## Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- PostgreSQL 14+ (optional — SQLite is the zero-setup default)

## 1. Backend

```bash
cd backend
python -m venv venv
```

Activate it:

```bash
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

Install dependencies and set up the database:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
```

`seed_demo` is idempotent — safe to re-run any time. It creates:
- the `purchase_ticket` task and its 4 steps
- the `kiosk_standard` environment fixture
- the 12-entry adaptation catalogue
- 3 demo Ability Profiles (`demo_low_vision_dexterity`, `demo_hearing_difficulty`,
  `demo_cognitive_load`), each with password `demo-password`
- a handful of labelled seed `InteractionSession`/`Feedback` rows so the analytics
  panel isn't empty on first launch

Start the server:

```bash
python manage.py runserver 4343
```

Verify it's actually working (not just "the process started") by checking the health
endpoint — it runs a real query against the database:

```bash
curl http://localhost:4343/api/health/
```

```json
{
  "status": "ok",
  "service": "AbilityOS API",
  "database": { "engine": "sqlite", "connected": true, "seeded_user_count": 3 },
  "ai_decision_engine": { "provider": "none", "configured": false }
}
```

### Optional: create a Django admin superuser

```bash
python manage.py createsuperuser
```

Lets you browse the raw data (Ability Profiles, barriers, adaptation results) at
`http://localhost:4343/admin/`.

### Optional: PostgreSQL instead of SQLite

```bash
cp .env.example .env
```

Edit `.env` and set:

```
DATABASE_URL=postgres://abilityos:abilityos@localhost:5432/abilityos
```

Create the database first:

```sql
CREATE DATABASE abilityos;
CREATE USER abilityos WITH PASSWORD 'abilityos';
GRANT ALL PRIVILEGES ON DATABASE abilityos TO abilityos;
```

Then run `python manage.py migrate` again — Django will apply all migrations to
Postgres instead of the SQLite file. See [DATABASE.md](DATABASE.md) for the schema.

## 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Opens on `http://localhost:3434` (configured in `vite.config.js`). It expects the
backend at `http://localhost:4343/api` by default (`frontend/.env.local`, sourced
from `frontend/.env.example`) — change `VITE_API_BASE_URL` there if you run the
backend on a different port.

## 3. Confirm the full chain works

Open `http://localhost:3434` in a browser. The landing page itself proves the chain:
its status line performs a live `GET /api/health/` call and reports whether the
backend and database are reachable. If it says "Could not reach the backend," the
Django server isn't running or the port doesn't match `VITE_API_BASE_URL`.

## Environment variables reference

| File | Variable | Default if unset |
|---|---|---|
| `backend/.env` | `DJANGO_SECRET_KEY` | An insecure dev-only key (change for any shared deployment) |
| | `DEBUG` | `true` |
| | `DATABASE_URL` | unset → SQLite at `backend/db.sqlite3` |
| | `CORS_ALLOWED_ORIGINS` | `http://localhost:3434,http://127.0.0.1:3434` |
| | `AI_PROVIDER` / `AI_API_KEY` / `AI_MODEL` | unset → deterministic Adaptation Engine fallback, no LLM call |
| | `VISION_ENABLED` | `false` → JSON-fixture environment path only |
| `frontend/.env.local` | `VITE_API_BASE_URL` | `http://localhost:4343/api` |

Full annotated lists: `backend/.env.example`, `frontend/.env.example`. Neither file
should ever be committed with real secrets — both are gitignored.

## Running tests

```bash
cd backend
python manage.py test
```

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Landing page says "Could not reach the backend" | Django isn't running, or is on a different port than `VITE_API_BASE_URL` |
| `python manage.py migrate` fails with a psycopg2 import error | `DATABASE_URL` is set to a Postgres URL but `psycopg2-binary` isn't installed — either `pip install psycopg2-binary` or unset `DATABASE_URL` to use SQLite |
| Profile list is empty | `seed_demo` hasn't been run yet |
| `EADDRINUSE` / port already in use | Another process is already listening on 4343 or 3434 — stop it or change the port in `vite.config.js` / the `runserver` command |
