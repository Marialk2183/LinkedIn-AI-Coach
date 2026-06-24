"""Compliant external-source fetching (the reusable scrape/fetch service).

This is *not* a LinkedIn scraper. LinkedIn prohibits scraping, so that path
stays on the existing export-`.zip` / "Save to PDF" upload. What this service
does is pull a candidate's *public, compliant* material and normalize it into
profile-style text that flows through the same `parse → score` pipeline:

* **GitHub** — via the **official REST API** (``api.github.com``), never HTML
  scraping. Profile bio + top repositories become headline/about/projects/skills
  text. Honors ``GITHUB_TOKEN`` for higher rate limits when set.
* **Portfolio sites & job postings** — a plain static fetch (``WebFetcher``) that
  pulls the page HTML and reduces it to readable text with the stdlib HTML
  parser (no heavyweight dependency).

Design notes (abstraction-first, per the Azure upgrade direction):

* Every fetcher takes an injected :class:`httpx.Client`, so tests run fully
  offline with ``httpx.MockTransport`` and a rendered fetcher (Playwright) can
  be slotted behind the same :class:`SourceFetcher` interface later without
  touching callers.
* Pure-ish and framework-free: no FastAPI import here. Failures raise
  :class:`UnsupportedSource` (a ``ValueError`` → 422) for things the caller got
  wrong, or :class:`FetchError` (→ 502) for upstream/network problems.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from config import Settings
from models.domain import FetchedSource

# Hosts we must never fetch — scraping them violates their ToS. The message
# points the user at the compliant alternative we already support.
_BLOCKED_HOSTS = {
    "linkedin.com": (
        "LinkedIn prohibits scraping, so we don't fetch it. Upload your LinkedIn "
        "data-export .zip or a 'Save to PDF' of your profile instead."
    ),
}

# GitHub path segments that are features, not usernames.
_GITHUB_RESERVED = {
    "marketplace", "explore", "topics", "trending", "collections", "events",
    "sponsors", "settings", "notifications", "orgs", "about", "pricing", "features",
}

_MAX_REPOS = 12  # top repos summarized into the profile text


class ScrapeError(Exception):
    """Base class for fetch failures."""


class UnsupportedSource(ScrapeError, ValueError):
    """The URL is unsupported, blocked (LinkedIn), or malformed → 422."""


class FetchError(ScrapeError):
    """An upstream/network error while fetching a valid source → 502."""


# --------------------------------------------------------------------------- #
# HTML → text (stdlib only)
# --------------------------------------------------------------------------- #
class _TextExtractor(HTMLParser):
    """Collect visible text, dropping script/style/nav noise and the <title>."""

    _SKIP = {"script", "style", "noscript", "template", "svg"}
    _BLOCK = {
        "p", "div", "section", "article", "header", "footer", "li", "ul", "ol",
        "h1", "h2", "h3", "h4", "h5", "h6", "br", "tr", "table",
    }

    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._chunks: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        if tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        if tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
            return
        if self._skip_depth:
            return
        if data.strip():
            self._chunks.append(data)

    def text(self) -> str:
        joined = "".join(self._chunks)
        # Collapse intra-line whitespace, then squeeze blank-line runs.
        lines = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in joined.splitlines()]
        out: list[str] = []
        for ln in lines:
            if ln or (out and out[-1]):
                out.append(ln)
        return "\n".join(out).strip()


def html_to_text(html: str) -> tuple[str, str]:
    """Return ``(title, text)`` extracted from an HTML document."""
    parser = _TextExtractor()
    try:
        parser.feed(html)
    except Exception:  # noqa: BLE001 - malformed HTML shouldn't 500
        pass
    return parser.title.strip(), parser.text()


# --------------------------------------------------------------------------- #
# Fetchers
# --------------------------------------------------------------------------- #
class GitHubFetcher:
    """Summarize a GitHub user from the official REST API."""

    API = "https://api.github.com"

    def __init__(self, client: httpx.Client, *, token: str | None = None) -> None:
        self._client = client
        self._token = token

    @staticmethod
    def username_from_url(url: str) -> str | None:
        host, path = _host(url), urlparse(_normalize(url)).path.strip("/")
        if host not in ("github.com", "www.github.com", "api.github.com"):
            return None
        if not path:
            return None
        first = path.split("/")[0]
        if host == "api.github.com":  # api.github.com/users/<name>
            parts = path.split("/")
            first = parts[1] if len(parts) > 1 and parts[0] == "users" else ""
        if not first or first.lower() in _GITHUB_RESERVED:
            return None
        return first

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/vnd.github+json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def fetch(self, url: str) -> FetchedSource:
        user = self.username_from_url(url)
        if not user:
            raise UnsupportedSource("That doesn't look like a GitHub profile URL.")
        profile = self._get(f"{self.API}/users/{user}")
        if profile.get("type") == "Organization":
            raise UnsupportedSource(
                "That's a GitHub organization, not a user profile."
            )
        repos = self._get(
            f"{self.API}/users/{user}/repos",
            params={"sort": "pushed", "per_page": 100, "type": "owner"},
        )
        return self._summarize(user, profile, repos if isinstance(repos, list) else [])

    def _get(self, url: str, *, params: dict | None = None):
        try:
            resp = self._client.get(url, headers=self._headers(), params=params)
        except httpx.HTTPError as exc:
            raise FetchError(f"Couldn't reach GitHub: {exc}") from exc
        if resp.status_code == 404:
            raise UnsupportedSource("No public GitHub user with that name.")
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            raise FetchError(
                "GitHub rate limit reached. Set GITHUB_TOKEN or try again later."
            )
        if resp.status_code >= 400:
            raise FetchError(f"GitHub returned {resp.status_code}.")
        return resp.json()

    def _summarize(self, user: str, profile: dict, repos: list[dict]) -> FetchedSource:
        owned = [r for r in repos if not r.get("fork")]
        owned.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)
        top = owned[:_MAX_REPOS]

        name = profile.get("name") or user
        bio = (profile.get("bio") or "").strip()
        total_stars = sum(r.get("stargazers_count", 0) for r in owned)

        # Languages, most-used first, as a stand-in for a skills section.
        langs: dict[str, int] = {}
        for r in owned:
            lang = r.get("language")
            if lang:
                langs[lang] = langs.get(lang, 0) + 1
        skills = sorted(langs, key=lambda k: langs[k], reverse=True)
        topics = sorted(
            {t for r in top for t in (r.get("topics") or [])}
        )

        parts = [name]
        headline = bio or f"{name} on GitHub — {profile.get('public_repos', 0)} repos"
        parts.append(headline)

        about_bits = []
        if bio:
            about_bits.append(bio)
        loc = profile.get("location")
        company = profile.get("company")
        if company:
            about_bits.append(f"Works at {company}.")
        if loc:
            about_bits.append(f"Based in {loc}.")
        about_bits.append(
            f"Public GitHub: {profile.get('public_repos', 0)} repositories, "
            f"{total_stars} total stars, {profile.get('followers', 0)} followers."
        )
        parts.append("About\n" + " ".join(about_bits))

        if top:
            block = ["Projects"]
            for r in top:
                desc = (r.get("description") or "").strip()
                meta = []
                if r.get("language"):
                    meta.append(r["language"])
                if r.get("stargazers_count"):
                    meta.append(f"{r['stargazers_count']}★")
                suffix = f" ({', '.join(meta)})" if meta else ""
                block.append(f"- {r.get('name', '')}{suffix}: {desc}".rstrip(": ").rstrip())
            parts.append("\n".join(block))

        if skills or topics:
            parts.append("Skills\n" + ", ".join(skills + topics))

        text = "\n\n".join(parts)
        meta: dict[str, str | int | float] = {
            "username": user,
            "public_repos": int(profile.get("public_repos", 0) or 0),
            "followers": int(profile.get("followers", 0) or 0),
            "total_stars": int(total_stars),
            "top_languages": ", ".join(skills[:8]),
        }
        return FetchedSource(
            url=f"https://github.com/{user}",
            kind="github",
            title=f"{name} (@{user}) · GitHub",
            text=text,
            metadata=meta,
        )


class WebFetcher:
    """Static fetch + text extraction for portfolio sites and job postings."""

    def __init__(self, client: httpx.Client, *, max_bytes: int) -> None:
        self._client = client
        self._max_bytes = max_bytes

    def fetch(self, url: str) -> FetchedSource:
        target = _normalize(url)
        try:
            resp = self._client.get(target, follow_redirects=True)
        except httpx.HTTPError as exc:
            raise FetchError(f"Couldn't reach that page: {exc}") from exc
        if resp.status_code >= 400:
            raise FetchError(f"That page returned {resp.status_code}.")

        content_type = resp.headers.get("content-type", "")
        body = resp.content[: self._max_bytes]

        if "html" in content_type or body[:200].lstrip().lower().startswith(
            (b"<!doctype", b"<html")
        ):
            title, text = html_to_text(body.decode("utf-8", errors="ignore"))
        else:
            title, text = "", body.decode("utf-8", errors="ignore").strip()

        if len(text) < 40:
            raise UnsupportedSource(
                "Couldn't read meaningful text from that page. If it needs a login "
                "or renders with JavaScript, paste the content instead."
            )
        title = title or urlparse(target).netloc
        return FetchedSource(
            url=target,
            kind="web",
            title=title,
            text=text,
            metadata={"host": urlparse(target).netloc, "char_count": len(text)},
        )


# --------------------------------------------------------------------------- #
# Dispatcher
# --------------------------------------------------------------------------- #
class ScrapeService:
    """Detect a URL's compliant source kind and delegate to the right fetcher."""

    def __init__(
        self, settings: Settings, *, client: httpx.Client | None = None
    ) -> None:
        self._settings = settings
        self._client = client or httpx.Client(
            timeout=settings.fetch_timeout_seconds,
            headers={"User-Agent": settings.fetch_user_agent},
        )
        self._github = GitHubFetcher(self._client, token=settings.github_token)
        self._web = WebFetcher(self._client, max_bytes=settings.fetch_max_bytes)

    def detect_kind(self, url: str) -> str:
        host = _host(url)
        if not host:
            raise UnsupportedSource("Enter a valid http(s) URL.")
        for blocked, message in _BLOCKED_HOSTS.items():
            if host == blocked or host.endswith("." + blocked):
                raise UnsupportedSource(message)
        if host in ("github.com", "www.github.com", "api.github.com"):
            return "github"
        return "web"

    def fetch(self, url: str, *, kind: str | None = None) -> FetchedSource:
        url = (url or "").strip()
        if not url:
            raise UnsupportedSource("A URL is required.")
        resolved = kind or self.detect_kind(url)
        if resolved == "github":
            return self._github.fetch(url)
        if resolved == "web":
            return self._web.fetch(url)
        raise UnsupportedSource(f"Unknown source kind: {resolved!r}.")


# --------------------------------------------------------------------------- #
# URL helpers
# --------------------------------------------------------------------------- #
def _normalize(url: str) -> str:
    """Add a scheme if the user pasted a bare host/path."""
    url = (url or "").strip()
    if url and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "https://" + url
    return url


def _host(url: str) -> str:
    netloc = urlparse(_normalize(url)).netloc.lower()
    return netloc.split("@")[-1].split(":")[0]
