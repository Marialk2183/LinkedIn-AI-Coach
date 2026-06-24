"""Pluggable text-generation providers behind a single tiny interface.

The Azure upgrade keeps **Gemini as the default and universal fallback** while
adding **Azure OpenAI** as an env-selected alternative. Both implement the same
:class:`TextProvider` contract (one method: ``generate(prompt) -> str | None``),
so :class:`services.ai_service.AIService` owns all the prompt logic and just
asks the selected provider to turn a prompt into text.

Selection (``AI_PROVIDER``):

* ``auto`` (default) — use Azure OpenAI when it's fully configured, else Gemini.
* ``gemini`` / ``azure`` — force one (returns ``None`` if it isn't configured,
  which makes ``AIService`` degrade to its deterministic templates).

Azure OpenAI is called over its **REST API with httpx** (already a dependency),
not the ``openai`` SDK — fewer deps and trivially testable offline with
``httpx.MockTransport`` via the injected client.
"""

from __future__ import annotations

import logging
from typing import Protocol

import httpx

from config import Settings

logger = logging.getLogger(__name__)


class TextProvider(Protocol):
    name: str

    def generate(self, prompt: str) -> str | None:
        """Return generated text, or ``None`` to trigger the caller's fallback."""
        ...


class GeminiProvider:
    """Google Gemini via google-generativeai."""

    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        self._model = None
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.gemini_api_key)
            self._model = genai.GenerativeModel(settings.gemini_model)
            logger.info("Gemini initialized (%s)", settings.gemini_model)
        except Exception:  # noqa: BLE001
            logger.exception("Gemini init failed; provider will no-op.")
            self._model = None

    def generate(self, prompt: str) -> str | None:
        if self._model is None:
            return None
        try:
            resp = self._model.generate_content(prompt)
            return (getattr(resp, "text", "") or "").strip() or None
        except Exception:  # noqa: BLE001
            logger.exception("Gemini generation failed; using fallback.")
            return None


class AzureOpenAIProvider:
    """Azure OpenAI chat completions over REST (httpx)."""

    name = "azure"

    def __init__(self, settings: Settings, *, client: httpx.Client | None = None) -> None:
        endpoint = (settings.azure_openai_endpoint or "").rstrip("/")
        self._deployment = settings.azure_openai_deployment
        self._api_key = settings.azure_openai_api_key
        self._url = (
            f"{endpoint}/openai/deployments/{self._deployment}/chat/completions"
            f"?api-version={settings.azure_openai_api_version}"
        )
        self._client = client or httpx.Client(timeout=settings.fetch_timeout_seconds)
        logger.info("Azure OpenAI initialized (deployment=%s)", self._deployment)

    def generate(self, prompt: str) -> str | None:
        try:
            resp = self._client.post(
                self._url,
                headers={"api-key": self._api_key or "", "Content-Type": "application/json"},
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 600,
                },
            )
        except httpx.HTTPError:
            logger.exception("Azure OpenAI request failed; using fallback.")
            return None
        if resp.status_code >= 400:
            logger.warning("Azure OpenAI returned %s; using fallback.", resp.status_code)
            return None
        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError):
            logger.exception("Unexpected Azure OpenAI response; using fallback.")
            return None
        return (content or "").strip() or None


def build_provider(
    settings: Settings, *, client: httpx.Client | None = None
) -> TextProvider | None:
    """Select and construct the configured provider (or ``None`` if unavailable)."""
    choice = (settings.ai_provider or "auto").lower()

    if choice in ("azure", "azure_openai"):
        if settings.azure_openai_enabled:
            return AzureOpenAIProvider(settings, client=client)
        logger.warning("AI_PROVIDER=azure but Azure OpenAI isn't configured.")
        return None
    if choice == "gemini":
        return GeminiProvider(settings) if settings.gemini_enabled else None

    # "auto": prefer Azure when configured, else Gemini, else nothing.
    if settings.azure_openai_enabled:
        return AzureOpenAIProvider(settings, client=client)
    if settings.gemini_enabled:
        return GeminiProvider(settings)
    return None
