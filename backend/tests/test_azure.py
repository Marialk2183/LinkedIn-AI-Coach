"""Azure-integration slice: provider selection, Azure OpenAI, artifact storage.

All offline — Azure OpenAI is exercised through ``httpx.MockTransport`` and the
artifact store through the local filesystem fallback.
"""

import httpx
import pytest
from fastapi.testclient import TestClient

import main
from config import Settings
from ml.synthesize import ARCHETYPES
from routes.deps import get_artifact_store
from services.report_service import REPORT_VERSION
from services.ai_providers import (
    AzureOpenAIProvider,
    GeminiProvider,
    build_provider,
)
from services.ai_service import AIService
from services.storage import LocalArtifactStore, build_store


def _no_ai_settings(monkeypatch) -> Settings:
    """Settings with no AI provider configured (empty env overrides .env)."""
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)
    return Settings()


def _azure_settings(monkeypatch, provider="auto") -> Settings:
    monkeypatch.setenv("AI_PROVIDER", provider)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://acme.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "secret-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    return Settings()


def _ok_handler(content="Rewritten | Python | SQL"):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["api-key"] == "secret-key"
        assert "chat/completions" in str(request.url)
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    return handler


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# ----------------------------- Azure OpenAI provider ----------------------------- #
def test_azure_provider_generates(monkeypatch):
    s = _azure_settings(monkeypatch)
    assert s.azure_openai_enabled
    p = AzureOpenAIProvider(s, client=_client(_ok_handler("Hello world")))
    assert p.generate("hi") == "Hello world"


def test_azure_provider_http_error_falls_back(monkeypatch):
    s = _azure_settings(monkeypatch)
    p = AzureOpenAIProvider(s, client=_client(lambda r: httpx.Response(429, text="busy")))
    assert p.generate("hi") is None


def test_azure_provider_malformed_response_falls_back(monkeypatch):
    s = _azure_settings(monkeypatch)
    p = AzureOpenAIProvider(s, client=_client(lambda r: httpx.Response(200, json={"x": 1})))
    assert p.generate("hi") is None


# ----------------------------- provider selection -------------------------------- #
def test_build_provider_auto_prefers_azure(monkeypatch):
    s = _azure_settings(monkeypatch, provider="auto")
    provider = build_provider(s, client=_client(_ok_handler()))
    assert isinstance(provider, AzureOpenAIProvider)
    assert provider.name == "azure"


def test_build_provider_forced_azure_without_config_is_none(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "azure")
    assert build_provider(_no_ai_settings(monkeypatch)) is None


def test_build_provider_none_when_nothing_configured(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "auto")
    assert build_provider(_no_ai_settings(monkeypatch)) is None


def test_build_provider_forced_gemini(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    provider = build_provider(Settings())
    assert isinstance(provider, GeminiProvider)


# ----------------------------- AIService delegation ------------------------------ #
def test_ai_service_uses_injected_azure_provider(monkeypatch):
    s = _azure_settings(monkeypatch)
    ai = AIService(s, provider=AzureOpenAIProvider(s, client=_client(_ok_handler("Punchy | AI | ML"))))
    assert ai.enabled and ai.provider_name == "azure"
    headline, ai_generated = ai.improve_headline("Student", ["python"], "AI Engineer")
    assert ai_generated is True and headline == "Punchy | AI | ML"


def test_ai_service_without_provider_falls_back(monkeypatch):
    ai = AIService(_no_ai_settings(monkeypatch))
    assert ai.provider_name == "fallback"
    headline, ai_generated = ai.improve_headline("Student", ["python"], None)
    assert ai_generated is False and "|" in headline  # deterministic template


# ----------------------------- artifact storage ---------------------------------- #
def test_local_store_round_trip(tmp_path):
    store = LocalArtifactStore(tmp_path)
    loc = store.save("reports/7.pdf", b"%PDF-1.4 data", "application/pdf")
    assert loc.endswith("7.pdf")
    assert store.load("reports/7.pdf") == b"%PDF-1.4 data"
    assert store.load("reports/missing.pdf") is None


def test_local_store_rejects_traversal(tmp_path):
    store = LocalArtifactStore(tmp_path)
    with pytest.raises(ValueError):
        store.save("../escape.pdf", b"x")


def test_build_store_defaults_to_local(monkeypatch):
    monkeypatch.delenv("AZURE_BLOB_CONNECTION_STRING", raising=False)
    monkeypatch.setenv("ARTIFACT_STORE", "auto")
    assert build_store(Settings()).name == "local"


# ----------------------------- report caching (end-to-end) ----------------------- #
def test_report_pdf_is_cached_in_store(tmp_path):
    store = LocalArtifactStore(tmp_path)
    app = main.app
    app.dependency_overrides[get_artifact_store] = lambda: store
    try:
        client = TestClient(app)
        result = client.post(
            "/api/v1/analyze",
            json={"source_type": "text", "profile_text": ARCHETYPES["average"]},
        ).json()
        analysis_id = result["analysis_id"]
        key = f"reports/v{REPORT_VERSION}/{analysis_id}.pdf"

        # First request builds + caches the PDF.
        r1 = client.get(f"/api/v1/analyses/{analysis_id}/report.pdf")
        assert r1.status_code == 200 and r1.content[:4] == b"%PDF"
        assert store.load(key) is not None

        # Second request is served from the cache: seed a sentinel and confirm
        # it's returned verbatim rather than rebuilt.
        store.save(key, b"%PDF-cached-sentinel", "application/pdf")
        r2 = client.get(f"/api/v1/analyses/{analysis_id}/report.pdf")
        assert r2.content == b"%PDF-cached-sentinel"
    finally:
        app.dependency_overrides.pop(get_artifact_store, None)


def test_health_reports_providers():
    client = TestClient(main.app)
    body = client.get("/health").json()
    assert body["artifact_store"] in ("local", "azure_blob")
    assert body["ai_provider"] in ("fallback", "gemini", "azure")
