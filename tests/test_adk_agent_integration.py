from backend.services.agent.scam_adk_agent import build_scam_adk_agent


def test_build_scam_adk_agent_registers_tools():
    agent = build_scam_adk_agent(model_name="gemini-3.1-flash-lite")

    assert agent.name == "scam_analysis_adk_agent"
    assert len(agent.tools) >= 3
    assert any(getattr(tool, "func", None).__name__ == "scam_rules_tool" for tool in agent.tools)
    assert any(getattr(tool, "func", None).__name__ == "retrieval_lookup_tool" for tool in agent.tools)
    assert any(getattr(tool, "func", None).__name__ == "classify_message_tool" for tool in agent.tools)
