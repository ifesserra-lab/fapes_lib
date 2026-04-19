"""Configuration loading for fapes_lib."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values

from fapes_lib.exceptions import FapesConfigError

DEFAULT_BASE_URL = "https://servicos.fapes.es.gov.br/webServicesSig/"
DEFAULT_TIMEOUT_SECONDS = 30.0

_REQUIRED_ENV_VARS = ("FAPES_AUTH_URL", "FAPES_USUARIO", "FAPES_SENHA")

__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT_SECONDS",
    "FapesSettings",
]


class _UseDefaultDotenv:
    pass


_USE_DEFAULT_DOTENV = _UseDefaultDotenv()


@dataclass(frozen=True, slots=True)
class FapesSettings:
    """Runtime settings required to authenticate and query the FAPES API."""

    auth_url: str
    usuario: str
    senha: str = field(repr=False)
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_env(
        cls,
        *,
        dotenv_path: str | Path | None | _UseDefaultDotenv = _USE_DEFAULT_DOTENV,
        environ: Mapping[str, str] | None = None,
    ) -> FapesSettings:
        """Load settings from a dotenv file and environment mapping.

        When `environ` is injected for tests, `.env` is not read unless
        `dotenv_path` is explicitly provided.
        """

        values = _load_environment(dotenv_path=dotenv_path, environ=environ)
        _validate_required_values(values)

        auth_url = _validated_url(values["FAPES_AUTH_URL"], "FAPES_AUTH_URL")
        base_url = _validated_url(
            values.get("FAPES_BASE_URL", DEFAULT_BASE_URL),
            "FAPES_BASE_URL",
        )

        return cls(
            auth_url=auth_url,
            usuario=values["FAPES_USUARIO"],
            senha=values["FAPES_SENHA"],
            base_url=_normalize_base_url(base_url),
            timeout_seconds=_validated_timeout(values.get("FAPES_TIMEOUT_SECONDS")),
        )


def _load_environment(
    *,
    dotenv_path: str | Path | None | _UseDefaultDotenv,
    environ: Mapping[str, str] | None,
) -> dict[str, str]:
    loaded: dict[str, str] = {}
    resolved_dotenv_path = _resolve_dotenv_path(dotenv_path, environ)

    if resolved_dotenv_path is not None:
        loaded.update(_non_empty_dotenv_values(resolved_dotenv_path))

    source_environ = os.environ if environ is None else environ
    loaded.update({key: value for key, value in source_environ.items()})
    return loaded


def _resolve_dotenv_path(
    dotenv_path: str | Path | None | _UseDefaultDotenv,
    environ: Mapping[str, str] | None,
) -> Path | None:
    if isinstance(dotenv_path, _UseDefaultDotenv):
        if environ is not None:
            return None
        return Path(".env")

    if dotenv_path is None:
        return None

    return Path(dotenv_path)


def _non_empty_dotenv_values(dotenv_path: Path) -> dict[str, str]:
    return {
        key: value
        for key, value in dotenv_values(dotenv_path).items()
        if value is not None
    }


def _validate_required_values(values: Mapping[str, str]) -> None:
    missing = [name for name in _REQUIRED_ENV_VARS if not values.get(name)]
    if not missing:
        return

    raise FapesConfigError(
        f"Missing required FAPES setting: {', '.join(missing)}",
        context={"missing": missing},
    )


def _validated_url(value: str, env_name: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return value

    raise FapesConfigError(
        f"Invalid FAPES setting: {env_name}",
        context={env_name: value},
    )


def _normalize_base_url(value: str) -> str:
    return f"{value.rstrip('/')}/"


def _validated_timeout(raw_value: str | None) -> float:
    if raw_value is None:
        return DEFAULT_TIMEOUT_SECONDS

    try:
        timeout = float(raw_value)
    except ValueError as exc:
        raise FapesConfigError(
            "Invalid FAPES setting: FAPES_TIMEOUT_SECONDS",
            context={"FAPES_TIMEOUT_SECONDS": raw_value},
        ) from exc

    if timeout > 0:
        return timeout

    raise FapesConfigError(
        "Invalid FAPES setting: FAPES_TIMEOUT_SECONDS",
        context={"FAPES_TIMEOUT_SECONDS": raw_value},
    )
