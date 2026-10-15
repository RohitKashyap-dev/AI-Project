import pytest

from backend.services.agent.scam_analysis_agent import (
    ToolCallRequest,
    analyze_with_tools,
    retrieval_lookup_tool,
    scam_rules_tool,
)


def test_scam_rules_tool_detects_high_risk_signals():
    result = scam_rules_tool(
        "Your OTP is 123456. Click this link to verify your account immediately."
    )

    assert result["classification"] == "Scam"
    assert "otp_request" in result["indicators"]
    assert "urgency" in result["indicators"]
    assert "suspicious_link" in result["indicators"]


def test_retrieval_lookup_tool_returns_context():
    result = retrieval_lookup_tool("Congratulations! You have won a prize. Pay a processing fee.")

    assert result["sanitized_message"]
    assert "similar_examples" in result
    assert "symbolic_signals" in result


def test_invalid_tool_calls_are_rejected():
    with pytest.raises(ValueError, match="Unsupported tool"):
        ToolCallRequest.model_validate({"tool_name": "not_real", "arguments": {"message": "test"}})

    with pytest.raises(ValueError, match="message"):
        ToolCallRequest.model_validate({"tool_name": "scam_rules_check", "arguments": {}})


def test_weak_keyword_evidence_is_not_auto_scam():
    result = scam_rules_tool("I saw a prize notification in a newsletter, but it's not asking for money.")

    assert result["classification"] in {"Unknown", "Not Scam"}
    assert "reward_manipulation" in result["indicators"]


def test_analyze_with_tools_respects_step_limit():
    result = analyze_with_tools(
        "Urgent! Click the link and share your OTP now.",
        model_name="dummy-model",
        max_steps=1,
    )

    assert result.is_scam in {"Scam", "Unknown", "Not Scam"}
    assert result.scam_type
