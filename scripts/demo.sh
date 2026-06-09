#!/usr/bin/env bash
# End-to-end local demo of TrainFlow Coach.
#
# Brings up the stack, demonstrates auth + scope enforcement, logs a workout,
# generates a personalized plan (fallback mode by default — no API key needed),
# and shows the Redis-backed idempotent refresh worker.
#
# Usage:  ./scripts/demo.sh
set -euo pipefail

EXERCISE_URL="http://localhost:8000"
COACH_URL="http://localhost:8001"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

json() { python3 -c "import sys,json; print(json.load(sys.stdin)$1)"; }
hr()   { printf '\n=== %s ===\n' "$1"; }

[ -f .env ] || cp .env.example .env

hr "Starting the stack (docker compose up --build -d)"
docker compose up --build -d

hr "Waiting for services to become healthy"
for url in "$EXERCISE_URL/" "$COACH_URL/health"; do
  for _ in $(seq 1 60); do
    if curl -sf "$url" >/dev/null 2>&1; then echo "ready: $url"; break; fi
    sleep 2
  done
done

hr "Registration: self-register a new athlete (expect 201, then 409 on duplicate)"
curl -s -o /dev/null -w "register new athlete -> %{http_code}\n" \
  -X POST "$EXERCISE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"demo_athlete","password":"password123"}'
curl -s -o /dev/null -w "register duplicate    -> %{http_code}\n" \
  -X POST "$EXERCISE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"demo_athlete","password":"password123"}'

hr "Auth: athlete logs in (history + coach scopes)"
ATHLETE_TOKEN=$(curl -sf -X POST "$EXERCISE_URL/auth/token" \
  -d "username=athlete&password=athlete123" | json "['access_token']")
echo "got athlete token"

hr "Scope enforcement: athlete CANNOT write to the catalog (expect 403)"
curl -s -o /dev/null -w "POST /exercises as athlete -> %{http_code}\n" \
  -X POST "$EXERCISE_URL/exercises" \
  -H "Authorization: Bearer $ATHLETE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"X","primary_muscles":["chest"],"equipment":"bodyweight","difficulty":"beginner"}'

hr "Admin can write (expect 201)"
ADMIN_TOKEN=$(curl -sf -X POST "$EXERCISE_URL/auth/token" \
  -d "username=admin&password=admin123" | json "['access_token']")
curl -s -o /dev/null -w "POST /exercises as admin  -> %{http_code}\n" \
  -X POST "$EXERCISE_URL/exercises" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo Curl","primary_muscles":["biceps"],"equipment":"dumbbell","difficulty":"beginner"}'

hr "History: log a chest-heavy session as athlete"
# exercise_id 1 is the seeded Barbell Bench Press.
curl -s -o /dev/null -w "POST /sessions -> %{http_code}\n" \
  -X POST "$EXERCISE_URL/sessions" \
  -H "Authorization: Bearer $ATHLETE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-06-06","goal":"hypertrophy","notes":"chest",
       "exercises":[{"exercise_id":1,"sets":5,"reps":8,"weight":60}]}'

hr "Coach: generate a personalized plan"
PLAN=$(curl -sf -X POST "$COACH_URL/plan" \
  -H "Authorization: Bearer $ATHLETE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"goal":"hypertrophy","experience":"intermediate","days_per_week":3,"session_minutes":60}')
echo "$PLAN" | python3 -m json.tool | head -30
echo "generated_by: $(echo "$PLAN" | json "['generated_by']")"

hr "Persistence: save the plan, then fetch it back (survives relogin)"
# The Streamlit UI does this automatically; shown here over the API.
SAVE_BODY=$(python3 -c "import sys,json; p=json.load(sys.stdin); print(json.dumps({'goal':p['goal'],'generated_by':p['generated_by'],'request':{},'plan':p}))" <<<"$PLAN")
curl -s -o /dev/null -w "POST /plans -> %{http_code}\n" \
  -X POST "$EXERCISE_URL/plans" \
  -H "Authorization: Bearer $ATHLETE_TOKEN" \
  -H "Content-Type: application/json" -d "$SAVE_BODY"
# Re-login (new token) and confirm the latest plan is still there.
ATHLETE_TOKEN2=$(curl -sf -X POST "$EXERCISE_URL/auth/token" \
  -d "username=athlete&password=athlete123" | json "['access_token']")
curl -s -o /dev/null -w "GET /plans/latest after relogin -> %{http_code}\n" \
  "$EXERCISE_URL/plans/latest" -H "Authorization: Bearer $ATHLETE_TOKEN2"
echo "(in the Streamlit UI: export the plan as PNG and 'Log Day N as a workout' from the Coach result)"

hr "Refresh worker: idempotent Redis-backed job (run the same job twice)"
docker compose run --rm refresh-worker \
  uv run --no-sync python refresh.py once --enqueue --job-id demo-1 || true
docker compose run --rm refresh-worker \
  uv run --no-sync python refresh.py once --enqueue --job-id demo-1 || true
echo "(second run reports the job as 'skipped' — idempotent)"

hr "Done"
echo "Open the interface at http://localhost:8501 (log in as athlete) and try the Coach tab."
echo "Tear down with:  docker compose down -v"
