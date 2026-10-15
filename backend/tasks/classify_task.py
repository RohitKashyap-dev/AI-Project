from celery import shared_task

from backend.db.session import AsyncSessionLocal
from backend.services.online_ingestion.rag_classifier import RAGClassifier


@shared_task(name="classify_message_task")
def classify_message_task(message: str, model_name: str | None = None):
    import asyncio

    async def _run():
        async with AsyncSessionLocal() as db:
            classifier = RAGClassifier(db)
            result = await classifier.classify_with_context(message, model_name=model_name, top_k=5)
            return {
                "is_scam": result.is_scam,
                "scam_type": result.scam_type,
                "confidence": float(result.confidence),
                "reply": result.reply,
                "indicators": result.indicators,
                "recommended_action": result.recommended_action,
            }

    return asyncio.run(_run())
