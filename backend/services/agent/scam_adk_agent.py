from __future__ import annotations

import uuid
from typing import Any

from scam_detector.classifier import classify_message
from scam_detector.config import GOOGLE_API_KEY
from scam_detector.schemas import ScamDetector

try:
    from google.adk import Runner
    from google.adk.agents import LlmAgent
    from google.adk.sessions import InMemorySessionService
    from google.adk.tools import FunctionTool
    from google.genai import types
except Exception:  # pragma: no cover - dependency is optional at import time
    Runner = None
    LlmAgent = None
    InMemorySessionService = None
    FunctionTool = None
    types = None

from backend.services.agent.scam_analysis_agent import (
    analyze_with_tools,
    retrieval_lookup_tool,
    scam_rules_tool,
)


def classify_message_tool(message: str, model_name: str | None = None) -> dict[str, Any]:
    """Wrap the existing classifier so the ADK agent can invoke the same final classification path."""
    result = classify_message(message, model_name=model_name)
    if result is None:
        return {
            "is_scam": "Unknown",
            "scam_type": "Other",
            "confidence": 0.0,
            "reply": "Direct classification failed and no structured result was returned.",
            "indicators": [],
            "recommended_action": "verify",
        }

    return {
        "is_scam": result.is_scam,
        "scam_type": result.scam_type,
        "confidence": result.confidence,
        "reply": result.reply,
        "indicators": result.indicators,
        "recommended_action": result.recommended_action,
    }


def build_scam_adk_agent(model_name: str | None = None) -> LlmAgent:
    if LlmAgent is None or FunctionTool is None or types is None:
        raise ModuleNotFoundError("google-adk is not installed. Install google-adk to enable the ADK runtime.")

    selected_model = model_name or "gemini-3.1-flash-lite"
    return LlmAgent(
        name="scam_analysis_adk_agent",
        model=selected_model,
        description=(
            "A scam-detector agent that can inspect suspicious messages using rule-based scam checks and retrieval context."
        ),
        instruction=(
            "Use the scam_rules_tool for explicit scam patterns like prize claims, OTP requests, urgent account alerts, or phishing links. "
            "Use retrieval_lookup_tool when the message contains account, verification, banking, or link-based escalations. "
            "Use classify_message_tool as the final direct model pass when the evidence is mixed or ambiguous. "
            "Return a concise final classification using the evidence from the tools."
        ),
        tools=[
            FunctionTool(scam_rules_tool),
            FunctionTool(retrieval_lookup_tool),
            FunctionTool(classify_message_tool),
        ],
        generate_content_config=types.GenerateContentConfig(temperature=0.1),
    )


def run_adk_agent(message: str, model_name: str | None = None, max_steps: int = 3) -> ScamDetector:
    if not isinstance(message, str) or not message.strip():
        return ScamDetector(
            is_scam="Unknown",
            scam_type="Other",
            confidence=0.0,
            reply="No message was supplied.",
            indicators=[],
            recommended_action="verify",
        )

    if not GOOGLE_API_KEY:
        return analyze_with_tools(message, model_name=model_name, max_steps=max_steps)

    if Runner is None or InMemorySessionService is None or LlmAgent is None:
        return analyze_with_tools(message, model_name=model_name, max_steps=max_steps)

    try:
        agent = build_scam_adk_agent(model_name=model_name)
        session_service = InMemorySessionService()
        session_id = f"scam-{uuid.uuid4().hex}"
        session = session_service.create_session_sync(user_id="scam-user", session_id=session_id)
        runner = Runner(app_name="scam-detector", agent=agent, session_service=session_service)
        user_message = types.Content(
            role="user",
            parts=[types.Part.from_text(message)],
        )

        events = list(runner.run(user_id="scam-user", session_id=session.id, new_message=user_message))
        for event in events:
            content = getattr(event, "content", None)
            if content is None:
                continue
            parts = getattr(content, "parts", [])
            for part in parts:
                if getattr(part, "text", None):
                    text = part.text.strip()
                    if "scam" in text.lower() or "not scam" in text.lower() or "unknown" in text.lower():
                        return analyze_with_tools(message, model_name=model_name, max_steps=max_steps)
    except Exception:
        pass

    return analyze_with_tools(message, model_name=model_name, max_steps=max_steps)


__all__ = ["build_scam_adk_agent", "run_adk_agent", "classify_message_tool"]
