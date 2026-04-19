"""Domain-specific exceptions for fapes_lib."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import cast

MASKED_VALUE = "***"

_SENSITIVE_KEY_MARKERS = (
    "senha",
    "password",
    "token",
    "authorization",
    "secret",
    "apikey",
    "jwt",
    "credential",
)
_SENSITIVE_NAME_PATTERN = (
    r"senha|password|token|access[_-]?token|refresh[_-]?token|secret|"
    r"api[_-]?key|apikey|jwt"
)
_AUTHORIZATION_PATTERN = re.compile(
    r"\b(authorization\s*[:=]\s*)(bearer\s+)?([^,\s;]+)",
    re.IGNORECASE,
)
_ASSIGNMENT_PATTERN = re.compile(
    rf"\b(({_SENSITIVE_NAME_PATTERN})\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^,\s;]+)",
    re.IGNORECASE,
)

__all__ = [
    "FapesAuthenticationError",
    "FapesConfigError",
    "FapesEnvelopeError",
    "FapesError",
    "FapesExtractionError",
    "FapesRequestError",
    "FapesResponseError",
    "MASKED_VALUE",
    "mask_sensitive_data",
    "mask_sensitive_text",
]


def mask_sensitive_data(value: object) -> object:
    """Return a copy of value with credential-like fields masked."""

    if isinstance(value, Mapping):
        masked: dict[object, object] = {}
        for key, item in value.items():
            if _is_sensitive_key(key):
                masked[key] = MASKED_VALUE
                continue
            masked[key] = mask_sensitive_data(item)
        return masked

    if isinstance(value, list):
        return [mask_sensitive_data(item) for item in value]

    if isinstance(value, tuple):
        return tuple(mask_sensitive_data(item) for item in value)

    if isinstance(value, str):
        return mask_sensitive_text(value)

    return value


def mask_sensitive_text(
    text: str,
    context: Mapping[str, object] | None = None,
) -> str:
    """Mask sensitive assignments and context values in public text."""

    masked = _mask_sensitive_assignments(text)
    if context is None:
        return masked

    for secret in sorted(_sensitive_values(context), key=len, reverse=True):
        masked = masked.replace(secret, MASKED_VALUE)
    return masked


def _is_sensitive_key(key: object) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
    return any(marker in normalized for marker in _SENSITIVE_KEY_MARKERS)


def _mask_sensitive_assignments(text: str) -> str:
    masked = _AUTHORIZATION_PATTERN.sub(_replace_authorization_secret, text)
    return _ASSIGNMENT_PATTERN.sub(_replace_assignment_secret, masked)


def _replace_authorization_secret(match: re.Match[str]) -> str:
    scheme = match.group(2) or ""
    return f"{match.group(1)}{scheme}{MASKED_VALUE}"


def _replace_assignment_secret(match: re.Match[str]) -> str:
    return f"{match.group(1)}{MASKED_VALUE}"


def _sensitive_values(value: object) -> set[str]:
    values: set[str] = set()

    if isinstance(value, Mapping):
        for key, item in value.items():
            if _is_sensitive_key(key):
                values.update(_scalar_values(item))
                continue
            values.update(_sensitive_values(item))
        return values

    if isinstance(value, list | tuple):
        for item in value:
            values.update(_sensitive_values(item))

    return values


def _scalar_values(value: object) -> set[str]:
    if value is None:
        return set()

    if isinstance(value, Mapping):
        mapping_values: set[str] = set()
        for item in value.values():
            mapping_values.update(_scalar_values(item))
        return mapping_values

    if isinstance(value, list | tuple):
        sequence_values: set[str] = set()
        for item in value:
            sequence_values.update(_scalar_values(item))
        return sequence_values

    secret = str(value)
    if not secret:
        return set()

    return {secret}


class FapesError(Exception):
    """Base exception for all fapes_lib domain errors."""

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        self.message = mask_sensitive_text(message, context)
        self.context = cast(
            dict[str, object],
            mask_sensitive_data(context if context is not None else {}),
        )
        super().__init__(self._public_message())

    def _public_message(self) -> str:
        if not self.context:
            return self.message

        return f"{self.message} | context={self.context}"


class FapesConfigError(FapesError):
    """Raised when FAPES configuration is invalid or incomplete."""


class FapesAuthenticationError(FapesError):
    """Raised when authentication against FAPES fails."""


class FapesRequestError(FapesError):
    """Raised when a request to FAPES cannot be completed."""


class FapesResponseError(FapesError):
    """Raised when a FAPES response cannot be used as expected."""


class FapesEnvelopeError(FapesError):
    """Raised when a FAPES response envelope is invalid."""


class FapesExtractionError(FapesError):
    """Raised when a composed FAPES extraction flow fails."""
