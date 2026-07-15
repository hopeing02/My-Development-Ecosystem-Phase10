from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from mde.ai.errors import AITransportError


def _safe_http_error_detail(body: str) -> str:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return ""
    if not isinstance(parsed, dict):
        return ""
    error = parsed.get("error")
    if not isinstance(error, dict):
        return ""
    parts = []
    error_type = error.get("type")
    error_code = error.get("code")
    if isinstance(error_type, str) and error_type:
        parts.append(f"type={error_type}")
    if isinstance(error_code, str) and error_code:
        parts.append(f"code={error_code}")
    return f" ({', '.join(parts)})" if parts else ""


@dataclass(frozen=True)
class HTTPResponse:
    status: int
    data: dict[str, Any]
    headers: dict[str, str]


class HTTPTransport(Protocol):
    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: float,
    ) -> HTTPResponse: ...


class UrllibHTTPTransport:
    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: float,
    ) -> HTTPResponse:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise AITransportError(
                        "AI endpoint returned a non-object JSON response."
                    )
                return HTTPResponse(
                    status=int(response.status),
                    data=data,
                    headers={
                        key.lower(): value for key, value in response.headers.items()
                    },
                )
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            detail = _safe_http_error_detail(body)
            raise AITransportError(f"AI endpoint HTTP {error.code}{detail}.") from error
        except (urllib.error.URLError, socket.timeout, TimeoutError) as error:
            raise AITransportError(f"AI endpoint request failed: {error}") from error
        except json.JSONDecodeError as error:
            raise AITransportError("AI endpoint returned invalid JSON.") from error
