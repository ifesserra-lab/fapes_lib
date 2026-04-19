from __future__ import annotations

from typing import Any

import pytest

from fapes_lib.exceptions import FapesRequestError
from fapes_lib.infrastructure.http_client import JsonValue


class RecordingQueryController:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def execute(self, funcao: str, **parameters: Any) -> JsonValue:
        self.requests.append((funcao, dict(parameters)))
        if funcao == "setores":
            return [{"sigla": "DIR", "descricao": "Diretoria"}]

        return [
            {
                "data": [{"funcao": funcao, **parameters}],
                "encontrado": "1",
                "msg": "ok",
                "erro": "",
                "qtd": "1",
            }
        ]


class RecordingHttpClient:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def post(
        self,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> JsonValue:
        self.requests.append((endpoint, json or {}))
        return [
            {
                "data": [],
                "encontrado": 0,
                "msg": "",
                "erro": "",
                "qtd": 0,
            }
        ]


def test_api_client_exposes_all_direct_queries_with_common_controller() -> None:
    from fapes_lib.controllers.api_client import FapesApiClient

    query_controller = RecordingQueryController()
    client = FapesApiClient(query_controller=query_controller)

    responses = [
        client.listar_setores(),
        client.listar_editais(),
        client.listar_edital_chamadas(codedt=756),
        client.listar_edital_objetos_filhos(codedt=756),
        client.listar_projetos(codedt=756),
        client.listar_projeto_bolsas(codprj=48409),
        client.listar_bolsistas(codprj=48409),
        client.obter_pesquisador(codpes=123),
        client.listar_modalidade_bolsas(),
        client.listar_situacao_projeto(),
    ]

    assert query_controller.requests == [
        ("setores", {}),
        ("editais", {}),
        ("edital_chamadas", {"codedt": 756}),
        ("edital_objetos_filhos", {"codedt": 756}),
        ("projetos", {"codedt": 756}),
        ("projeto_bolsas", {"codprj": 48409}),
        ("bolsistas", {"codprj": 48409}),
        ("pesquisador", {"codpes": 123}),
        ("modalidade_bolsas", {}),
        ("situacao_projeto", {}),
    ]
    assert responses[0].data == [{"sigla": "DIR", "descricao": "Diretoria"}]
    assert responses[0].qtd == 1
    assert all(response.msg == "ok" for response in responses[1:])
    assert all(response.qtd == 1 for response in responses[1:])


def test_api_client_fails_before_http_when_required_parameter_is_empty() -> None:
    from fapes_lib.controllers.api_client import FapesApiClient
    from fapes_lib.controllers.query_controller import FapesQueryController

    http_client = RecordingHttpClient()
    query_controller = FapesQueryController(
        http_client=http_client,
        token="jwt-secret",
    )
    client = FapesApiClient(query_controller=query_controller)

    with pytest.raises(FapesRequestError) as exc_info:
        client.listar_projetos(codedt="")

    assert http_client.requests == []
    assert "codedt" in str(exc_info.value)
    assert "jwt-secret" not in str(exc_info.value)


def test_api_client_reexports_public_type_from_controller_package() -> None:
    from fapes_lib.controllers import FapesApiClient

    assert FapesApiClient.__name__ == "FapesApiClient"
