"""Async, Redis-backed refresh worker for TrainFlow.

Rebuilds a cached "coach context" snapshot — a denormalized view of the exercise
catalog plus simple aggregates — so the coach-service can keep its prompts small
and fast. Demonstrates the EX3 requirements:

- bounded concurrency (asyncio.Semaphore)
- retries with exponential backoff for transient failures
- Redis-backed idempotency (SET NX), so replaying a job is a no-op

The worker primitives accept an injected Redis client and fetch callable, so the
test suite drives them with fakeredis and never needs a real Redis or network.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from collections import Counter
from uuid import uuid4

QUEUE_KEY = "coach:refresh:queue"
CONTEXT_KEY = "coach:context:current"
DONE_KEY_PREFIX = "coach:refresh:done:"

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
EXERCISE_API_URL = os.getenv("EXERCISE_API_URL", "http://localhost:8000")


def _done_key(job_id: str) -> str:
    return f"{DONE_KEY_PREFIX}{job_id}"


class NonRetryableError(Exception):
    """A failure that should not be retried (e.g. a 4xx response)."""


class RefreshWorker:
    def __init__(
        self,
        redis,
        fetch_snapshot,
        *,
        max_concurrency: int = 4,
        max_attempts: int = 3,
        idempotency_ttl: int = 3600,
        base_delay: float = 0.05,
    ) -> None:
        self._redis = redis
        self._fetch = fetch_snapshot
        self._sem = asyncio.Semaphore(max_concurrency)
        self._max_attempts = max_attempts
        self._ttl = idempotency_ttl
        self._base_delay = base_delay
        # Observability for tests/metrics.
        self._inflight = 0
        self.max_inflight = 0

    async def enqueue(self, job_id: str | None = None, job_type: str = "refresh_catalog") -> str:
        job_id = job_id or uuid4().hex
        await self._redis.rpush(QUEUE_KEY, json.dumps({"job_id": job_id, "type": job_type}))
        return job_id

    async def _claim(self, job_id: str) -> bool:
        # Idempotency gate: only the first claimant proceeds. Returns truthy on
        # success, None if the key already exists.
        return bool(await self._redis.set(_done_key(job_id), "1", nx=True, ex=self._ttl))

    async def _run_with_retries(self, job: dict) -> None:
        async with self._sem:
            self._inflight += 1
            self.max_inflight = max(self.max_inflight, self._inflight)
            try:
                attempt = 0
                while True:
                    try:
                        snapshot = await self._fetch()
                        await self._redis.set(CONTEXT_KEY, json.dumps(snapshot))
                        return
                    except NonRetryableError:
                        raise
                    except Exception:  # noqa: BLE001 - transient; retry with backoff
                        attempt += 1
                        if attempt >= self._max_attempts:
                            raise
                        await asyncio.sleep(self._base_delay * (2 ** (attempt - 1)))
            finally:
                self._inflight -= 1

    async def process_job(self, job: dict) -> str:
        job_id = job["job_id"]
        if not await self._claim(job_id):
            return "skipped"  # already processed — idempotent no-op
        try:
            await self._run_with_retries(job)
        except Exception:  # noqa: BLE001 - give up after retries
            # Release the idempotency claim so a re-enqueue can try again later.
            await self._redis.delete(_done_key(job_id))
            return "dead"
        return "done"

    async def drain_once(self) -> Counter:
        """Pop everything currently queued and process it with bounded
        concurrency, then return. Used by tests and CI."""
        jobs: list[dict] = []
        while True:
            raw = await self._redis.lpop(QUEUE_KEY)
            if raw is None:
                break
            jobs.append(json.loads(raw))
        results = await asyncio.gather(*(self.process_job(job) for job in jobs))
        return Counter(results)

    async def watch(self, poll_timeout: int = 1, stop_after: int | None = None) -> None:
        """Block on the queue and process jobs as they arrive. stop_after bounds
        the loop for tests; production runs unbounded."""
        tasks: set[asyncio.Task] = set()
        seen = 0
        while True:
            result = await self._redis.brpop([QUEUE_KEY], timeout=poll_timeout)
            if result is None:
                if stop_after is not None:
                    break
                continue
            _, raw = result
            task = asyncio.create_task(self.process_job(json.loads(raw)))
            tasks.add(task)
            task.add_done_callback(tasks.discard)
            seen += 1
            if stop_after is not None and seen >= stop_after:
                break
        if tasks:
            await asyncio.gather(*tasks)


# ---------------------------------------------------------------------------
# Real snapshot builder (used by the CLI; tests inject a fake).
# ---------------------------------------------------------------------------
async def fetch_catalog_snapshot(base_url: str = EXERCISE_API_URL) -> dict:
    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{base_url}/exercises")
    if 400 <= response.status_code < 500:
        raise NonRetryableError(f"catalog request failed: {response.status_code}")
    response.raise_for_status()
    catalog = response.json()

    by_muscle: dict[str, int] = {}
    by_equipment: dict[str, int] = {}
    for exercise in catalog:
        for muscle in exercise.get("primary_muscles", []):
            by_muscle[muscle] = by_muscle.get(muscle, 0) + 1
        equipment = exercise.get("equipment")
        if equipment:
            by_equipment[equipment] = by_equipment.get(equipment, 0) + 1

    return {
        "generated_at": time.time(),
        "exercise_count": len(catalog),
        "by_muscle": by_muscle,
        "by_equipment": by_equipment,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
async def _amain(args: argparse.Namespace) -> None:
    import redis.asyncio as aioredis

    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    worker = RefreshWorker(redis_client, lambda: fetch_catalog_snapshot(args.exercise_url))
    try:
        if args.enqueue:
            job_id = await worker.enqueue(job_id=args.job_id)
            print(f"enqueued job {job_id}")
        if args.mode == "once":
            results = await worker.drain_once()
            print("drained:", dict(results))
        elif args.mode == "watch":
            print("watching queue (ctrl-c to stop)...")
            await worker.watch()
    finally:
        await redis_client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="TrainFlow refresh worker")
    parser.add_argument("mode", choices=["once", "watch"], help="drain once and exit, or watch")
    parser.add_argument("--enqueue", action="store_true", help="enqueue a refresh job first")
    parser.add_argument("--job-id", default=None, help="fixed job id (for idempotency demos)")
    parser.add_argument("--exercise-url", default=EXERCISE_API_URL)
    asyncio.run(_amain(parser.parse_args()))


if __name__ == "__main__":
    main()
