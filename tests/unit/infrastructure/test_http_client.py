from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from fapes_lib.exceptions import FapesRequestError, FapesResponseError
from fapes_lib.infrastructure.http_client import FapesHttpClient


def test_get_returns_json_and_applies_base_url_timeout_and_headers() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(200, json={"setores": ["pesquisa"]})

    client = FapesHttpClient(
        base_url="https://api.fapes.example/webServicesSig/",
        timeout=2.5,
        headers={"Authorization": "Bearer default-token", "X-Client": "fapes-lib"},
        transport=httpx.MockTransport(handler),
    )

    result = client.get("/setores", headers={"X-Trace-ID": "trace-123"})

    assert result == {"setores": ["pesquisa"]}
    request = captured_requests[0]
    assert request.method == "GET"
    assert str(request.url) == "https://api.fapes.example/webServicesSig/setores"
    assert request.headers["Authorization"] == "Bearer default-token"
    assert request.headers["X-Client"] == "fapes-lib"
    assert request.headers["X-Trace-ID"] == "trace-123"
    assert request.extensions["timeout"] == {
        "connect": 2.5,
        "read": 2.5,
        "write": 2.5,
        "pool": 2.5,
    }


def test_post_sends_json_body_and_returns_json_response() -> None:
    captured_requests: list[httpx.Request] = []
    payload = {"filtro": {"ano": 2026}}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(201, json={"protocolo": "abc-123"})

    client = FapesHttpClient(
        base_url="https://api.fapes.example",
        transport=httpx.MockTransport(handler),
    )

    result = client.post("consultas", json=payload, headers={"X-Mode": "unit"})

    assert result == {"protocolo": "abc-123"}
    request = captured_requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://api.fapes.example/consultas"
    assert json.loads(request.content.decode()) == payload
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["X-Mode"] == "unit"


def test_request_errors_are_wrapped_without_leaking_secrets() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        msg = "Could not connect with token=request-error-secret"
        raise httpx.ConnectError(msg, request=request)

    client = FapesHttpClient(
        base_url="https://api.fapes.example",
        headers={"Authorization": "Bearer header-secret"},
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(FapesRequestError) as exc_info:
        client.get("setores")

    error = exc_info.value
    assert isinstance(error.__cause__, httpx.RequestError)
    assert error.context["method"] == "GET"
    assert error.context["endpoint"] == "setores"
    assert error.context["headers"] == {"Authorization": "***"}
    assert "GET" in str(error)
    assert "setores" in str(error)
    assert "request-error-secret" not in str(error)
    assert "header-secret" not in str(error)


def test_http_error_responses_are_wrapped_without_leaking_secrets() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"detail": "invalid token=response-secret"},
            request=request,
        )

    client = FapesHttpClient(
        base_url="https://api.fapes.example",
        headers={"Authorization": "Bearer header-secret"},
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(FapesResponseError) as exc_info:
        client.get("setores")

    error = exc_info.value
    assert isinstance(error.__cause__, httpx.HTTPStatusError)
    assert error.context["method"] == "GET"
    assert error.context["endpoint"] == "setores"
    assert error.context["status_code"] == 401
    assert error.context["headers"] == {"Authorization": "***"}
    assert "401" in str(error)
    assert "setores" in str(error)
    assert "response-secret" not in str(error)
    assert "header-secret" not in str(error)


def test_invalid_json_responses_are_wrapped_as_response_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"token=json-secret", request=request)

    client = FapesHttpClient(
        base_url="https://api.fapes.example",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(FapesResponseError) as exc_info:
        client.get("setores")

    error = exc_info.value
    assert error.context["method"] == "GET"
    assert error.context["endpoint"] == "setores"
    assert "json-secret" not in str(error)


def test_json_response_can_be_a_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": 1}, {"id": 2}], request=request)

    client = FapesHttpClient(
        base_url="https://api.fapes.example",
        transport=httpx.MockTransport(handler),
    )

    result: Any = client.get("setores")

    assert result == [{"id": 1}, {"id": 2}]
