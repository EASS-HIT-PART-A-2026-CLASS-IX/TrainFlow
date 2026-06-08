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
coach uses its deterministic fallback planner. To enable the LLM planner, set
`ANTHROPIC_API_KEY` in `.env`.

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

## 3. Use it

1. Open the interface. In the sidebar, **Register** a new athlete account
   (username + password), or log in. The demo `athlete` / `athlete123` and
   `admin` / `admin123` accounts also work.
2. **Coach** tab → choose a goal/schedule → **Generate plan**. The plan is
   personalized from your workout history and shows whether it came from the LLM
   or the fallback planner.
3. **History** tab → log and view your own sessions. Athletes see only their own
   history; admins see everyone's. The **Add Exercise** tab only appears for
   admins.

## 4. Optional — free cloud LLM (Gemini)

By default the coach uses the deterministic fallback planner. For a free,
zero-billing LLM, use Google Gemini:

```bash
# 1. Get a free API key (no billing) at https://aistudio.google.com/apikey

# 2. Add it to .env
echo "GEMINI_API_KEY=your-key-here" >> .env

# 3. Restart the coach
docker compose up -d --build coach-service
```

In `auto` mode the coach uses Gemini automatically when `GEMINI_API_KEY` is set,
so generated plans now show `generated_by: "llm"`. If Gemini is unreachable or
rate-limited, the coach transparently falls back to the deterministic planner.
Override the model with `GEMINI_MODEL` in `.env` (default `gemini-2.0-flash`).

To use Anthropic Claude instead, set `ANTHROPIC_API_KEY` (and optionally
`COACH_PROVIDER=anthropic`).

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
- **Coach always says "fallback"** — expected without `ANTHROPIC_API_KEY`. Set it
  in `.env` and `docker compose up -d --build coach-service`.
- **Reset all data** — `docker compose down -v` drops the `trainflow-db` volume.
