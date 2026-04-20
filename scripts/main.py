"""Download projects for all FAPES editais into one JSON file per edital."""

from __future__ import annotations

import argparse
import logging
import socket
import ssl
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol
from urllib.parse import urlparse

import certifi
import httpx

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if _SRC_DIR.exists():
    sys.path.insert(0, str(_SRC_DIR))

from fapes_lib.controllers import (  # noqa: E402
    FapesApiClient,
    FapesAuthenticator,
    FapesExtractor,
    FapesQueryController,
)
from fapes_lib.controllers.extractor import FapesExtractionResult  # noqa: E402
from fapes_lib.infrastructure.http_client import FapesHttpClient  # noqa: E402
from fapes_lib.settings import FapesSettings  # noqa: E402

_DEFAULT_OUTPUT_DIR: Final = Path("downloads/projetos_por_edital")
_DEFAULT_MAX_WORKERS: Final = 4
_DEFAULT_RETRIES: Final = 2
_TLS_PREFLIGHT_TIMEOUT_SECONDS: Final = 10.0
_GLOBALSIGN_RSA_OV_SSL_CA_2018_URL: Final = (
    "https://secure.globalsign.com/cacert/gsrsaovsslca2018.crt"
)


class ProjectExtractor(Protocol):
    def extrair_projetos_dos_editais_em_threads(
        self,
        *,
        destination_dir: str | Path,
        max_workers: int | None = None,
        retry_attempts: int = 0,
        skip_existing: bool = False,
    ) -> FapesExtractionResult:
        """Download projects by edital and write one JSON file per edital."""


@dataclass(frozen=True, slots=True)
class MainArgs:
    output_dir: Path
    max_workers: int
    retries: int
    skip_existing: bool
    log_level: str


def run(
    argv: Sequence[str] | None = None,
    *,
    extractor_factory: Callable[[], ProjectExtractor] | None = None,
) -> int:
    """Run the downloader and return a process exit code."""

    args = _parse_args(argv)
    _configure_logging(args.log_level)

    factory = extractor_factory if extractor_factory is not None else _build_extractor
    extractor = factory()
    result = extractor.extrair_projetos_dos_editais_em_threads(
        destination_dir=args.output_dir,
        max_workers=args.max_workers,
        retry_attempts=args.retries,
        skip_existing=args.skip_existing,
    )

    _print_summary(result, args.output_dir)
    return 0


def _build_extractor() -> FapesExtractor:
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

    return FapesExtractor(
        api_client=api_client,
        logger=logging.getLogger("fapes_lib.main"),
    )


def _parse_args(argv: Sequence[str] | None) -> MainArgs:
    parser = argparse.ArgumentParser(
        description="Baixa os projetos de todos os editais da FAPES.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_DEFAULT_OUTPUT_DIR,
        help=(
            f"Diretorio de destino dos JSONs por edital. Padrao: {_DEFAULT_OUTPUT_DIR}"
        ),
    )
    parser.add_argument(
        "--max-workers",
        type=_positive_int,
        default=_DEFAULT_MAX_WORKERS,
        help=(
            "Quantidade maxima de consultas simultaneas de projetos. "
            f"Padrao: {_DEFAULT_MAX_WORKERS}"
        ),
    )
    parser.add_argument(
        "--retries",
        type=_non_negative_int,
        default=_DEFAULT_RETRIES,
        help=(
            "Tentativas extras para cada consulta de projetos que falhar. "
            f"Padrao: {_DEFAULT_RETRIES}"
        ),
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Nao consulta nem sobrescreve arquivos de edital que ja existem.",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        default="INFO",
        help="Nivel de logging. Padrao: INFO",
    )
    namespace = parser.parse_args(argv)
    return MainArgs(
        output_dir=namespace.output_dir,
        max_workers=namespace.max_workers,
        retries=namespace.retries,
        skip_existing=namespace.skip_existing,
        log_level=namespace.log_level,
    )


def _positive_int(raw_value: str) -> int:
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("deve ser um numero inteiro positivo") from exc

    if value < 1:
        raise argparse.ArgumentTypeError("deve ser um numero inteiro positivo")

    return value


def _non_negative_int(raw_value: str) -> int:
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "deve ser um numero inteiro nao negativo"
        ) from exc

    if value < 0:
        raise argparse.ArgumentTypeError("deve ser um numero inteiro nao negativo")

    return value


def _configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _print_summary(result: FapesExtractionResult, output_dir: Path) -> None:
    counts = result.metadata.counts
    print("Download concluido.")
    print(f"Destino: {output_dir}")
    print(f"Editais: {counts.get('editais', 0)}")
    print(f"Projetos: {counts.get('projetos', 0)}")
    print(f"Arquivos: {counts.get('arquivos', 0)}")
    if counts.get("arquivos_existentes", 0):
        print(f"Arquivos existentes: {counts.get('arquivos_existentes', 0)}")


def _secure_http_transport(settings: FapesSettings) -> httpx.HTTPTransport:
    context = _default_ssl_context()
    if _requires_globalsign_intermediate(settings, context):
        context = _default_ssl_context()
        _load_intermediate_certificate(context, _GLOBALSIGN_RSA_OV_SSL_CA_2018_URL)
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


if __name__ == "__main__":
    raise SystemExit(run())
