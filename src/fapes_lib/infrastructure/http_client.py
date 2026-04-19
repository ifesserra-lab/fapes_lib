"""HTTP transport adapter for FAPES API calls."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeAlias, cast

import httpx

from fapes_lib.exceptions import FapesRequestError, FapesResponseError

JsonValue: TypeAlias = dict[str, Any] | list[Any] | str | int | float | bool | None


class FapesHttpClient:
    """Synchronous HTTP client for FAPES JSON endpoints."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float | httpx.Timeout = 10.0,
        headers: Mapping[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._headers = dict(headers or {})
        self._client = httpx.Client(
            base_url=self._normalize_base_url(base_url),
            timeout=timeout,
            headers=self._headers,
            transport=transport,
        )

    def get(
        self,
        endpoint: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> JsonValue:
        return self._request("GET", endpoint, headers=headers)

    def post(
        self,
        endpoint: str,
        *,
        json: JsonValue = None,
        headers: Mapping[str, str] | None = None,
    ) -> JsonValue:
        return self._request("POST", endpoint, json=json, headers=headers)

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json: JsonValue = None,
        headers: Mapping[str, str] | None = None,
    ) -> JsonValue:
        normalized_endpoint = self._normalize_endpoint(endpoint)
        request_headers = self._headers_for_context(headers)
        context = self._context(method, normalized_endpoint, request_headers)

        try:
            response = self._client.request(
                method,
                normalized_endpoint,
                json=json,
                headers=dict(headers or {}),
            )
            response.raise_for_status()
            return self._json_response(response, context)
        except httpx.HTTPStatusError as exc:
            raise FapesResponseError(
                "FAPES response returned an invalid HTTP status",
                context={
                    **context,
                    "status_code": exc.response.status_code,
                    "response_body": exc.response.text,
                },
            ) from exc
        except httpx.RequestError as exc:
            raise FapesRequestError(
                "FAPES request failed",
                context={**context, "error": str(exc)},
            ) from exc

    def _json_response(
        self,
        response: httpx.Response,
        context: Mapping[str, object],
    ) -> JsonValue:
        try:
            return cast(JsonValue, response.json())
        except ValueError as exc:
            raise FapesResponseError(
                "FAPES response did not contain valid JSON",
                context={
                    **context,
                    "status_code": response.status_code,
                    "response_body": response.text,
                    "error": str(exc),
                },
            ) from exc

    def _headers_for_context(
        self,
        headers: Mapping[str, str] | None,
    ) -> dict[str, str]:
        merged_headers = dict(self._headers)
        merged_headers.update(headers or {})
        return merged_headers

    def _context(
        self,
        method: str,
        endpoint: str,
        headers: Mapping[str, str],
    ) -> dict[str, object]:
        return {
            "method": method,
            "endpoint": endpoint,
            "url": str(self._client.base_url.join(endpoint)),
            "headers": dict(headers),
        }

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        if base_url.endswith("/"):
            return base_url

        return f"{base_url}/"

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        return endpoint.lstrip("/")
