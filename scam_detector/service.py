from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from scam_detector.classifier import classify_message
from scam_detector.schemas import ScamDetector


class AnalyzeRequest(BaseModel):
    message: str = Field(min_length=1)
    model_name: Optional[str] = None


class AnalyzeResponse(BaseModel):
    result: ScamDetector
    analyzed_at: str


def analyze_message(message: str, model_name: Optional[str] = None) -> AnalyzeResponse:
    parsed = classify_message(message, model_name=model_name)
    if parsed is None:
        raise ValueError("Failed to classify message")
    return AnalyzeResponse(result=parsed, analyzed_at=datetime.now(timezone.utc).isoformat())
