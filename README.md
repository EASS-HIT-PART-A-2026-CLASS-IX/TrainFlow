# TrainFlow

TrainFlow is a local, full-stack workout-planning system built across three exercises:

- **EX1** — the Exercise backend (FastAPI).
- **EX2** — a Streamlit interface for browsing and managing exercises.
- **EX3** — **TrainFlow Coach**: an AI-powered, history-aware planner. A Coach service generates structured, schema-validated workout plans from the persisted catalog, the user's training context, and their recent workout history. The LLM is central but bounded — it may only select existing catalog exercises, output is schema-validated, tests never call a real LLM, and without an API key a deterministic fallback planner takes over.

## EX3: TrainFlow Coach (quickstart)

```bash
cp .env.example .env
docker compose up --build
```

Then open the interface at `http://localhost:8501`. Use the sidebar to **Register** a new athlete account (or log in), then try the **Coach** tab. Full details: [`docs/EX3-notes.md`](docs/EX3-notes.md) and the runbook [`docs/runbooks/compose.md`](docs/runbooks/compose.md). A scripted end-to-end demo lives at [`scripts/demo.sh`](scripts/demo.sh).

### Accounts & roles

| Account | How to get it | Role | Can |
|---|---|---|---|
| **admin** | seeded: `admin` / `admin123` | admin | everything an athlete can, **plus** create/update/delete exercises and view all workout history |
| **athlete** | **self-register** in the UI (Register screen) | athlete | log in, browse exercises, generate coach plans, and create/view **their own** workout history |

Athletes **cannot** manage the exercise catalog or other users — those controls are hidden in the UI and rejected by the backend (the backend is authoritative). Self-registration always creates an athlete; admin is seeded only. A demo `athlete` / `athlete123` account is also seeded for convenience.

The EX1/EX2 backend now uses **SQLite/SQLModel** persistence and **JWT auth** (hashed credentials, scoped writes). The sections below describe the original EX1/EX2 single-service workflow, which still applies.

## Design & Development Approach

This project was developed with a focus on clean system design, controlled scope, and iterative refinement.

The initial step was to define a simple but extensible domain. An Exercise resource was chosen as the core entity, representing the definition of a movement (e.g., Bench Press, Squat). This aligns well with the assignment requirement of building a single, well-defined resource while also serving as a strong foundation for future extensions such as workout planning and recommendation features.

### Modeling Decisions

Several design choices were made to ensure data consistency and clarity:

- Enums over free text were used for muscle groups, equipment, and difficulty to prevent invalid or inconsistent inputs.
- Primary and secondary muscle groups were modeled separately to reflect real-world exercise mechanics and allow more expressive queries in the future.
- Validation rules were added at both the field and model level, including:
  - rejecting empty or whitespace-only names
  - enforcing at least one primary muscle
  - preventing overlap between primary and secondary muscle groups
  - validating media URLs when provided

One example of iterative refinement was the muscle taxonomy: an initial generic "legs" category was replaced with more specific "quadriceps" and "hamstrings" values to avoid mixed granularity and improve consistency.

### Architecture

The project follows a simple separation of concerns:

- models define the data schema and validation rules
- repository handles storage and data access
- routes define the API layer and HTTP behavior

This structure keeps responsibilities clear and allows future changes (e.g., replacing in-memory storage with a database) without affecting the API layer.

### Development Workflow

Development was done iteratively, treating each change as a small, testable step. AI tools were used as a coding assistant to accelerate implementation, but all core decisions — including data modeling, validation rules, API design, and test coverage — were defined and reviewed manually.

Rather than generating the entire project in one step, the system was built and refined in stages:

- defining the data model and constraints
- implementing CRUD behavior
- adding validation and edge-case handling
- expanding test coverage
- refining naming and consistency

All generated code was reviewed and adjusted to ensure correctness, clarity, and alignment with the intended design.

### Future Direction

This repository is structured as the starting point of a larger TrainFlow monorepo. In future exercises, it can be extended with:

- a Workout service for composing exercise plans
- additional services such as recommendation or analytics

By keeping the current implementation focused and well-structured, it can be easily integrated into a broader multi-service architecture.

## Project Structure

- `README.md` - TrainFlow repository overview
- `docs/` - product and roadmap documentation
- `services/exercise-service/` - FastAPI Exercise Catalog backend (EX1)
  - `app/main.py` - FastAPI application entry point
  - `app/models.py` - Pydantic models and enums
  - `app/repository.py` - in-memory repository for exercises
  - `app/routes.py` - API routes for CRUD operations
  - `tests/test_exercises.py` - pytest test suite
  - `pyproject.toml` - Exercise service dependencies
- `interface/` - Streamlit interface (EX2)
  - `app.py` - Streamlit entrypoint
  - `client.py` - HTTP client wrapping the backend
  - `filters.py` - client-side filter logic
  - `export.py` - PNG reference sheet generation
  - `tests/` - pytest tests for filter and export logic
  - `pyproject.toml` - interface dependencies

## EX2: Running the Interface

The interface requires the backend to be running first. Open two terminals:

**Terminal 1 — start the backend:**
```bash
cd services/exercise-service
uv run uvicorn app.main:app --reload
```

**Terminal 2 — start the interface:**
```bash
cd interface
uv run streamlit run app.py
```

The interface opens at `http://localhost:8501`.

**What you can do in the interface:**

- **Browse Exercises** tab: view all exercises in a table, filter by muscle group, equipment, or difficulty using the sidebar, and export the visible exercises as a PNG reference sheet.
- **Add Exercise** tab: fill in the form to add a new exercise; client-side validation runs before the request is sent.

> Note: as of EX3 the backend persists exercises in SQLite, and write operations (Add Exercise) require logging in as a user with the `exercises:write` scope (e.g. `admin` / `admin123`).

## EX1: Running the API Directly

```bash
cd services/exercise-service
uv sync --dev
uv run uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

Interactive docs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Run the Tests

Each component has its own suite:
```bash
cd services/exercise-service && uv run pytest   # catalog, auth, history
cd services/coach-service    && uv run pytest   # planner, context, fake-LLM, auth
cd scripts                   && uv run pytest   # refresh worker (anyio + fakeredis)
cd interface                 && uv run pytest   # filters, export, coach helpers
```

## Available Endpoints

- `POST /exercises` - create an exercise, returns `201 Created`
- `GET /exercises` - list all exercises
- `GET /exercises/{id}` - get one exercise by ID, returns `404 Not Found` if the exercise does not exist
- `PUT /exercises/{id}` - fully replace an existing exercise, returns `404 Not Found` if the exercise does not exist. This endpoint performs a full replacement of the exercise object. All fields must be provided.
- `DELETE /exercises/{id}` - delete an exercise, returns `204 No Content`, or `404 Not Found` if the exercise does not exist

## Example Request Body

```json
{
  "name": "Squat",
  "primary_muscles": ["quadriceps"],
  "secondary_muscles": ["glutes", "hamstrings"],
  "equipment": "barbell",
  "difficulty": "beginner",
  "instructions": "Keep your chest up and drive through your feet.",
  "media_url": "https://example.com/squat"
}
```

## Notes

- IDs are generated automatically by the database.
- As of EX3, data is persisted in SQLite (`DATABASE_URL`, default `sqlite:///./trainflow.db`); the catalog and demo users/history are seeded on first startup.
- `POST` / `PUT` / `DELETE /exercises` require a JWT with the `exercises:write` scope (`POST /auth/token`); `GET` endpoints remain public.
- Validation is handled with FastAPI and Pydantic, including enum checks, blank-name rejection, and muscle overlap rules.
