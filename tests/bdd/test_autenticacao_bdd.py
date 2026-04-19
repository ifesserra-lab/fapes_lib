from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, scenario, then, when

from fapes_lib.controllers.authenticator import FapesAuthenticator
from fapes_lib.infrastructure.http_client import JsonValue
from fapes_lib.settings import FapesSettings


class FakeAuthHttpClient:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def post(
        self,
        endpoint: str,
        *,
        json: JsonValue = None,
    ) -> JsonValue:
        request_payload = json if isinstance(json, dict) else {}
        self.requests.append((endpoint, request_payload))
        return {"token": "jwt-token"}


@pytest.fixture
def context() -> dict[str, Any]:
    return {}


@scenario(
    "../../docs/features/autenticacao.feature",
    "Autenticacao com sucesso",
)
def test_autenticacao_com_sucesso() -> None:
    """Execute the authentication smoke scenario without real network access."""


@given("que a URL de autenticacao da FAPES esta configurada")
def url_de_autenticacao_configurada(context: dict[str, Any]) -> None:
    context["settings"] = FapesSettings(
        auth_url="https://api.fapes.example/webServicesSig/auth.php",
        usuario="service-user",
        senha="secret-password",
        base_url="https://api.fapes.example/webServicesSig/",
        timeout_seconds=10.0,
    )


@given("que as credenciais da FAPES estao configuradas")
def credenciais_configuradas(context: dict[str, Any]) -> None:
    assert context["settings"].usuario == "service-user"
    assert context["settings"].senha == "secret-password"


@given("que a API de autenticacao retorna um token JWT")
def api_de_autenticacao_retorna_token(context: dict[str, Any]) -> None:
    context["http_client"] = FakeAuthHttpClient()


@when("eu solicito um token de autenticacao")
def solicitar_token(context: dict[str, Any]) -> None:
    authenticator = FapesAuthenticator(
        settings=context["settings"],
        http_client=context["http_client"],
    )

    context["authenticator"] = authenticator
    context["token"] = authenticator.authenticate()


@then("a biblioteca deve armazenar o token em memoria")
def token_armazenado_em_memoria(context: dict[str, Any]) -> None:
    assert context["authenticator"].token == context["token"]


@then("o token deve ficar disponivel para as proximas consultas")
def token_disponivel_para_proximas_consultas(context: dict[str, Any]) -> None:
    assert context["token"].value == "jwt-token"
    assert context["http_client"].requests == [
        (
            "https://api.fapes.example/webServicesSig/auth.php",
            {
                "username": "service-user",
                "password": "secret-password",
            },
        )
    ]


@then("o token completo nao deve ser exibido em logs ou mensagens")
def token_nao_exibido_em_mensagens(context: dict[str, Any]) -> None:
    public_text = f"{context['token']!r} {context['token']}"

    assert "jwt-token" not in public_text
    assert "secret-password" not in public_text
