import asyncio

from backend.api import app as app_module


def test_app_bootstraps_database_on_startup(monkeypatch):
    calls = []

    async def fake_create_all_tables():
        calls.append("called")

    monkeypatch.setattr(app_module, "create_all_tables", fake_create_all_tables)

    async def run_startups():
        for startup in app_module.app.router.on_startup:
            await startup()

    asyncio.run(run_startups())

    assert calls == ["called"]
