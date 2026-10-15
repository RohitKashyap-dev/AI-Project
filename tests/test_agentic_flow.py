from scam_detector.agentic import classify_message_agentic


def test_agentic_flow_returns_valid_result_for_scam_message():
    result = classify_message_agentic(
        "Congratulations! You have won ₹10 Lakhs. Pay a small processing fee to claim your prize."
    )

    assert result.is_scam in {"Scam", "Unknown"}
    assert result.scam_type
    assert result.reply
