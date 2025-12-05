from app.services.llm import LLMClient


def test_llm_stub_echoes_prompt_snippet(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "stub")
    client = LLMClient()
    reply = client.generate("Tell me something about context", max_tokens=32)
    assert "[stubbed llm reply]" in reply
    assert "Tell me something" in reply
