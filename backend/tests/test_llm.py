from app.services.llm import LLMClient


def test_llm_stub_echoes_prompt_snippet():
    client = LLMClient()
    reply = client.generate("Tell me something about context", max_tokens=32)
    assert "[stubbed llm reply]" in reply
    assert "Tell me something" in reply
