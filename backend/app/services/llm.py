from __future__ import annotations

import logging
from typing import Any

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self) -> None:
        self.settings = settings

    def generate(self, prompt: str, max_tokens: int = 128) -> str:
        provider = (self.settings.llm_provider or "stub").lower()
        if provider == "stub":
            return f"[stubbed llm reply]\nPrompt was:\n{prompt[:500]}"

        api_key = self.settings.llm_api_key
        if not api_key:
            raise ValueError("LLM API key is not configured")

        url = self._provider_url(provider)
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": "You answer with concise, grounded responses using provided context."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if not response.ok:
            logger.error("LLM provider error status=%s body=%s", response.status_code, response.text)
            raise RuntimeError(f"LLM provider returned status {response.status_code}")

        data: dict[str, Any] = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content")
        if not content:
            logger.error("LLM provider returned unexpected payload: %s", data)
            raise RuntimeError("LLM provider response missing content")
        return str(content)

    def _provider_url(self, provider: str) -> str:
        if provider == "openai":
            return "https://api.openai.com/v1/chat/completions"
        if provider == "groq":
            return "https://api.groq.com/openai/v1/chat/completions"
        raise ValueError(f"Unsupported LLM provider: {provider}")
