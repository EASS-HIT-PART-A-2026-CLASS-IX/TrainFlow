import asyncio
import json

import pytest

from refresh import CONTEXT_KEY, NonRetryableError, RefreshWorker, _done_key

pytestmark = pytest.mark.anyio


def _snapshot_fetcher(counter: list[int]):
    async def fetch():
        counter[0] += 1
        return {"exercise_count": 1, "by_muscle": {"chest": 1}}

    return fetch


async def test_processing_is_idempotent(redis):
    calls = [0]
    worker = RefreshWorker(redis, _snapshot_fetcher(calls))
    job = {"job_id": "abc", "type": "refresh_catalog"}

    first = await worker.process_job(job)
    second = await worker.process_job(job)

    assert first == "done"
    assert second == "skipped"
    # The work ran exactly once despite two identical jobs.
    assert calls[0] == 1
    assert json.loads(await redis.get(CONTEXT_KEY))["exercise_count"] == 1


async def test_drain_once_processes_each_job_once(redis):
    calls = [0]
    worker = RefreshWorker(redis, _snapshot_fetcher(calls))
    await worker.enqueue(job_id="j1")
    await worker.enqueue(job_id="j2")
    await worker.enqueue(job_id="j1")  # duplicate id

    results = await worker.drain_once()

    assert results["done"] == 2
    assert results["skipped"] == 1
    assert calls[0] == 2


async def test_bounded_concurrency(redis):
    inflight = [0]
    peak = [0]

    async def slow_fetch():
        inflight[0] += 1
        peak[0] = max(peak[0], inflight[0])
        await asyncio.sleep(0.02)
        inflight[0] -= 1
        return {"ok": True}

    worker = RefreshWorker(redis, slow_fetch, max_concurrency=2)
    jobs = [{"job_id": f"job-{i}", "type": "refresh_catalog"} for i in range(8)]

    await asyncio.gather(*(worker.process_job(j) for j in jobs))

    assert peak[0] <= 2
    assert worker.max_inflight <= 2


async def test_retries_then_succeeds(redis):
    attempts = [0]

    async def flaky_fetch():
        attempts[0] += 1
        if attempts[0] < 3:
            raise ConnectionError("transient")
        return {"ok": True}

    worker = RefreshWorker(redis, flaky_fetch, max_attempts=3, base_delay=0.0)
    result = await worker.process_job({"job_id": "retry", "type": "refresh_catalog"})

    assert result == "done"
    assert attempts[0] == 3


async def test_permanent_failure_is_marked_dead_and_releases_claim(redis):
    async def always_fails():
        raise RuntimeError("nope")

    worker = RefreshWorker(redis, always_fails, max_attempts=2, base_delay=0.0)
    result = await worker.process_job({"job_id": "dead", "type": "refresh_catalog"})

    assert result == "dead"
    # The idempotency claim was released so a future re-enqueue can retry.
    assert await redis.get(_done_key("dead")) is None


async def test_non_retryable_fails_fast(redis):
    attempts = [0]

    async def four_oh_four():
        attempts[0] += 1
        raise NonRetryableError("400")

    worker = RefreshWorker(redis, four_oh_four, max_attempts=5, base_delay=0.0)
    result = await worker.process_job({"job_id": "nr", "type": "refresh_catalog"})

    assert result == "dead"
    assert attempts[0] == 1  # no retries on a non-retryable error


async def test_watch_drains_then_stops(redis):
    calls = [0]
    worker = RefreshWorker(redis, _snapshot_fetcher(calls))
    await worker.enqueue(job_id="w1")
    await worker.enqueue(job_id="w2")

    await worker.watch(poll_timeout=1, stop_after=2)

    assert calls[0] == 2
