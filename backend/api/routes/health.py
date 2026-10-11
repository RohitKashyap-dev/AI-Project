import asyncio

import redis
from fastapi import APIRouter
from sqlalchemy import text

from backend.core.config import settings
from backend.db.session import AsyncSessionLocal

router = APIRouter(tags=["health"])


async def check_database_status() -> dict:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return {"status": "ok", "details": "database reachable"}
    except Exception as exc:  # pragma: no cover - exercised in production runtime
        return {"status": "degraded", "details": str(exc)}


def check_redis_status() -> dict:
    try:
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        ping_ok = bool(client.ping())
        if ping_ok:
            return {"status": "ok", "details": "redis reachable"}
        return {"status": "degraded", "details": "redis ping failed"}
    except Exception as exc:  # pragma: no cover - exercised in production runtime
        return {"status": "degraded", "details": str(exc)}


@router.get("/health")
async def health_check():
    database = await check_database_status()
    redis_status = check_redis_status()

    overall_status = "ok" if database["status"] == "ok" and redis_status["status"] == "ok" else "degraded"

    return {
        "status": overall_status,
        "service": "scam-detector-api",
        "environment": settings.ENVIRONMENT,
        "database": database,
        "redis": redis_status,
    }
