"""BYOK AI provider registry — users supply their own API keys."""
from __future__ import annotations

from typing import Protocol

import httpx


class AIProvider(Protocol):
    def chat(self, messages: list[dict], context: str = "") -> str: ...

    def explain(self, text: str, style: str, context: str = "") -> str: ...


class ProviderError(Exception):
    def __init__(self, message: str, code: str = "provider_error"):
        super().__init__(message)
        self.code = code


def _style_prompt(style: str) -> str:
    return {
        "simpler": "Explain in very simple terms for a beginner.",
        "technical": "Explain with technical precision.",
        "example": "Explain and give a concrete example.",
        "balanced": "Explain clearly with a short example if helpful.",
    }.get(style, "Explain clearly.")


class OpenAIProvider:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[dict], context: str = "") -> str:
        payload_messages = list(messages)
        if context:
            payload_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an AI reading companion. Use the book context below. "
                        "Be clear and concise.\n\n" + context[:6000]
                    ),
                },
                *payload_messages,
            ]
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": payload_messages},
            )
        if resp.status_code >= 400:
            raise ProviderError(resp.text[:300], code="openai_error")
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def explain(self, text: str, style: str, context: str = "") -> str:
        return self.chat(
            [
                {
                    "role": "user",
                    "content": f"{_style_prompt(style)}\n\nSelected text:\n\"\"\"{text}\"\"\"",
                }
            ],
            context=context,
        )


class GeminiProvider:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[dict], context: str = "") -> str:
        parts = []
        if context:
            parts.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": "You are an AI reading companion. Context:\n"
                            + context[:6000]
                        }
                    ],
                }
            )
            parts.append({"role": "model", "parts": [{"text": "Understood."}]})
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            parts.append({"role": role, "parts": [{"text": m["content"]}]})
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json={"contents": parts})
        if resp.status_code >= 400:
            raise ProviderError(resp.text[:300], code="gemini_error")
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise ProviderError("Unexpected Gemini response", code="gemini_error") from exc

    def explain(self, text: str, style: str, context: str = "") -> str:
        return self.chat(
            [
                {
                    "role": "user",
                    "content": f"{_style_prompt(style)}\n\nSelected text:\n\"\"\"{text}\"\"\"",
                }
            ],
            context=context,
        )


class AnthropicProvider:
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-latest"):
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[dict], context: str = "") -> str:
        system = "You are an AI reading companion."
        if context:
            system += "\n\nBook context:\n" + context[:6000]
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 1024,
                    "system": system,
                    "messages": [
                        {"role": m["role"], "content": m["content"]}
                        for m in messages
                        if m["role"] in ("user", "assistant")
                    ],
                },
            )
        if resp.status_code >= 400:
            raise ProviderError(resp.text[:300], code="anthropic_error")
        data = resp.json()
        return data["content"][0]["text"]

    def explain(self, text: str, style: str, context: str = "") -> str:
        return self.chat(
            [{"role": "user", "content": f"{_style_prompt(style)}\n\n\"\"\"{text}\"\"\""}],
            context=context,
        )


PROVIDERS = {
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "anthropic": AnthropicProvider,
}


def get_provider(name: str, api_key: str):
    cls = PROVIDERS.get(name)
    if not cls:
        raise ProviderError(f"Unknown provider: {name}", code="unknown_provider")
    return cls(api_key)
