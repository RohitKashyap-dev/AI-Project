from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from scam_detector.graph_rag import GraphRAGEngine, _build_symbolic_signals, redact_pii
from scam_detector.schemas import ScamDetector

APPROVED_TOOLS = {
    "retrieval_lookup": "retrieval_lookup",
    "scam_rules_check": "scam_rules_check",
}


def _validate_message_arg(arguments: dict[str, Any], tool_name: str) -> str:
    message = arguments.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ValueError(f"{tool_name} requires a non-empty 'message' argument.")
    return message.strip()


class ToolCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: Literal["retrieval_lookup", "scam_rules_check"]
    arguments: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def model_validate(cls, obj: Any, *args: Any, **kwargs: Any):
        if isinstance(obj, dict):
            tool_name = obj.get("tool_name")
            if tool_name not in APPROVED_TOOLS:
                raise ValueError(
                    f"Unsupported tool '{tool_name}'. Approved tools: {sorted(APPROVED_TOOLS.keys())}."
                )
            arguments = obj.get("arguments") or {}
            if not isinstance(arguments, dict):
                raise ValueError(f"Tool '{tool_name}' arguments must be a dictionary.")
            if "message" not in arguments:
                raise ValueError(f"Tool '{tool_name}' requires a 'message' argument.")
            _validate_message_arg(arguments, tool_name)
        return super().model_validate(obj, *args, **kwargs)


def retrieval_lookup_tool(message: str) -> dict[str, Any]:
    cleaned = message.strip()
    try:
        engine = GraphRAGEngine(dataset_path=None)
        context = engine.retrieve_context(cleaned)
        return {
            "sanitized_message": context.get("sanitized_message", cleaned),
            "similar_examples": context.get("similar_examples", []),
            "graph_context": context.get("graph_context", {"nodes": [], "edges": []}),
            "symbolic_signals": context.get("symbolic_signals", {}),
            "user_id": context.get("user_id"),
            "session_id": context.get("session_id"),
        }
    except Exception:
        fallback_signals = _build_symbolic_signals(cleaned)
        return {
            "sanitized_message": cleaned,
            "similar_examples": [],
            "graph_context": {"nodes": [], "edges": []},
            "symbolic_signals": fallback_signals,
            "user_id": None,
            "session_id": None,
        }


def scam_rules_tool(message: str) -> dict[str, Any]:
    cleaned = redact_pii(message).strip()
    lowered = cleaned.lower()
    indicators: list[str] = []

    if any(token in lowered for token in ["urgent", "immediately", "today", "limited time", "expires soon", "act now"]):
        indicators.append("urgency")
    if any(token in lowered for token in ["otp", "one time password", "share otp", "verify otp", "pin", "password code"]):
        indicators.append("otp_request")
    if any(token in lowered for token in ["click this link", "visit link", "tap this link", "tracking link", "click here", "link"]):
        indicators.append("suspicious_link")
    if any(token in lowered for token in ["won", "congratulations", "claim prize", "free prize", "processing fee", "lottery", "reward", "prize"]):
        indicators.append("reward_manipulation")
    if any(token in lowered for token in ["account suspended", "restricted your", "verify your account", "security alert", "bank alert"]):
        indicators.append("account_alert")
    if any(token in lowered for token in ["pay a fee", "processing fee", "deposit", "upi", "bank account", "refund", "transfer", "bank details"]):
        indicators.append("financial_request")

    unique_indicators = sorted(set(indicators))
    weights = {
        "urgency": 0.30,
        "otp_request": 0.38,
        "suspicious_link": 0.35,
        "reward_manipulation": 0.18,
        "account_alert": 0.28,
        "financial_request": 0.24,
    }
    score = sum(weights.get(indicator, 0.12) for indicator in unique_indicators)

    if any(phrase in lowered for phrase in ["not asking for money", "not asking for payment", "not asking for a fee", "newsletter", "just informational", "reminder only"]):
        score -= 0.18

    if any(phrase in lowered for phrase in ["verify your account", "security alert", "account suspended"]):
        score += 0.15

    explicit_combo = (
        "reward_manipulation" in unique_indicators and ("financial_request" in unique_indicators or "urgency" in unique_indicators)
    ) or ("otp_request" in unique_indicators and "account_alert" in unique_indicators) or (
        "suspicious_link" in unique_indicators and ("urgency" in unique_indicators or "account_alert" in unique_indicators)
    )

    if explicit_combo or (len(unique_indicators) >= 2 and score >= 0.55):
        classification = "Scam"
    elif score >= 0.25 or (len(unique_indicators) >= 2 and score > 0.10):
        classification = "Unknown"
    else:
        classification = "Not Scam"

    return {
        "classification": classification,
        "indicators": unique_indicators,
        "sanitized_message": cleaned,
        "risk_score": round(min(1.0, max(0.0, score)), 3),
        "summary": "Deterministic scam-rule evaluation completed.",
    }


def _deterministic_tool_selector(message: str) -> ToolCallRequest:
    lowered = message.lower()
    if any(token in lowered for token in ["otp", "click", "link", "verify", "account", "bank", "upi", "urgent"]):
        return ToolCallRequest(
            tool_name="retrieval_lookup",
            arguments={"message": message},
        )
    return ToolCallRequest(
        tool_name="scam_rules_check",
        arguments={"message": message},
    )


def _finalize_classification(tool_result: dict[str, Any]) -> ScamDetector:
    classification = str(tool_result.get("classification", "Unknown")).strip()
    indicators = tool_result.get("indicators") or []
    risk_score = float(tool_result.get("risk_score", 0.0) or 0.0)

    if classification == "Scam":
        scam_type = "Reward_Manipulation" if "reward_manipulation" in indicators else "OTP_Fraud" if "otp_request" in indicators else "Phishing" if "suspicious_link" in indicators else "Financial_Fraud"
        result = ScamDetector(
            is_scam="Scam",
            scam_type=scam_type,
            confidence=min(0.99, max(0.55, risk_score + 0.35)),
            reply="The message triggered scam-risk checks and should be treated as suspicious.",
            indicators=indicators,
            recommended_action="verify",
        )
    elif classification == "Unknown":
        result = ScamDetector(
            is_scam="Unknown",
            scam_type="Other",
            confidence=min(0.8, max(0.35, risk_score + 0.2)),
            reply="The message is ambiguous and needs additional verification.",
            indicators=indicators,
            recommended_action="verify",
        )
    else:
        result = ScamDetector(
            is_scam="Not Scam",
            scam_type="Informational_Alert",
            confidence=max(0.4, min(0.9, 0.7 - risk_score)),
            reply="The message does not match the scam-risk rules used by the tool pipeline.",
            indicators=indicators,
            recommended_action="ignore",
        )

    allowed = {"Scam", "Not Scam", "Unknown"}
    if result.is_scam not in allowed:
        raise ValueError(f"Invalid final classification: {result.is_scam}")
    if result.scam_type not in set(__import__('scam_detector.schemas', fromlist=['SCAM_TYPES']).SCAM_TYPES):
        raise ValueError(f"Invalid scam type: {result.scam_type}")
    return result


def _tool_result_to_scam_detector(tool_name: str, tool_result: dict[str, Any]) -> ScamDetector:
    if tool_name == "scam_rules_check":
        return _finalize_classification(tool_result)

    symbols = tool_result.get("symbolic_signals", {})
    if isinstance(symbols, dict):
        return _finalize_classification(symbols)

    return _finalize_classification({"classification": "Unknown", "indicators": [], "risk_score": 0.0})


def analyze_with_tools(message: str, model_name: str | None = None, max_steps: int = 3) -> ScamDetector:
    if not isinstance(message, str) or not message.strip():
        return ScamDetector(
            is_scam="Unknown",
            scam_type="Other",
            confidence=0.0,
            reply="No message was supplied.",
            indicators=[],
            recommended_action="verify",
        )

    if max_steps <= 0:
        raise ValueError("max_steps must be a positive integer.")

    step_count = 0
    last_result: dict[str, Any] | None = None
    last_tool_name = "scam_rules_check"

    while step_count < max_steps:
        step_count += 1
        request = _deterministic_tool_selector(message)
        if request.tool_name not in APPROVED_TOOLS:
            raise ValueError(f"Unsupported tool '{request.tool_name}' selected by planner.")

        arguments = request.arguments or {}
        message_text = _validate_message_arg(arguments, request.tool_name)
        requested_tool = request.tool_name
        last_tool_name = requested_tool

        if requested_tool == "retrieval_lookup":
            tool_result = retrieval_lookup_tool(message_text)
        elif requested_tool == "scam_rules_check":
            tool_result = scam_rules_tool(message_text)
        else:
            raise ValueError(f"Unsupported tool '{requested_tool}'.")

        last_result = tool_result

        if requested_tool == "scam_rules_check":
            return _finalize_classification(tool_result)

        if isinstance(tool_result.get("symbolic_signals"), dict):
            symbols = tool_result["symbolic_signals"]
            if isinstance(symbols.get("classification"), str):
                return _finalize_classification(symbols)

        if step_count >= max_steps:
            break

    if last_result is not None:
        return _tool_result_to_scam_detector(last_tool_name, last_result)

    fallback = scam_rules_tool(message)
    return _finalize_classification(fallback)


__all__ = [
    "ToolCallRequest",
    "retrieval_lookup_tool",
    "scam_rules_tool",
    "analyze_with_tools",
]
