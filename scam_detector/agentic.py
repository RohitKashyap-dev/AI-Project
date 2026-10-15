from __future__ import annotations

import json
from typing import Any

from scam_detector.classifier import classify_message
from scam_detector.graph_rag import GraphRAGEngine, redact_pii
from scam_detector.llm_client import get_llm
from scam_detector.schemas import ScamDetector


class AgentDecision:
    def __init__(self, tool: str, reason: str, evidence: dict[str, Any] | None = None):
        self.tool = tool
        self.reason = reason
        self.evidence = evidence or {}


def _rule_check(message: str) -> tuple[str, dict[str, Any], str]:
    cleaned = redact_pii(message)
    lowered = cleaned.lower()
    indicators: list[str] = []

    if any(token in lowered for token in ["won", "congratulations", "claim prize", "free prize", "processing fee"]):
        indicators.append("reward_manipulation")
    if any(token in lowered for token in ["otp", "one time password", "share otp", "verify otp", "pin"]):
        indicators.append("otp_request")
    if any(token in lowered for token in ["account suspended", "restricted your", "verify your account", "security alert"]):
        indicators.append("account_alert")
    if any(token in lowered for token in ["click this link", "visit link", "tap this link", "tracking link", "click here"]):
        indicators.append("phishing_link")
    if any(token in lowered for token in ["urgent", "immediately", "today", "limited time", "expires soon", "act now"]):
        indicators.append("urgency")
    if any(token in lowered for token in ["pay a fee", "processing fee", "deposit", "upi", "bank account", "refund"]):
        indicators.append("financial_request")

    if indicators:
        return "rule_check", {"indicators": indicators, "sanitized_message": cleaned}, "High-risk signal pattern detected."
    return "rule_check", {"indicators": [], "sanitized_message": cleaned}, "No obvious rule-based scam indicators."


APPROVED_TOOLS = {"rule_check", "retrieval", "llm_direct"}


def _normalize_llm_tool_response(payload: Any, fallback_evidence: dict[str, Any]) -> AgentDecision:
    if isinstance(payload, str):
        payload = json.loads(payload)

    if not isinstance(payload, dict):
        raise ValueError("LLM tool selection must return a JSON object.")

    tool_name = payload.get("tool") or payload.get("tool_name")
    if tool_name not in APPROVED_TOOLS:
        raise ValueError(f"Unsupported tool '{tool_name}'. Approved tools: {sorted(APPROVED_TOOLS)}")

    evidence = payload.get("evidence")
    if evidence is not None and not isinstance(evidence, dict):
        raise ValueError("Tool evidence must be a JSON object.")

    return AgentDecision(
        tool=tool_name,
        reason=payload.get("reason") or "LLM selected the next tool based on the message evidence.",
        evidence={**fallback_evidence, **(evidence or {})},
    )


def _llm_select_tool(message: str, evidence: dict[str, Any], model_name: str | None = None) -> AgentDecision:
    prompt = (
        "Select exactly one tool to run next for scam detection. "
        "Return valid JSON with keys: tool, reason, evidence. "
        f"Approved tools: {sorted(APPROVED_TOOLS)}.\n"
        f"Message: {message}\n"
        f"Evidence: {json.dumps(evidence, ensure_ascii=False)}\n"
        "Rules: prefer rule_check for explicit reward/urgency/OTP patterns, retrieval for suspicious account/link/verification flows, and llm_direct for ambiguous or informational messages."
    )

    try:
        raw = get_llm(model_name).invoke(prompt)
        content = getattr(raw, "content", raw)
        if hasattr(content, "text"):
            content = content.text
        if isinstance(content, str):
            text = content.strip()
            if text.startswith("```"):
                text = text.strip("`\n ")
                if text.lower().startswith("json"):
                    text = text.split("\n", 1)[1]
            payload = json.loads(text)
        else:
            payload = content
        return _normalize_llm_tool_response(payload, evidence)
    except Exception:
        pass

    return _fallback_select_tool(message, evidence)


def _fallback_select_tool(message: str, evidence: dict[str, Any]) -> AgentDecision:
    lowered = message.lower()

    if any(keyword in lowered for keyword in ["prize", "won", "claim", "reward", "lottery", "processing fee"]):
        return AgentDecision(
            tool="rule_check",
            reason="Reward-style scam language is explicit and should be evaluated first using rule heuristics.",
            evidence=evidence,
        )

    if any(keyword in lowered for keyword in ["link", "click", "verify", "account", "otp", "upi", "bank"]):
        return AgentDecision(
            tool="retrieval",
            reason="This looks like a suspicious request that benefits from retrieval context and semantic matching.",
            evidence=evidence,
        )

    return AgentDecision(
        tool="llm_direct",
        reason="This looks informational or ambiguous; use the direct classifier path as the safest default.",
        evidence=evidence,
    )


def _select_tool(message: str, evidence: dict[str, Any], model_name: str | None = None) -> AgentDecision:
    try:
        return _llm_select_tool(message, evidence, model_name=model_name)
    except Exception:
        return _fallback_select_tool(message, evidence)


def _run_rule_based_result(message: str, evidence: dict[str, Any]) -> ScamDetector:
    indicators = evidence.get("indicators", [])
    lowered = (message or "").lower()
    weights = {
        "reward_manipulation": 0.18,
        "otp_request": 0.38,
        "account_alert": 0.28,
        "phishing_link": 0.35,
        "urgency": 0.30,
        "financial_request": 0.24,
    }
    score = sum(weights.get(indicator, 0.10) for indicator in indicators)

    if any(phrase in lowered for phrase in ["not asking for money", "not asking for payment", "newsletter", "just informational", "reminder only"]):
        score -= 0.18

    explicit_combo = (
        "reward_manipulation" in indicators and ("financial_request" in indicators or "urgency" in indicators)
    ) or ("otp_request" in indicators and "account_alert" in indicators) or (
        "phishing_link" in indicators and ("urgency" in indicators or "account_alert" in indicators)
    )
    strong_single_signal = (
        "reward_manipulation" in indicators
        and any(phrase in lowered for phrase in ["claim prize", "free prize", "processing fee", "won ₹", "won rs", "won lakhs", "lottery prize"])
    ) or (
        "otp_request" in indicators
        and any(phrase in lowered for phrase in ["share otp", "verify otp", "send otp", "one time password", "enter otp"])
    ) or (
        "urgency" in indicators
        and any(phrase in lowered for phrase in ["expires soon", "limited time", "act now", "immediately", "today only"])
    )

    if explicit_combo or strong_single_signal or (len(indicators) >= 2 and score >= 0.55):
        decision = "Scam"
    elif score >= 0.25 or (len(indicators) >= 2 and score > 0.10):
        decision = "Unknown"
    else:
        decision = "Not Scam"

    if decision == "Scam":
        return ScamDetector(
            is_scam="Scam",
            scam_type="Reward_Manipulation" if "reward_manipulation" in indicators else "OTP_Fraud" if "otp_request" in indicators else "Phishing" if "phishing_link" in indicators else "Financial_Fraud",
            confidence=min(0.99, max(0.55, score + 0.30)),
            reply="Rule-based analysis detected multiple scam indicators, but the final result also considers context and the strength of the evidence.",
            indicators=indicators,
            recommended_action="verify",
        )

    if decision == "Unknown":
        return ScamDetector(
            is_scam="Unknown",
            scam_type="Other",
            confidence=min(0.85, max(0.35, score + 0.15)),
            reply="The message contains weak or mixed scam signals, so its risk is uncertain and should be reviewed.",
            indicators=indicators,
            recommended_action="verify",
        )

    return ScamDetector(
        is_scam="Not Scam",
        scam_type="Informational_Alert",
        confidence=max(0.45, min(0.9, 0.75 - score)),
        reply="No strong scam indicators were combined across the rule checks.",
        indicators=indicators,
        recommended_action="ignore",
    )


def classify_message_agentic(message: str, model_name: str | None = None, max_steps: int = 3) -> ScamDetector:
    """Agentic orchestration that chooses the best tool based on the current message.

    This keeps the existing services and adds a decision layer on top of them rather than replacing them.
    """
    if not message or not message.strip():
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

    rule_tool, rule_evidence, rule_reason = _rule_check(message)
    tools_used: list[str] = []

    for step in range(max_steps):
        decision = _select_tool(message, rule_evidence, model_name=model_name)
        tools_used.append(decision.tool)

        if decision.tool == "rule_check":
            result = _run_rule_based_result(message, rule_evidence)
            result.reply = f"{rule_reason} {result.reply}"
            return result

        if decision.tool == "retrieval":
            try:
                engine = GraphRAGEngine(dataset_path=None)
                context = engine.retrieve_context(message)
                if context.get("similar_examples"):
                    result = engine._symbolic_classification(message, context)
                    result.reply = f"Retrieval selected a relevant context set. {result.reply}"
                    return result
            except Exception:
                pass

        if decision.tool == "llm_direct":
            direct = classify_message(message, model_name=model_name)
            if direct is not None:
                return direct

        if step == max_steps - 1:
            break

        if decision.tool in {"retrieval", "llm_direct"}:
            tool_evidence = {**rule_evidence, "tools_tried": tools_used, "step": step + 1}
            next_decision = _select_tool(message, tool_evidence, model_name=model_name)
            if next_decision.tool == "rule_check":
                result = _run_rule_based_result(message, rule_evidence)
                result.reply = f"Tool loop re-evaluated with rule evidence after prior tool attempts. {result.reply}"
                return result

    fallback = _run_rule_based_result(message, rule_evidence)
    fallback.reply = f"Agent fallback triggered after the bounded tool loop was exhausted. {fallback.reply}"
    return fallback
