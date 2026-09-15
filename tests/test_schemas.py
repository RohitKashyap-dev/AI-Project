from scam_detector.llm_client import get_model_candidates
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


def test_get_model_candidates_prioritizes_requested_model_and_falls_back_to_supported_values():
    candidates = get_model_candidates("gemini-2.0-flash")
    assert candidates[0] == "gemini-2.0-flash"
    assert "gemini-3.1-flash-lite" in candidates
    assert "gemini-3.6-flash" in candidates
