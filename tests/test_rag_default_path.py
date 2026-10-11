from types import SimpleNamespace

import pytest

from backend.api.routes.analyze import analyze_message
from backend.schemas.analyze import AnalyzeRequest


@pytest.mark.asyncio
async def test_analyze_uses_rag_when_available(monkeypatch):
    class DummyAsyncSession:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummyRAGClassifier:
        def __init__(self, db_session):
            self.db_session = db_session

        async def classify_with_context(self, message, model_name=None, top_k=5):
            return SimpleNamespace(
                is_scam="Scam",
                scam_type="Phishing",
                confidence=0.99,
                reply="RAG answer",
                indicators=["retrieved context"],
                recommended_action="block",
            )

    def fail_delay(*args, **kwargs):
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr("backend.api.routes.analyze.classify_message_task.delay", fail_delay)
    monkeypatch.setattr("backend.api.routes.analyze.AsyncSessionLocal", DummyAsyncSession)
    monkeypatch.setattr("backend.api.routes.analyze.RAGClassifier", DummyRAGClassifier)
    monkeypatch.setattr(
        "backend.api.routes.analyze.classify_message",
        lambda *args, **kwargs: pytest.fail("plain classifier should not be called when RAG is available"),
    )

    response = await analyze_message(
        AnalyzeRequest(message="Claim your prize now", model_name="gemini-3.1-flash-lite"),
        {"sub": "admin", "role": "admin"},
    )

    assert response.status == "completed"
    assert response.result["is_scam"] == "Scam"
    assert response.result["scam_type"] == "Phishing"
