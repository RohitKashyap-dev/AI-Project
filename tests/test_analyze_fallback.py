from types import SimpleNamespace

import pytest

from backend.api.routes.analyze import analyze_message
from backend.schemas.analyze import AnalyzeRequest


@pytest.mark.asyncio
async def test_analyze_falls_back_to_local_classification_when_celery_is_unavailable(monkeypatch):
    def fail_delay(*args, **kwargs):
        raise ConnectionError("[Errno 61] Connection refused")

    monkeypatch.setattr("backend.api.routes.analyze.classify_message_task.delay", fail_delay)

    monkeypatch.setattr(
        "backend.api.routes.analyze.classify_message",
        lambda message, model_name=None: SimpleNamespace(
            is_scam="Not Scam",
            scam_type="None",
            confidence=0.92,
            reply="Looks safe.",
            indicators=[],
            recommended_action="Continue",
        ),
    )

    response = await analyze_message(
        AnalyzeRequest(message="Hi team, lunch is at noon.", model_name="gemini-3.1-flash-lite"),
        {"sub": "admin", "role": "admin"},
    )

    assert response["status"] == "completed"
    assert response["result"]["is_scam"] == "Not Scam"
    assert response["result"]["confidence"] == 0.92
