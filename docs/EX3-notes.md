# EX3 — TrainFlow Coach

TrainFlow Coach is a local, full-stack workout-planning system. An LLM-backed
Coach service generates structured, schema-validated workout plans from the
persisted exercise catalog, the user's training context, and their recent
workout history — while remaining strictly bounded: it may only select existing
catalog exercises, and every plan is validated server-side.

## Architecture

```
                                USER (browser)
                                      │ HTTP :8501
                                      ▼
                    ┌──────────────────────────────────────┐
                    │   STREAMLIT INTERFACE  (interface/)   │
                    │   Login · Browse · Add · Coach        │
                    │   Holds JWT in session_state          │
                    └───────┬───────────────────────┬───────┘
              Bearer JWT    │                       │  Bearer JWT
              :8000         ▼                       ▼  :8001
        ┌───────────────────────────┐   ┌───────────────────────────────┐
        │   EXERCISE SERVICE  :8000  │   │      COACH SERVICE  :8001      │
        │   FastAPI + SQLModel       │   │   FastAPI (stateless)          │
        │                            │   │                                │
        │   ISSUES + VERIFIES JWT    │   │   Verifies JWT (shared secret) │
        │   /auth/token              │   │   scope: coach:use             │
        │                            │   │                                │
        │   CATALOG (GET public,     │   │   POST /plan:                  │
        │     writes need            │◄──┼── GET /exercises (catalog)     │
        │     exercises:write)       │◄──┼── GET /sessions  (history)     │
        │   HISTORY  /sessions       │   │   build deterministic context  │
        │     (history:read/write)   │   │   → LLM planner | fallback     │
        │                            │   │   → catalog-only validation    │
        │        ▲ owns ALL data     │   │                                │
        └────────┼───────────────────┘   │   ┌────────────┐ ┌───────────┐ │
                 ▼ SQLModel              │   │ LLMPlanner │ │ Fallback  │ │
        ┌──────────────────┐            │   └─────┬──────┘ └───────────┘ │
        │  SQLite (volume) │            │         │ if ANTHROPIC_API_KEY  │
        │  exercise        │            │         ▼                       │
        │  user            │            │   ┌──────────────┐ external     │
        │  workoutsession  │            │   │ Anthropic LLM│  API         │
        │  workoutexercise │            │   │ (schema-forced)             │
        └──────────────────┘            │   └──────────────┘              │
                                        │         │ REDIS_URL (cache)     │
                                        └─────────┼───────────────────────┘
                                                  ▼ reads cached context
                                       ┌────────────────────────────┐
                                       │          REDIS :6379        │
                                       │  coach:refresh:queue        │
                                       │  coach:refresh:done:{id}    │
                                       │  coach:context:current      │
                                       └──────────────▲──────────────┘
                                                      │ BRPOP / SET NX EX
                                       ┌──────────────┴──────────────┐
                                       │  REFRESH WORKER (scripts/)   │
                                       │  async · Semaphore · retries │
                                       │  idempotent · compose profile│
                                       └──────────────┬───────────────┘
                                                      ▼ GET /exercises
                                               EXERCISE SERVICE
```

### Ownership & boundaries

- **Exercise Service owns all persistence** (SQLite): catalog, users, and workout
  history. It is the sole auth issuer and the only writer to the database.
- **Coach Service owns no persistent data.** It reads the catalog and recent
  history strictly over HTTP, calls the LLM (or fallback), and returns a plan.
- **Redis is a cache/queue, never a source of truth.** If the cached context is
  absent, the coach reads live over HTTP — Redis is never required for correctness.
- **The Refresh Worker** is the only queue consumer; it rebuilds the cached
  catalog snapshot. It is opt-in via the `worker` compose profile.
- **JWT_SECRET is shared** so the coach can verify tokens the exercise service
  issues — but only the exercise service mints them.

## Persistence

The exercise service migrated from an in-memory dict to **SQLModel/SQLite**.
Pydantic API schemas (with their validators) are kept separate from the SQLModel
tables, so the EX1 validation contract is unchanged. A lifespan hook creates the
tables and seeds demo users, a 16-exercise catalog, and two recent chest/push
sessions on startup.

## Auth & security

- **Hashed credentials** — bcrypt; only `hashed_password` is stored.
- **JWT** — OAuth2 password flow at `POST /auth/token` (HS256, 30-min expiry).
- **Scopes / roles** — `exercises:write`, `history:read`, `history:write`,
  `coach:use`. `admin` holds all; `athlete` holds history + coach.
- **Protected writes** — `POST/PUT/DELETE /exercises` need `exercises:write`;
  GET stays public (EX1 behavior preserved).
- **Cross-service** — the coach verifies the same JWT and requires `coach:use`.

### Registration & roles

- **`POST /auth/register`** (username + password) creates an **athlete** account.
  Role and scopes are forced server-side — clients cannot self-register as admin
  even if they smuggle a `role`/`scopes` field. Passwords are validated by a
  single backend rule (`validate_password_strength`, min 8 chars) and stored
  hashed; usernames must be unique (`409` on conflict). The UI auto-logs-in after
  a successful registration.
- **Admin** is **seeded only** (`admin` / `admin123`); there is no UI path to
  create one. A demo `athlete` / `athlete123` is also seeded.
- **Role capabilities:**

  | | athlete | admin |
  |---|---|---|
  | log in / browse exercises / generate plans | ✓ | ✓ |
  | create + view **own** workout history | ✓ | ✓ |
  | create / update / delete exercises | ✗ (403) | ✓ |
  | view **all** workout history | ✗ | ✓ |

- **Per-user history ownership** — each `WorkoutSession` records an `owner`
  (the JWT subject). `GET /sessions` returns only the caller's sessions for
  athletes and everyone's for admins; reading or deleting another user's session
  returns `404`. The backend is authoritative; the Streamlit UI additionally
  hides admin-only controls (the **Add Exercise** tab renders only when the token
  carries `exercises:write`).

Tested: hashing, login, **expired token → 401**, **missing scope → 403**, role
enforcement, registration (athlete-only, duplicate `409`, weak password `422`,
no self-admin), and per-user history isolation (athlete sees own, admin sees all).

## Workout history & personalization

Two lightweight tables (`WorkoutSession`, `WorkoutExercise`) record what was
trained. A pure-Python context builder turns recent sessions into deterministic
signals — recently-used exercises, recency-weighted volume per muscle, and
human-readable insights ("You trained chest heavily in recent sessions"). These
feed **both** planners, so personalization works with or without the LLM:

- **Fallback planner** deweights recently-used exercises and rebalances toward
  under-trained muscles — fully deterministic.
- **LLM planner** receives the same signals in its prompt.

## LLM integration & bounding (the enhancement)

The **enhancement is TrainFlow Coach itself** — AI-powered, history-aware,
structured workout planning over the catalog. The LLM is central but bounded:

1. The catalog (ids + metadata) is injected into the prompt.
2. The model returns **schema-forced JSON** (`messages.parse` with a Pydantic
   `output_format`).
3. A **catalog-only validation/repair layer** drops any item whose `exercise_id`
   is not in the catalog or violates the equipment/avoid constraints, and tops up
   empty days from the deterministic fallback — so the model can never invent an
   exercise and the response is always complete.
4. With no LLM configured, the coach uses the **fallback planner** automatically.
   **Tests never call a real LLM** — the client is injected and a fake returns
   canned (including deliberately invalid) output.

### Pluggable providers

The LLM is reached through an injected `LLMClient` protocol
(`generate_plan(system, user) -> dict`), so the provider is swappable without
touching the planner or validation. `COACH_PROVIDER` selects it:

| Provider | Cost | Notes |
|---|---|---|
| `auto` (default) | — | Gemini if `GEMINI_API_KEY` is set, else Anthropic if `ANTHROPIC_API_KEY` is set, else fallback |
| `gemini` | **free cloud tier** | Google Gemini REST API (JSON mode); default `gemini-2.0-flash`; key from aistudio.google.com (no billing) |
| `anthropic` | paid | `messages.parse` structured output; default `claude-opus-4-8` |
| `fallback` | free | Deterministic planner only |

Because the catalog-only validation/repair layer runs regardless of provider, a
smaller free model is safe — bad or hallucinated picks are dropped and topped up
from the fallback.

## Redis job / idempotency model

- Queue: Redis list `coach:refresh:queue`.
- Idempotency: `SET coach:refresh:done:{job_id} 1 NX EX <ttl>` — only the first
  claimant processes a job; replays are no-ops. A permanently failing job
  releases its claim so a re-enqueue can retry.
- Result cache: `coach:context:current` (catalog snapshot + aggregates).

The worker (`scripts/refresh.py`) is async with **bounded concurrency**
(`asyncio.Semaphore`), **retries with exponential backoff**, and `once`/`watch`
modes. Its tests use **fakeredis** and are marked `@pytest.mark.anyio`.

## Requirement checklist

| Requirement | Where |
|---|---|
| One repo, cooperating services | `services/*`, `interface/`, `scripts/`, `compose.yaml` |
| FastAPI backend | `services/exercise-service`, `services/coach-service` |
| Persistence (SQLModel/SQLite) | `exercise-service/app/db.py`, `models.py` |
| Streamlit interface | `interface/app.py` (+ Coach tab) |
| compose.yaml | `compose.yaml` |
| Redis + async worker/refresh | `scripts/refresh.py` + redis service |
| Bounded concurrency, retries, idempotency | `scripts/refresh.py` |
| `pytest.mark.anyio` test | `scripts/tests/test_refresh.py` |
| Hashed credentials | `exercise-service/app/auth.py` (bcrypt) |
| JWT-protected route | `/exercises` writes, `/sessions`, coach `/plan` |
| Role / scope checks | `auth.py` scopes; `seed.py` roles |
| Expired-token test | `tests/test_auth.py::test_expired_token_is_rejected` |
| Missing-scope test | `test_auth.py` + `coach tests/test_api.py` |
| Enhancement + automated tests | TrainFlow Coach; `coach-service/tests/*` |
| Local demo script | `scripts/demo.sh` |
| docs/EX3-notes.md | this file |
| docs/runbooks/compose.md | runbook |

## Running the tests

```bash
cd services/exercise-service && uv run pytest      # catalog, auth, registration, history ownership
cd services/coach-service    && uv run pytest      # planner, context, providers, validation, auth
cd scripts                   && uv run pytest      # refresh worker (anyio + fakeredis)
cd interface                 && uv run pytest      # filters, export, coach + permissions helpers
```
