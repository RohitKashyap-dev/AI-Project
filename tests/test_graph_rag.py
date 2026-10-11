from scam_detector.graph_rag import GraphRAGEngine, redact_pii


def test_redact_pii_masks_common_identifiers():
    cleaned = redact_pii("Call 9876543210 or email abc@example.com and use UPI 1234567890")
    assert "9876543210" not in cleaned
    assert "abc@example.com" not in cleaned
    assert "UPI" in cleaned


def test_graph_rag_retrieves_similar_examples_and_tracks_state():
    engine = GraphRAGEngine(dataset_path=None)
    message = "Congratulations! You have won a prize. Pay a small fee to claim it now."

    context = engine.retrieve_context(message, user_id="user-1", session_id="s-1")
    assert context["similar_examples"]
    assert "user-1" in engine.state["users"]
    assert "s-1" in engine.state["sessions"]
