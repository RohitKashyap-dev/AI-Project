from backend.api.routes import health


def test_health_reports_database_and_redis_status(monkeypatch):
    monkeypatch.setattr(
        health,
        "check_database_status",
        lambda: {"status": "ok", "details": "database healthy"},
    )
    monkeypatch.setattr(
        health,
        "check_redis_status",
        lambda: {"status": "ok", "details": "redis healthy"},
    )

    payload = health.health_check()

    assert payload["status"] == "ok"
    assert payload["database"]["status"] == "ok"
    assert payload["redis"]["status"] == "ok"
    assert payload["service"] == "scam-detector-api"
