from __future__ import annotations

from typing import Any

import pytest

from fapes_lib.exceptions import FapesAuthenticationError, FapesResponseError
from fapes_lib.settings import FapesSettings


class RecordingHttpClient:
    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.response = response if response is not None else {"token": "jwt-token"}
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def post(
        self,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.requests.append((endpoint, json or {}))
        return self.response


class FailingHttpClient:
    def post(
        self,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise FapesResponseError(
            "FAPES response returned an invalid HTTP status",
            context={
                "endpoint": endpoint,
                "status_code": 401,
                "response_body": "password=invalid-secret token=invalid-token",
                "payload": json or {},
            },
        )


def make_settings() -> FapesSettings:
    return FapesSettings(
        auth_url="https://api.fapes.example/webServicesSig/auth.php",
        usuario="service-user",
        senha="secret-password",
        base_url="https://api.fapes.example/webServicesSig/",
        timeout_seconds=10.0,
    )


def test_authenticator_posts_credentials_and_returns_encapsulated_token() -> None:
    from fapes_lib.controllers.authenticator import FapesAuthenticator, FapesAuthToken

    http_client = RecordingHttpClient(response={"token": "jwt-token"})
    authenticator = FapesAuthenticator(
        settings=make_settings(), http_client=http_client
    )

    token = authenticator.authenticate()

    assert isinstance(token, FapesAuthToken)
    assert token.value == "jwt-token"
    assert authenticator.token == token
    assert http_client.requests == [
        (
            "https://api.fapes.example/webServicesSig/auth.php",
            {
                "username": "service-user",
                "password": "secret-password",
            },
        ),
    ]
    assert "jwt-token" not in repr(token)
    assert "jwt-token" not in str(token)


def test_authenticator_wraps_invalid_credentials_without_leaking_secrets() -> None:
    from fapes_lib.controllers.authenticator import FapesAuthenticator

    authenticator = FapesAuthenticator(
        settings=make_settings(),
        http_client=FailingHttpClient(),
    )

    with pytest.raises(FapesAuthenticationError) as exc_info:
        authenticator.authenticate()

    message = str(exc_info.value)

    assert isinstance(exc_info.value.__cause__, FapesResponseError)
    assert "401" in message
    assert "secret-password" not in message
    assert "invalid-secret" not in message
    assert "invalid-token" not in message
    assert authenticator.token is None


def test_authenticator_rejects_response_without_token() -> None:
    from fapes_lib.controllers.authenticator import FapesAuthenticator

    authenticator = FapesAuthenticator(
        settings=make_settings(),
        http_client=RecordingHttpClient(response={"message": "ok"}),
    )

    with pytest.raises(FapesResponseError) as exc_info:
        authenticator.authenticate()

    assert "token" in str(exc_info.value)
    assert "secret-password" not in str(exc_info.value)
    assert authenticator.token is None


def test_authenticator_rejects_empty_token() -> None:
    from fapes_lib.controllers.authenticator import FapesAuthenticator

    authenticator = FapesAuthenticator(
        settings=make_settings(),
        http_client=RecordingHttpClient(response={"token": ""}),
    )

    with pytest.raises(FapesResponseError):
        authenticator.authenticate()

    assert authenticator.token is None
