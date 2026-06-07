# TrainFlow Roadmap

TrainFlow is a monorepo for a local, full-stack workout-planning system.

## Delivered

- **Exercise backend** (FastAPI) — catalog CRUD, now persisted in SQLite/SQLModel
  with JWT auth (hashed credentials, scoped writes).
- **Streamlit interface** — browse/filter/add exercises, login, and a Coach tab.
- **Workout history** — lightweight `WorkoutSession` / `WorkoutExercise` model.
- **Coach service** (FastAPI) — AI-powered, history-aware, schema-validated
  workout planning with a deterministic fallback planner.
- **Redis refresh worker** — async, idempotent, bounded-concurrency context cache.
- **Docker Compose** — exercise-service, coach-service, redis, interface, worker.

See [EX3-notes.md](EX3-notes.md) for the EX3 design and requirement mapping.

## Possible future work

- Persist generated plans and richer history analytics.
- Per-user data isolation beyond role checks.
- Asymmetric (RS256) cross-service token verification.
