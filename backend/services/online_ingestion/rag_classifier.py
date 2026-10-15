from __future__ import annotations

import json

from scam_detector.classifier import classify_message
from scam_detector.prompts import SYSTEM_PROMPT
from scam_detector.response_parser import extract_text_from_response, parse_model_output
from scam_detector.schemas import ScamDetector
from scam_detector.llm_client import get_llm
from backend.core.monitoring import track_retrieval_request
from backend.services.online_ingestion.retrieval_service import RetrievalService


class RAGClassifier:
    def __init__(self, db_session):
        self.db_session = db_session
        self.retrieval = RetrievalService(db_session)

    async def classify_with_context(self, message: str, model_name: str | None = None, top_k: int = 5):
        try:
            matches = await self.retrieval.search_similar(message, limit=top_k)
            retrieved_context = [
                {"text": item.text, "metadata": item.metadata or {}} for item in matches
            ]
        except Exception:
            matches = []
            retrieved_context = []

        track_retrieval_request(len(matches))

        if not retrieved_context:
            return None

        fallback = classify_message(message, model_name=model_name)
        if fallback is None:
            fallback = ScamDetector(
                is_scam="Unknown",
                scam_type="Other",
                confidence=0.0,
                reply="Classification unavailable.",
                indicators=[],
                recommended_action="verify",
            )

        try:
            parser = __import__("langchain_core.output_parsers", fromlist=["PydanticOutputParser"]).PydanticOutputParser(pydantic_object=ScamDetector)
            fmt = parser.get_format_instructions()
            prompt = (
                f"{SYSTEM_PROMPT}\n\n"
                f"Relevant retrieved examples:\n{json.dumps(retrieved_context, ensure_ascii=False, indent=2)}\n\n"
                f"Format instructions:\n{fmt}\n\nMessage:\n{message}\n"
            )
            raw = get_llm(model_name).invoke(prompt)
            inner = extract_text_from_response(raw)
            parsed = parse_model_output(parser, inner)
            return parsed
        except Exception:
            return fallback
