"""Safe web-content retrieval for URL-only mobile shares."""

from __future__ import annotations

import ipaddress
import json
import re
import socket
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import urljoin, urlparse

import httpx

from autoknowledge_lite.models import ShareRecord

MAX_CONTENT_BYTES = 2_000_000
MAX_REDIRECTS = 5
JSON_STRING_PATTERN = re.compile(r'"(?:[^"\\]|\\.)*"')


class ContentFetchError(RuntimeError):
    """Raised when a shared URL cannot be retrieved safely."""


class ContentFetcher(Protocol):
    def fetch(self, url: str) -> str: ...


class HttpContentFetcher:
    """Retrieve public HTTP(S) text while blocking internal-network targets."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            timeout=20,
            headers={"User-Agent": "AutoKnowledge-Lite/0.1"},
        )

    def fetch(self, url: str) -> str:
        current_url = url
        for _ in range(MAX_REDIRECTS + 1):
            _validate_public_url(current_url)
            try:
                response = self.client.get(current_url, follow_redirects=False)
            except httpx.HTTPError as error:
                raise ContentFetchError("Unable to retrieve shared URL.") from error
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise ContentFetchError("Shared URL returned an invalid redirect.")
                current_url = urljoin(current_url, location)
                continue
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                raise ContentFetchError(
                    "Shared URL returned an error response."
                ) from error
            content_type = response.headers.get("content-type", "").lower()
            if not (content_type.startswith("text/") or "json" in content_type):
                raise ContentFetchError("Shared URL is not textual content.")
            if len(response.content) > MAX_CONTENT_BYTES:
                raise ContentFetchError("Shared URL content is too large.")
            return extract_web_content(str(response.url), response.text)
        raise ContentFetchError("Shared URL redirected too many times.")


def should_fetch_content(record: ShareRecord) -> bool:
    if not record.source_url:
        return False
    normalized_content = record.content.strip().rstrip("/\n")
    normalized_url = record.source_url.strip().rstrip("/")
    return normalized_content == normalized_url


def extract_web_content(url: str, html: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host in {"chatgpt.com", "www.chatgpt.com"} and urlparse(url).path.startswith(
        ("/s/", "/share/")
    ):
        shared_content = _extract_chatgpt_share(html)
        if shared_content:
            return shared_content

    parser = _VisibleTextParser()
    parser.feed(html)
    text = "\n".join(line for line in parser.lines if line)
    if not text.strip():
        raise ContentFetchError("Shared page contains no readable text.")
    return text[:100_000]


def _extract_chatgpt_share(html: str) -> str | None:
    candidates: list[str] = []
    pending = [html]
    for _ in range(2):
        next_pending: list[str] = []
        for source in pending:
            for token in JSON_STRING_PATTERN.findall(source):
                if "\\n" not in token and '\\"' not in token:
                    continue
                try:
                    value = json.loads(token)
                except json.JSONDecodeError:
                    continue
                if not isinstance(value, str):
                    continue
                normalized = value.strip()
                if normalized.startswith(("[{", '{"')):
                    next_pending.append(normalized)
                    continue
                if normalized.startswith(
                    (
                        "You are ",
                        "Knowledge cutoff:",
                        "<|system|>",
                        "First-response output contract",
                    )
                ):
                    continue
                if len(normalized) >= 200 and "\n" in normalized:
                    candidates.append(normalized)
        pending = next_pending
    if not candidates:
        return None
    return max(candidates, key=len)[:100_000]


def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ContentFetchError("Shared URL must be HTTP or HTTPS.")
    try:
        default_port = 443 if parsed.scheme == "https" else 80
        addresses = {
            result[4][0]
            for result in socket.getaddrinfo(
                parsed.hostname,
                parsed.port or default_port,
            )
        }
    except socket.gaierror as error:
        raise ContentFetchError("Shared URL host could not be resolved.") from error
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ContentFetchError("Shared URL points to a non-public address.")


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        normalized = " ".join(data.split())
        if normalized:
            self.lines.append(normalized)
