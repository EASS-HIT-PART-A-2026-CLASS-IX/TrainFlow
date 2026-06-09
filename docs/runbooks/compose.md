# Runbook — Docker Compose

Bring up the full TrainFlow Coach stack (exercise-service, coach-service, redis,
interface) with one command.

## Prerequisites

- Docker Engine + Docker Compose v2 (`docker compose version`)
- Ports free on the host: `8000`, `8001`, `8501`, `6379`

## 1. Configure environment

```bash
cp .env.example .env
```

Defaults work out of the box. The app runs **fully without an API key** — the
coach uses its deterministic fallback planner. To enable the real Gemini LLM, set
these in `.env` (compose reads `.env` automatically) and rebuild coach-service:

```ini
COACH_PROVIDER=gemini
GEMINI_API_KEY=<your free key from https://aistudio.google.com/apikey>
GEMINI_MODEL=gemini-2.5-flash
```

`.env` is gitignored — never commit it. Anthropic is optional (`ANTHROPIC_API_KEY`).

## 2. Start the stack

```bash
docker compose up --build
```

Wait for `exercise-service` and `coach-service` to report healthy. On first
start, the exercise service creates the SQLite database and seeds demo users, a
catalog, and recent workout history.

| Service | URL |
|---|---|
| Interface (Streamlit) | http://localhost:8501 |
| Exercise API docs | http://localhost:8000/docs |
| Coach API docs | http://localhost:8001/docs |

Demo logins: `admin` / `admin123` (full access), `athlete` / `athlete123`
(history + coach).

### Verify health

```bash
curl -i http://localhost:8000/            # exercise-service -> 200 {"message": ...}
curl -i http://localhost:8001/health      # coach-service    -> 200 {"status":"ok","provider":"fallback"|"gemini"|"anthropic"}
docker compose ps                         # all services "healthy"
```

The coach `/health` `provider` field tells you which planner is active. Note:
this project does **not** implement rate limiting, so there are no
`X-RateLimit-*` headers to verify; health is verified via the endpoints above and
the compose healthchecks.

### Run the tests

The automated coverage is pytest (run per component; all offline — no real LLM):

```bash
cd services/exercise-service && uv run pytest   # catalog, auth, registration, history, plans
cd services/coach-service    && uv run pytest   # planner, context, providers, validation, auth
cd scripts                   && uv run pytest   # refresh worker (anyio + fakeredis)
cd interface                 && uv run pytest   # filters, export, coach/permissions/ui helpers
```

Schemathesis is **not** configured for this project — use the pytest suites
above. There is no committed CI workflow; run the suites locally.

## 3. Use it

1. Open the interface. On the polished sign-in screen, **Register** a new athlete
   account (username + password) or log in. The demo `athlete` / `athlete123` and
   `admin` / `admin123` accounts also work. After login you land on the
   **Dashboard**.
2. Use the **sidebar navigation** (Dashboard · AI Coach · Exercise Catalog ·
   Workout History · Admin Catalog for admins). On **AI Coach**, set a
   goal/schedule → **Generate plan**; the plan renders as day cards with a coach
   mode indicator (Gemini / Anthropic / built-in fallback). You can **export the
   plan as a PNG** and **log any day as a workout** straight from the result.
3. Your latest plan is **persisted per user** — log out and back in and it's
   still there (so the "Log Day" action stays available). Plans are private to
   each user.
4. **Workout History** → log and view your own sessions. Athletes see only their
   own; admins see everyone's. **Admin Catalog** (add/edit/delete exercises) is
   visible to admins only.

### Demo flow

1. Register or log in.
2. **AI Coach** → Generate plan (watch the staged "Coach is building your plan…"
   status).
3. Log out, then log back in as the same user — the latest plan is still shown.
4. **Export plan as PNG** from the Coach result.
5. **Log Day N as a workout** to push it into your history.

## 4. Optional — free cloud LLM (Gemini)

By default the coach uses the deterministic fallback planner. For a free,
zero-billing LLM, use Google Gemini:

```bash
# 1. Get a free API key (no billing) at https://aistudio.google.com/apikey

# 2. Add these to .env
#    COACH_PROVIDER=gemini
#    GEMINI_API_KEY=your-key-here
#    GEMINI_MODEL=gemini-2.5-flash

# 3. Restart the coach (env vars are only read at startup)
docker compose up -d --build coach-service
```

Generated plans then show `generated_by: "llm"`. If Gemini is unreachable,
rate-limited, or returns an unparseable response, the coach **transparently falls
back** to the deterministic planner — generation never fails. The default model
is `gemini-2.5-flash`; override via `GEMINI_MODEL`.

To use Anthropic Claude instead, set `ANTHROPIC_API_KEY` (and optionally
`COACH_PROVIDER=anthropic`). In `auto` mode Gemini is preferred when its key is
present, then Anthropic, then fallback.

## 5. Optional — the refresh worker

The async worker is opt-in via a compose profile:

```bash
docker compose --profile worker up refresh-worker
```

Run a one-shot drain with idempotency (re-running the same job is a no-op):

```bash
docker compose run --rm refresh-worker \
  uv run --no-sync python refresh.py once --enqueue --job-id demo-1
```

## 6. Teardown

```bash
docker compose down          # stop containers
docker compose down -v       # also remove the SQLite volume (fresh seed next time)
```

## Troubleshooting

- **Port already in use** — stop the conflicting process or remap the host port
  in `compose.yaml` (e.g. `"8010:8000"`).
- **Coach returns 502** — the exercise service isn't healthy yet; wait for its
  healthcheck or check `docker compose logs exercise-service`.
- **Coach always says "fallback"** — expected with no LLM key. Set
  `COACH_PROVIDER=gemini` + `GEMINI_API_KEY` (or `ANTHROPIC_API_KEY`) in `.env`
  and `docker compose up -d --build coach-service`. Check
  `docker compose logs coach-service` — a failed LLM call logs the provider and a
  redacted error, then falls back.
- **Stale SQLite schema** (e.g. after a model change, errors about missing
  columns) — delete the local database and restart so it re-creates and re-seeds:
  `docker compose down -v && docker compose up --build` (compose), or delete the
  `*.db` file for a manual run. The DB is seed-reproducible, so this is safe.
- **Redis not running** — only the opt-in refresh worker needs Redis. If you ran
  `--profile worker` without Redis, start it (`docker compose up -d redis`); the
  core app (API, coach, interface) does not require Redis.
- **Reset all data** — `docker compose down -v` drops the `trainflow-db` volume
  and the catalog/users/history/plans are re-seeded on next startup.
