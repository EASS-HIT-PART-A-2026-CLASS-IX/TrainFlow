import fakeredis.aioredis
import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()
