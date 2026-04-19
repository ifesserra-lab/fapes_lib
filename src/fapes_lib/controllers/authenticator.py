"""Controller for authenticating against the FAPES API."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from fapes_lib.exceptions import FapesAuthenticationError, FapesResponseError
from fapes_lib.infrastructure.http_client import JsonValue
from fapes_lib.settings import FapesSettings

__all__ = [
    "FapesAuthToken",
    "FapesAuthenticator",
]


class FapesAuthPoster(Protocol):
    """HTTP collaborator required by the authenticator."""

    def post(
        self,
        endpoint: str,
        *,
        json: JsonValue = None,
    ) -> JsonValue:
        """Send a JSON POST request to the authentication endpoint."""


@dataclass(frozen=True, slots=True)
class FapesAuthToken:
    """JWT token returned by FAPES with masked textual representation."""

    value: str = field(repr=False)

    def __str__(self) -> str:
        return "***"

    def __repr__(self) -> str:
        return "FapesAuthToken(value='***')"


class FapesAuthenticator:
    """Authenticate with FAPES using configured credentials."""

    def __init__(
        self, *, settings: FapesSettings, http_client: FapesAuthPoster
    ) -> None:
        self._settings = settings
        self._http_client = http_client
        self._token: FapesAuthToken | None = None

    @property
    def token(self) -> FapesAuthToken | None:
        """Return the last successfully authenticated token, if any."""

        return self._token

    def authenticate(self) -> FapesAuthToken:
        """Authenticate and return an encapsulated JWT token.

        Raises:
            FapesAuthenticationError: When FAPES rejects the credentials.
            FapesResponseError: When the response does not contain a token.
        """

        try:
            response = self._http_client.post(
                self._settings.auth_url,
                json={
                    "username": self._settings.usuario,
                    "password": self._settings.senha,
                },
            )
        except FapesResponseError as exc:
            if _is_authentication_status(exc.context):
                raise FapesAuthenticationError(
                    "FAPES authentication failed",
                    context={
                        "auth_url": self._settings.auth_url,
                        "usuario": self._settings.usuario,
                        "senha": self._settings.senha,
                        "status_code": exc.context.get("status_code"),
                        "response": exc.context,
                    },
                ) from exc
            raise

        token_value = _extract_token(response)
        self._token = FapesAuthToken(token_value)
        return self._token


def _is_authentication_status(context: Mapping[str, object]) -> bool:
    return context.get("status_code") in {401, 403}


def _extract_token(response: JsonValue) -> str:
    if not isinstance(response, Mapping):
        raise _missing_token_error(response)

    token = response.get("token")
    if isinstance(token, str) and token:
        return token

    raise _missing_token_error(response)


def _missing_token_error(response: JsonValue) -> FapesResponseError:
    return FapesResponseError(
        "FAPES authentication response did not contain a valid token",
        context={
            "missing": ["token"],
            "response": response,
        },
    )
