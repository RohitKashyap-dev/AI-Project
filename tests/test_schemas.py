from scam_detector.schemas import ScamDetector


def test_scam_schema_accepts_valid_payload():
    result = ScamDetector(
        is_scam="Scam",
        scam_type="Phishing",
        confidence=0.92,
        reply="Suspicious tracking link with urgency.",
        indicators=["unexpected link", "urgency"],
        recommended_action="verify",
    )
    assert result.is_scam == "Scam"
    assert 0.0 <= result.confidence <= 1.0
