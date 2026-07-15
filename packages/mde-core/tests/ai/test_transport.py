from io import BytesIO
from urllib.error import HTTPError

import pytest

from mde.ai.errors import AITransportError
from mde.ai.transport import UrllibHTTPTransport


def test_http_error_does_not_expose_response_body(monkeypatch) -> None:
    body = b'{"error":{"message":"Incorrect API key provided: sk-secret","type":"invalid_request_error","code":"invalid_api_key"}}'

    def fail(*args, **kwargs):
        raise HTTPError(
            url="https://example.invalid",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=BytesIO(body),
        )

    monkeypatch.setattr("urllib.request.urlopen", fail)

    with pytest.raises(AITransportError) as raised:
        UrllibHTTPTransport().post_json(
            "https://example.invalid",
            headers={"Authorization": "Bearer sk-secret"},
            payload={"model": "test"},
            timeout=1,
        )

    message = str(raised.value)
    assert "sk-secret" not in message
    assert "Incorrect API key" not in message
    assert (
        message
        == "AI endpoint HTTP 401 (type=invalid_request_error, code=invalid_api_key)."
    )
