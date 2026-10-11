import asyncio
import os
from urllib.request import urlopen


async def wait_for_service(url: str, timeout_seconds: int = 30) -> None:
    deadline = __import__("time").time() + timeout_seconds
    while __import__("time").time() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except Exception:
            await asyncio.sleep(1)
    raise RuntimeError(f"Service at {url} did not become healthy in time")


async def startup_health_checks() -> None:
    postgres_host = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    if postgres_host and postgres_port:
        await wait_for_service(f"http://{postgres_host}:{postgres_port}", timeout_seconds=20)
    if redis_url:
        import redis
        client = redis.from_url(redis_url)
        client.ping()
