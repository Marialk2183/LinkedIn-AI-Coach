"""Offline tests for the compliant fetch/scrape service (httpx.MockTransport)."""

import httpx
import pytest
from fastapi.testclient import TestClient

import main
from config import get_settings
from routes.deps import get_scrape_service
from services.scrape_service import (
    FetchError,
    ScrapeService,
    UnsupportedSource,
    html_to_text,
)

GH_PROFILE = {
    "login": "octocat",
    "name": "The Octocat",
    "type": "User",
    "bio": "Building open-source tools in Python and Go.",
    "company": "@github",
    "location": "Internet",
    "public_repos": 8,
    "followers": 4200,
}
GH_REPOS = [
    {"name": "ml-toolkit", "description": "ML helpers", "language": "Python",
     "stargazers_count": 120, "fork": False, "topics": ["machine-learning", "python"]},
    {"name": "go-cli", "description": "A CLI", "language": "Go",
     "stargazers_count": 30, "fork": False, "topics": []},
    {"name": "someones-fork", "description": "x", "language": "C",
     "stargazers_count": 9999, "fork": True, "topics": []},
]

PORTFOLIO_HTML = """
<!doctype html><html><head><title>Jane Dev — Portfolio</title>
<style>.x{color:red}</style></head>
<body><nav>menu</nav>
<h1>Jane Dev</h1>
<p>Senior Data Scientist building ML systems in Python, SQL and PyTorch.</p>
<script>console.log('ignored')</script>
<p>Led a team of five and shipped recommendation models to production.</p>
</body></html>
"""


def _gh_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/users/octocat":
        return httpx.Response(200, json=GH_PROFILE)
    if path == "/users/octocat/repos":
        return httpx.Response(200, json=GH_REPOS)
    if path == "/users/ghost":
        return httpx.Response(404, json={"message": "Not Found"})
    return httpx.Response(404, json={"message": "Not Found"})


def _make_service(handler) -> ScrapeService:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return ScrapeService(get_settings(), client=client)


# --------------------------- unit: HTML extraction --------------------------- #
def test_html_to_text_drops_script_and_style():
    title, text = html_to_text(PORTFOLIO_HTML)
    assert title == "Jane Dev — Portfolio"
    assert "Senior Data Scientist" in text
    assert "console.log" not in text and "color:red" not in text


# --------------------------- unit: URL detection ----------------------------- #
@pytest.mark.parametrize(
    "url,kind",
    [
        ("https://github.com/octocat", "github"),
        ("github.com/octocat", "github"),
        ("https://janedev.io/about", "web"),
        ("https://careers.acme.com/jobs/123", "web"),
    ],
)
def test_detect_kind(url, kind):
    assert _make_service(_gh_handler).detect_kind(url) == kind


def test_linkedin_is_refused():
    svc = _make_service(_gh_handler)
    with pytest.raises(UnsupportedSource, match="LinkedIn"):
        svc.detect_kind("https://www.linkedin.com/in/jane")
    with pytest.raises(UnsupportedSource, match="LinkedIn"):
        svc.fetch("https://linkedin.com/in/jane")


# --------------------------- GitHub fetch ------------------------------------ #
def test_github_fetch_builds_profile_text():
    src = _make_service(_gh_handler).fetch("https://github.com/octocat")
    assert src.kind == "github"
    assert "The Octocat" in src.text
    assert "About" in src.text and "Projects" in src.text
    # Forks excluded; owned repos summarized, highest-starred first.
    assert "ml-toolkit" in src.text and "someones-fork" not in src.text
    assert src.text.index("ml-toolkit") < src.text.index("go-cli")
    # Languages become a Skills section.
    assert "Python" in src.text and "Go" in src.text
    assert src.metadata["total_stars"] == 150  # 120 + 30, fork ignored
    assert src.metadata["username"] == "octocat"


def test_github_unknown_user_is_422():
    with pytest.raises(UnsupportedSource):
        _make_service(_gh_handler).fetch("https://github.com/ghost")


# --------------------------- Web fetch --------------------------------------- #
def test_web_fetch_extracts_readable_text():
    def handler(request):
        return httpx.Response(
            200, text=PORTFOLIO_HTML, headers={"content-type": "text/html"}
        )

    src = _make_service(handler).fetch("https://janedev.io")
    assert src.kind == "web"
    assert "Jane Dev" in src.title
    assert "recommendation models" in src.text


def test_web_fetch_thin_page_is_422():
    def handler(request):
        return httpx.Response(200, text="<html><body>hi</body></html>",
                              headers={"content-type": "text/html"})

    with pytest.raises(UnsupportedSource):
        _make_service(handler).fetch("https://empty.example")


def test_web_fetch_upstream_error_is_fetcherror():
    def handler(request):
        return httpx.Response(503, text="down")

    with pytest.raises(FetchError):
        _make_service(handler).fetch("https://janedev.io")


# --------------------------- route end-to-end -------------------------------- #
def test_fetch_route(monkeypatch):
    app = main.app
    app.dependency_overrides[get_scrape_service] = lambda: _make_service(_gh_handler)
    try:
        client = TestClient(app)
        r = client.post("/api/v1/fetch", json={"url": "https://github.com/octocat"})
        assert r.status_code == 200
        body = r.json()
        assert body["kind"] == "github"
        assert body["char_count"] > 0 and "The Octocat" in body["text"]

        bad = client.post("/api/v1/fetch", json={"url": "https://linkedin.com/in/x"})
        assert bad.status_code == 422
    finally:
        app.dependency_overrides.pop(get_scrape_service, None)
