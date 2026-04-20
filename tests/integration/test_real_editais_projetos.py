from __future__ import annotations

import os
import socket
import ssl
from typing import Final
from urllib.parse import urlparse

import certifi
import httpx
import pytest

from fapes_lib.controllers.api_client import FapesApiClient
from fapes_lib.controllers.authenticator import FapesAuthenticator
from fapes_lib.controllers.extractor import FapesExtractor
from fapes_lib.controllers.query_controller import (
    FapesQueryController,
    QueryParameterValue,
)
from fapes_lib.infrastructure.http_client import FapesHttpClient
from fapes_lib.models import FapesResponseEnvelope
from fapes_lib.settings import FapesSettings

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FAPES_RUN_INTEGRATION") != "1",
        reason="set FAPES_RUN_INTEGRATION=1 to run live FAPES integration tests",
    ),
]

_DEFAULT_EDITAIS_LIMIT: Final = 3
_TLS_PREFLIGHT_TIMEOUT_SECONDS: Final = 10.0

# The current FAPES leaf certificate advertises this intermediate in AIA over
# HTTP; the HTTPS equivalent keeps certificate validation enabled end to end.
_GLOBALSIGN_RSA_OV_SSL_CA_2018_URL: Final = (
    "https://secure.globalsign.com/cacert/gsrsaovsslca2018.crt"
)


class LimitedEditaisApiClient:
    def __init__(self, *, api_client: FapesApiClient, limit: int) -> None:
        self._api_client = api_client
        self.limit = limit

    def listar_setores(self) -> FapesResponseEnvelope:
        return self._api_client.listar_setores()

    def listar_modalidade_bolsas(self) -> FapesResponseEnvelope:
        return self._api_client.listar_modalidade_bolsas()

    def listar_situacao_projeto(self) -> FapesResponseEnvelope:
        return self._api_client.listar_situacao_projeto()

    def listar_editais(self) -> FapesResponseEnvelope:
        envelope = self._api_client.listar_editais()
        limited_data = envelope.data[: self.limit]
        return FapesResponseEnvelope(
            data=limited_data,
            encontrado=1 if limited_data else 0,
            msg=envelope.msg,
            erro=envelope.erro,
            qtd=len(limited_data),
            extra=dict(envelope.extra),
        )

    def listar_edital_chamadas(
        self,
        codedt: QueryParameterValue,
    ) -> FapesResponseEnvelope:
        return self._api_client.listar_edital_chamadas(codedt)

    def listar_projetos(
        self,
        codedt: QueryParameterValue,
    ) -> FapesResponseEnvelope:
        return self._api_client.listar_projetos(codedt)

    def listar_projeto_bolsas(
        self,
        codprj: QueryParameterValue,
    ) -> FapesResponseEnvelope:
        return self._api_client.listar_projeto_bolsas(codprj)

    def listar_bolsistas(
        self,
        codprj: QueryParameterValue,
    ) -> FapesResponseEnvelope:
        return self._api_client.listar_bolsistas(codprj)


def test_live_extractor_fetches_limited_editais_with_projects() -> None:
    settings = FapesSettings.from_env()
    http_client = FapesHttpClient(
        base_url=settings.base_url,
        timeout=settings.timeout_seconds,
        transport=_secure_http_transport(settings),
    )
    authenticator = FapesAuthenticator(settings=settings, http_client=http_client)
    token = authenticator.authenticate()
    query_controller = FapesQueryController(http_client=http_client, token=token.value)
    api_client = FapesApiClient(query_controller=query_controller)
    limited_api_client = LimitedEditaisApiClient(
        api_client=api_client,
        limit=_integration_limit(),
    )
    extractor = FapesExtractor(api_client=limited_api_client)

    result = extractor.extrair_editais_com_projetos()

    editais = result.data["editais"]
    total_projetos = sum(len(edital["projetos"]) for edital in editais)

    assert editais
    assert len(editais) <= limited_api_client.limit
    assert all("projetos" in edital for edital in editais)
    assert result.metadata.success is True
    assert result.metadata.counts["editais"] == len(editais)
    assert result.metadata.counts["projetos"] == total_projetos
    assert "listar_editais" in result.metadata.steps
    assert any(step.startswith("listar_projetos:") for step in result.metadata.steps)


def _integration_limit() -> int:
    raw_limit = os.environ.get("FAPES_INTEGRATION_LIMIT")
    if raw_limit is None:
        return _DEFAULT_EDITAIS_LIMIT

    try:
        limit = int(raw_limit)
    except ValueError:
        pytest.fail("FAPES_INTEGRATION_LIMIT must be a positive integer")

    if limit < 1:
        pytest.fail("FAPES_INTEGRATION_LIMIT must be a positive integer")

    return limit


def _secure_http_transport(settings: FapesSettings) -> httpx.HTTPTransport:
    context = _default_ssl_context()
    if _requires_globalsign_intermediate(settings, context):
        context = _default_ssl_context()
        _load_intermediate_certificate(
            context,
            _GLOBALSIGN_RSA_OV_SSL_CA_2018_URL,
        )
        _verify_https_hosts(settings, context)

    return httpx.HTTPTransport(verify=context)


def _default_ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def _requires_globalsign_intermediate(
    settings: FapesSettings,
    context: ssl.SSLContext,
) -> bool:
    for host, port in _https_hosts(settings):
        try:
            _verify_tls_host(host, port, context)
        except ssl.SSLCertVerificationError:
            return True

    return False


def _verify_https_hosts(settings: FapesSettings, context: ssl.SSLContext) -> None:
    for host, port in _https_hosts(settings):
        _verify_tls_host(host, port, context)


def _verify_tls_host(host: str, port: int, context: ssl.SSLContext) -> None:
    with (
        socket.create_connection(
            (host, port),
            timeout=_TLS_PREFLIGHT_TIMEOUT_SECONDS,
        ) as sock,
        context.wrap_socket(sock, server_hostname=host),
    ):
        pass


def _load_intermediate_certificate(context: ssl.SSLContext, url: str) -> None:
    response = httpx.get(url, timeout=_TLS_PREFLIGHT_TIMEOUT_SECONDS)
    response.raise_for_status()

    content = response.content
    if b"-----BEGIN CERTIFICATE-----" in content:
        certificate = content.decode("ascii")
    else:
        certificate = ssl.DER_cert_to_PEM_cert(content)

    context.load_verify_locations(cadata=certificate)


def _https_hosts(settings: FapesSettings) -> list[tuple[str, int]]:
    hosts: list[tuple[str, int]] = []
    for url in (settings.auth_url, settings.base_url):
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname is None:
            continue

        host = (parsed.hostname, parsed.port or 443)
        if host not in hosts:
            hosts.append(host)

    return hosts
