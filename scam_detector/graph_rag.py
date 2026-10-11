import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from langchain_core.output_parsers import PydanticOutputParser
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from scam_detector.config import DEFAULT_DATASET_PATH, GOOGLE_API_KEY
from scam_detector.llm_client import get_llm
from scam_detector.prompts import SYSTEM_PROMPT
from scam_detector.response_parser import extract_text_from_response, parse_model_output
from scam_detector.schemas import ScamDetector


FALLBACK_EXAMPLES = [
    {
        "message_text": "Congratulations! You have won ₹50,000. Click to claim your prize.",
        "label": "Scam",
        "intent_type": "Reward_Manipulation",
    },
    {
        "message_text": "Your OTP is 123456. Share to verify your account.",
        "label": "Scam",
        "intent_type": "OTP_Fraud",
    },
    {
        "message_text": "We have restricted your UPI services. Update now.",
        "label": "Scam",
        "intent_type": "Account_Suspension",
    },
    {
        "message_text": "Reminder: Your gas cylinder booking is confirmed.",
        "label": "Not Scam",
        "intent_type": "Service_Reminder",
    },
    {
        "message_text": "Power cut scheduled from 2 PM to 4 PM tomorrow.",
        "label": "Not Scam",
        "intent_type": "Informational_Alert",
    },
]


def redact_pii(message: str) -> str:
    """Mask obvious personal identifiers before retrieval or LLM analysis."""
    if not message:
        return ""

    cleaned = message
    cleaned = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", cleaned)
    cleaned = re.sub(
        r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)\d{3}[-.\s]?\d{4}(?!\d)",
        "[PHONE]",
        cleaned,
    )
    cleaned = re.sub(r"\b(UPI|upi)\s*[:\-]?\s*\d{6,}\b", "UPI[REDACTED]", cleaned)
    cleaned = re.sub(r"\b(?:account|acct|card|bank)\s*(?:no|number|#)?\s*[:\-]?\s*\d{8,}\b", "[ACCOUNT]", cleaned, flags=re.IGNORECASE)
    return cleaned


def _build_symbolic_signals(message: str) -> Dict[str, Any]:
    text = (message or "").lower()
    signal_rules = {
        "urgency": ["act now", "immediately", "today", "urgent", "within 1 hour", "limited time", "expire"],
        "financial_request": ["pay a fee", "deposit", "claim prize", "win", "refund", "transaction", "upi", "bank account", "otp"],
        "account_alert": ["account suspended", "restricted your", "verify your account", "security alert", "bank account is under threat"],
        "phishing_link": ["click this link", "tap this link", "visit link", "tracking link"],
        "authority_impersonation": ["government", "bank", "police", "official", "courier", "amazon", "paypal"],
    }

    indicators: List[str] = []
    score = 0.0
    for name, phrases in signal_rules.items():
        if any(p in text for p in phrases):
            indicators.append(name)
            score += 0.2

    if "otp" in text or "one time password" in text:
        indicators.append("otp_request")
        score += 0.25
    if "click" in text or "link" in text:
        indicators.append("suspicious_link")
        score += 0.2
    if "congratulations" in text or "won" in text:
        indicators.append("reward_manipulation")
        score += 0.2

    risk_score = min(1.0, max(0.0, round(score, 2)))
    if risk_score >= 0.8:
        classification = "Scam"
    elif risk_score >= 0.4:
        classification = "Unknown"
    else:
        classification = "Not Scam"

    return {
        "risk_score": risk_score,
        "classification": classification,
        "indicators": sorted(set(indicators)),
    }


class GraphRAGEngine:
    def __init__(self, dataset_path: Optional[str | Path] = None):
        self.dataset_path = Path(dataset_path) if dataset_path else DEFAULT_DATASET_PATH
        self.state: Dict[str, Any] = {"users": {}, "sessions": {}, "entities": {}, "edges": []}
        self.documents: List[str] = []
        self.labels: List[str] = []
        self.intent_types: List[str] = []
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = None
        self._load_dataset()

    def _load_dataset(self):
        rows: List[Dict[str, str]] = []
        try:
            df = pd.read_csv(self.dataset_path)
            if not df.empty:
                rows = df.to_dict("records")
        except Exception:
            rows = []

        if not rows:
            rows = FALLBACK_EXAMPLES

        for row in rows:
            message = str(row.get("message_text") or "").strip()
            label = str(row.get("label") or "Not Scam").strip()
            intent = str(row.get("intent_type") or "Other").strip()
            if not message:
                continue
            self.documents.append(message)
            self.labels.append(label)
            self.intent_types.append(intent)

        if self.documents:
            self.matrix = self.vectorizer.fit_transform(self.documents)

    def _ensure_user(self, user_id: Optional[str]):
        if not user_id:
            return
        self.state["users"].setdefault(
            user_id,
            {"history": [], "risk_score": 0.0, "last_seen": datetime.now(timezone.utc).isoformat()},
        )

    def _ensure_session(self, session_id: Optional[str]):
        if not session_id:
            return
        self.state["sessions"].setdefault(
            session_id,
            {"messages": [], "risk_score": 0.0, "created_at": datetime.now(timezone.utc).isoformat()},
        )

    def _register_message(self, message: str, user_id: Optional[str] = None, session_id: Optional[str] = None):
        cleaned = redact_pii(message)
        self._ensure_user(user_id)
        self._ensure_session(session_id)
        if user_id:
            self.state["users"][user_id]["history"].append(cleaned)
            self.state["users"][user_id]["last_seen"] = datetime.now(timezone.utc).isoformat()
        if session_id:
            self.state["sessions"][session_id]["messages"].append(cleaned)
        return cleaned

    def _extract_entities(self, message: str) -> Dict[str, str]:
        text = message.lower()
        entities: Dict[str, str] = {}
        if "otp" in text:
            entities["credential"] = "OTP"
        if "prize" in text or "won" in text:
            entities["campaign"] = "Reward_Manipulation"
        if "account" in text or "suspended" in text:
            entities["account_state"] = "Account_Suspension"
        if "link" in text or "click" in text:
            entities["channel"] = "Phishing_Link"
        if "bank" in text:
            entities["institution"] = "Bank"
        return entities

    def _graph_context(self, message: str, user_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, List[str]]:
        nodes: List[str] = []
        edges: List[str] = []

        if user_id:
            nodes.append(f"user:{user_id}")
        if session_id:
            nodes.append(f"session:{session_id}")

        for key, value in self._extract_entities(message).items():
            nodes.append(f"entity:{key}:{value}")
            if user_id:
                edges.append(f"user:{user_id}->entity:{key}:{value}")
            if session_id:
                edges.append(f"session:{session_id}->entity:{key}:{value}")

        if user_id and session_id:
            edges.append(f"user:{user_id}->session:{session_id}")

        self.state["entities"].update(self._extract_entities(message))
        self.state["edges"].extend(edges)
        return {"nodes": sorted(set(nodes)), "edges": sorted(set(edges))}

    def _find_similar_examples(self, message: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.matrix is None or not self.documents:
            return []
        query = self.vectorizer.transform([message])
        similarities = cosine_similarity(query, self.matrix)[0]
        ranked = similarities.argsort()[-top_k:][::-1]
        results: List[Dict[str, Any]] = []
        for idx in ranked:
            score = float(similarities[idx])
            if score <= 0.0:
                continue
            results.append({
                "message": self.documents[int(idx)],
                "label": self.labels[int(idx)],
                "intent": self.intent_types[int(idx)],
                "score": round(score, 3),
            })
        return results

    def retrieve_context(self, message: str, user_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        cleaned = self._register_message(message, user_id=user_id, session_id=session_id)
        graph_context = self._graph_context(cleaned, user_id=user_id, session_id=session_id)
        signals = _build_symbolic_signals(cleaned)
        similar_examples = self._find_similar_examples(cleaned)
        return {
            "sanitized_message": cleaned,
            "similar_examples": similar_examples,
            "graph_context": graph_context,
            "symbolic_signals": signals,
            "user_id": user_id,
            "session_id": session_id,
        }

    @staticmethod
    def _select_scam_type(signals: Dict[str, Any]) -> str:
        indicators = signals.get("indicators", [])
        if "reward_manipulation" in indicators:
            return "Reward_Manipulation"
        if "otp_request" in indicators:
            return "OTP_Fraud"
        if "account_alert" in indicators:
            return "Account_Suspension"
        if "urgency" in indicators:
            return "Urgency"
        if "suspicious_link" in indicators:
            return "Phishing"
        if "financial_request" in indicators:
            return "Financial_Fraud"
        return "Other"

    def _symbolic_classification(self, message: str, context: Dict[str, Any]) -> ScamDetector:
        signals = context.get("symbolic_signals", {})
        indicators = signals.get("indicators", [])
        risk_score = float(signals.get("risk_score", 0.0))
        classification = signals.get("classification", "Not Scam")

        if classification == "Scam":
            is_scam = "Scam"
            recommended = "verify"
            reply = "The message contains scam-like patterns such as urgency, financial ask, or deceptive messaging."
        elif classification == "Unknown":
            is_scam = "Unknown"
            recommended = "verify"
            reply = "The message is ambiguous. Extra context or verification is recommended."
        else:
            is_scam = "Not Scam"
            recommended = "ignore"
            reply = "The message appears to be ordinary and non-deceptive."

        return ScamDetector(
            is_scam=is_scam,
            scam_type=self._select_scam_type(signals),
            confidence=min(0.99, max(0.55, risk_score + 0.25 if is_scam == "Scam" else 0.52)),
            reply=reply,
            indicators=indicators or None,
            recommended_action=recommended,
        )

    def multi_agent_inference(
        self,
        message: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        context = self.retrieve_context(message, user_id=user_id, session_id=session_id)
        examples = context.get("similar_examples", [])[:5]
        symbolic = context.get("symbolic_signals", {})

        if not GOOGLE_API_KEY:
            result = self._symbolic_classification(message, context)
            return {"result": result, "retrieval_context": context, "method": "symbolic"}

        parser = PydanticOutputParser(pydantic_object=ScamDetector)
        fmt = parser.get_format_instructions()
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Privacy note: sensitive identifiers have been redacted before analysis.\n\n"
            f"Relevant retrieved examples:\n{json.dumps(examples, ensure_ascii=False, indent=2)}\n\n"
            f"Symbolic risk signals:\n{json.dumps(symbolic, ensure_ascii=False, indent=2)}\n\n"
            f"Graph context:\n{json.dumps(context.get('graph_context', {}), ensure_ascii=False, indent=2)}\n\n"
            f"Format instructions:\n{fmt}\n\nMessage:\n{context['sanitized_message']}\n"
        )

        try:
            raw = get_llm(model_name).invoke(prompt)
            inner = extract_text_from_response(raw)
            parsed = parse_model_output(parser, inner)
            return {"result": parsed, "retrieval_context": context, "method": "graph_rag_llm"}
        except Exception:
            fallback = self._symbolic_classification(message, context)
            return {"result": fallback, "retrieval_context": context, "method": "graph_rag_symbolic_fallback"}


def classify_message_with_graph_rag(
    message: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    model_name: Optional[str] = None,
    dataset_path: Optional[str | Path] = None,
) -> ScamDetector:
    engine = GraphRAGEngine(dataset_path=dataset_path)
    response = engine.multi_agent_inference(message, user_id=user_id, session_id=session_id, model_name=model_name)
    return response["result"]


__all__ = ["GraphRAGEngine", "classify_message_with_graph_rag", "redact_pii"]
