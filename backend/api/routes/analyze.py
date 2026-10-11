from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from backend.core.security import get_current_claims
from backend.db.session import AsyncSessionLocal
from backend.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from backend.services.rag_classifier import RAGClassifier
from backend.tasks.classify_task import classify_message_task
from scam_detector.classifier import classify_message

router = APIRouter(tags=["analyze"])


async def _classify_with_rag_or_fallback(message: str, model_name: str | None = None):
    try:
        async with AsyncSessionLocal() as db:
            classifier = RAGClassifier(db)
            result = await classifier.classify_with_context(message, model_name=model_name, top_k=5)
            if result is not None:
                return result
    except Exception:
        pass

    return classify_message(message, model_name=model_name)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_message(payload: AnalyzeRequest, claims: dict = Depends(get_current_claims)):
    try:
        task = classify_message_task.delay(payload.message, payload.model_name)
        return AnalyzeResponse(
            task_id=str(task.id),
            status="queued",
            message="Analysis request accepted and queued for processing.",
        )
    except Exception:
        result = await _classify_with_rag_or_fallback(payload.message, payload.model_name)
        if result is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Analysis failed")

        return AnalyzeResponse(
            task_id="local",
            status="completed",
            message="Analysis completed using the retrieval-augmented flow because the background queue is unavailable.",
            result={
                "is_scam": result.is_scam,
                "scam_type": result.scam_type,
                "confidence": float(result.confidence),
                "reply": result.reply,
                "indicators": result.indicators,
                "recommended_action": result.recommended_action,
            },
        )


@router.get("/analyze/{task_id}")
async def get_analysis_status(task_id: str, claims: dict = Depends(get_current_claims)):
    result = classify_message_task.AsyncResult(task_id)
    if result.state in {"PENDING", "STARTED", "RETRY"}:
        return {"task_id": task_id, "status": result.state}
    if result.state == "FAILURE":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Task failed")
    return {"task_id": task_id, "status": result.state, "result": result.result}
