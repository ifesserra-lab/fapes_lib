from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from fapes_lib.exceptions import FapesRequestError
from fapes_lib.models import FapesResponseEnvelope, JsonObject


def envelope(*records: JsonObject) -> FapesResponseEnvelope:
    data = list(records)
    return FapesResponseEnvelope(
        data=data,
        encontrado=1 if data else 0,
        msg="ok" if data else "",
        erro="",
        qtd=len(data),
    )


class FakeExtractionApiClient:
    def __init__(
        self, *, empty: bool = False, fail_project_query: bool = False
    ) -> None:
        self.empty = empty
        self.fail_project_query = fail_project_query
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def listar_setores(self) -> FapesResponseEnvelope:
        self.calls.append(("listar_setores", {}))
        if self.empty:
            return envelope()
        return envelope({"sigla": "DIR", "descricao": "Diretoria"})

    def listar_modalidade_bolsas(self) -> FapesResponseEnvelope:
        self.calls.append(("listar_modalidade_bolsas", {}))
        if self.empty:
            return envelope()
        return envelope({"modalidade_id": 1, "descricao": "Bolsa"})

    def listar_situacao_projeto(self) -> FapesResponseEnvelope:
        self.calls.append(("listar_situacao_projeto", {}))
        if self.empty:
            return envelope()
        return envelope({"situacao_id": 2, "descricao": "Em andamento"})

    def listar_editais(self) -> FapesResponseEnvelope:
        self.calls.append(("listar_editais", {}))
        if self.empty:
            return envelope()
        return envelope(
            {"edital_id": 756, "edital_nome": "Edital com codigo"},
            {"edital_nome": "Edital sem codigo"},
        )

    def listar_edital_chamadas(self, codedt: int | str) -> FapesResponseEnvelope:
        self.calls.append(("listar_edital_chamadas", {"codedt": codedt}))
        if self.empty:
            return envelope()
        return envelope({"edital_id": codedt, "chamada_id": 10})

    def listar_projetos(self, codedt: int | str) -> FapesResponseEnvelope:
        self.calls.append(("listar_projetos", {"codedt": codedt}))
        if self.fail_project_query:
            raise FapesRequestError(
                "FAPES request failed",
                context={
                    "step": "listar_projetos",
                    "token": "jwt-secret",
                    "senha": "secret-password",
                },
            )
        if self.empty:
            return envelope()
        return envelope({"projeto_id": 48409, "edital_id": codedt})

    def listar_projeto_bolsas(self, codprj: int | str) -> FapesResponseEnvelope:
        self.calls.append(("listar_projeto_bolsas", {"codprj": codprj}))
        if self.empty:
            return envelope()
        return envelope({"projeto_id": codprj, "bolsa_id": 1})

    def listar_bolsistas(self, codprj: int | str) -> FapesResponseEnvelope:
        self.calls.append(("listar_bolsistas", {"codprj": codprj}))
        if self.empty:
            return envelope()
        return envelope({"projeto_id": codprj, "bolsista_id": 99})


@pytest.fixture
def context() -> dict[str, Any]:
    return {}


scenarios("../../docs/features/extracao_dados.feature")


@given("que a biblioteca esta autenticada")
def biblioteca_autenticada(context: dict[str, Any]) -> None:
    context["authenticated"] = True


@given("que as consultas diretas da API estao disponiveis")
def consultas_diretas_disponiveis(context: dict[str, Any]) -> None:
    from fapes_lib.controllers.extractor import FapesExtractor

    api_client = FakeExtractionApiClient()
    context["api_client"] = api_client
    context["extractor"] = FapesExtractor(api_client=api_client)


@given("que a API possui editais retornados")
def api_possui_editais_retornados(context: dict[str, Any]) -> None:
    assert context["api_client"].empty is False


@given("que a API possui projetos retornados")
def api_possui_projetos_retornados(context: dict[str, Any]) -> None:
    context["projetos"] = [{"projeto_id": 48409, "projeto_nome": "Projeto A"}]


@given("que uma consulta encadeada retorna erro")
def consulta_encadeada_retorna_erro(context: dict[str, Any]) -> None:
    from fapes_lib.controllers.extractor import FapesExtractor

    api_client = FakeExtractionApiClient(fail_project_query=True)
    context["api_client"] = api_client
    context["extractor"] = FapesExtractor(api_client=api_client)


@given("que a API responde sem registros encontrados")
def api_responde_sem_registros(context: dict[str, Any]) -> None:
    from fapes_lib.controllers.extractor import FapesExtractor

    api_client = FakeExtractionApiClient(empty=True)
    context["api_client"] = api_client
    context["extractor"] = FapesExtractor(api_client=api_client)


@when("eu executar a extracao de cadastros auxiliares")
def executar_extracao_cadastros_auxiliares(context: dict[str, Any]) -> None:
    context["result"] = context["extractor"].extrair_cadastros_auxiliares()


@when("eu executar a extracao de editais com chamadas")
def executar_extracao_editais_com_chamadas(context: dict[str, Any]) -> None:
    context["result"] = context["extractor"].extrair_editais_com_chamadas()


@when("eu executar a extracao de editais com projetos")
def executar_extracao_editais_com_projetos(context: dict[str, Any]) -> None:
    context["result"] = context["extractor"].extrair_editais_com_projetos()


@when("eu executar a extracao de projetos com bolsas e bolsistas")
def executar_extracao_projetos_com_bolsas_bolsistas(
    context: dict[str, Any],
) -> None:
    context["result"] = context["extractor"].extrair_projetos_com_bolsas_bolsistas(
        context["projetos"]
    )


@when("eu executar a extracao completa")
def executar_extracao_completa(context: dict[str, Any]) -> None:
    from fapes_lib.exceptions import FapesExtractionError

    try:
        context["result"] = context["extractor"].extrair_completa()
    except FapesExtractionError as exc:
        context["exception"] = exc


@when("eu executar uma extracao")
def executar_uma_extracao(context: dict[str, Any]) -> None:
    context["result"] = context["extractor"].extrair_cadastros_auxiliares()


@then("a biblioteca deve consultar setores")
def deve_consultar_setores(context: dict[str, Any]) -> None:
    assert ("listar_setores", {}) in context["api_client"].calls


@then("deve consultar modalidades de bolsas")
def deve_consultar_modalidades_de_bolsas(context: dict[str, Any]) -> None:
    assert ("listar_modalidade_bolsas", {}) in context["api_client"].calls


@then("deve consultar situacoes de projeto")
def deve_consultar_situacoes_de_projeto(context: dict[str, Any]) -> None:
    assert ("listar_situacao_projeto", {}) in context["api_client"].calls


@then("o resultado deve identificar a origem de cada conjunto de dados")
def resultado_identifica_origem(context: dict[str, Any]) -> None:
    assert set(context["result"].data) == {
        "setores",
        "modalidade_bolsas",
        "situacao_projeto",
    }
    assert context["result"].metadata.counts == {
        "setores": 1,
        "modalidade_bolsas": 1,
        "situacao_projeto": 1,
    }


@then("a biblioteca deve consultar chamadas para cada edital com identificador")
def deve_consultar_chamadas_para_editais_com_id(context: dict[str, Any]) -> None:
    assert context["api_client"].calls == [
        ("listar_editais", {}),
        ("listar_edital_chamadas", {"codedt": 756}),
    ]


@then("cada edital deve preservar sua lista de chamadas")
def cada_edital_preserva_chamadas(context: dict[str, Any]) -> None:
    editais = context["result"].data["editais"]

    assert editais[0]["chamadas"] == [{"edital_id": 756, "chamada_id": 10}]
    assert editais[1]["chamadas"] == []


@then("a biblioteca deve consultar projetos para cada edital com identificador")
def deve_consultar_projetos_para_editais_com_id(context: dict[str, Any]) -> None:
    assert context["api_client"].calls == [
        ("listar_editais", {}),
        ("listar_projetos", {"codedt": 756}),
    ]


@then("cada edital deve preservar sua lista de projetos")
def cada_edital_preserva_projetos(context: dict[str, Any]) -> None:
    editais = context["result"].data["editais"]

    assert editais[0]["projetos"] == [{"projeto_id": 48409, "edital_id": 756}]
    assert editais[1]["projetos"] == []


@then("a biblioteca deve consultar bolsas para cada projeto")
def deve_consultar_bolsas_para_cada_projeto(context: dict[str, Any]) -> None:
    assert ("listar_projeto_bolsas", {"codprj": 48409}) in context["api_client"].calls


@then("deve consultar bolsistas para cada projeto")
def deve_consultar_bolsistas_para_cada_projeto(context: dict[str, Any]) -> None:
    assert ("listar_bolsistas", {"codprj": 48409}) in context["api_client"].calls


@then("cada projeto deve preservar suas bolsas e seus bolsistas")
def cada_projeto_preserva_bolsas_e_bolsistas(context: dict[str, Any]) -> None:
    projeto = context["result"].data["projetos"][0]

    assert projeto["bolsas"] == [{"projeto_id": 48409, "bolsa_id": 1}]
    assert projeto["bolsistas"] == [{"projeto_id": 48409, "bolsista_id": 99}]


@then("a biblioteca deve autenticar antes das consultas quando necessario")
def deve_autenticar_antes_das_consultas(context: dict[str, Any]) -> None:
    assert context["authenticated"] is True
    assert "result" in context


@then("deve extrair cadastros auxiliares")
def deve_extrair_cadastros_auxiliares(context: dict[str, Any]) -> None:
    assert set(context["result"].data["cadastros_auxiliares"]) == {
        "setores",
        "modalidade_bolsas",
        "situacao_projeto",
    }


@then("deve extrair editais")
def deve_extrair_editais(context: dict[str, Any]) -> None:
    assert context["result"].data["editais_com_chamadas"]["editais"]
    assert context["result"].data["editais_com_projetos"]["editais"]


@then("deve extrair dados relacionados aos editais")
def deve_extrair_dados_relacionados_aos_editais(context: dict[str, Any]) -> None:
    assert context["result"].data["editais_com_chamadas"]["editais"][0]["chamadas"]
    assert context["result"].data["editais_com_projetos"]["editais"][0]["projetos"]
    assert context["result"].data["projetos_com_bolsas_bolsistas"]["projetos"][0][
        "bolsas"
    ]


@then("deve retornar dados e metadados da execucao")
def deve_retornar_dados_e_metadados(context: dict[str, Any]) -> None:
    result = context["result"]

    assert result.metadata.success is True
    assert result.metadata.steps == (
        "listar_setores",
        "listar_modalidade_bolsas",
        "listar_situacao_projeto",
        "listar_editais",
        "listar_edital_chamadas:756",
        "listar_projetos:756",
        "listar_projeto_bolsas:48409",
        "listar_bolsistas:48409",
    )
    assert set(result.metadata.counts) == {
        "cadastros_auxiliares",
        "editais_com_chamadas",
        "editais_com_projetos",
        "projetos_com_bolsas_bolsistas",
    }


@then("a biblioteca deve informar qual etapa falhou")
def deve_informar_etapa_que_falhou(context: dict[str, Any]) -> None:
    message = str(context["exception"])

    assert "listar_projetos:756" in message


@then("nao deve retornar sucesso silencioso")
def nao_deve_retornar_sucesso_silencioso(context: dict[str, Any]) -> None:
    assert "exception" in context
    assert "result" not in context


@then("a mensagem nao deve expor senha ou token")
def mensagem_nao_expoe_segredos(context: dict[str, Any]) -> None:
    message = str(context["exception"])

    assert "jwt-secret" not in message
    assert "secret-password" not in message


@then("a biblioteca deve retornar resultado vazio de forma explicita")
def deve_retornar_resultado_vazio_explicito(context: dict[str, Any]) -> None:
    assert context["result"].data == {
        "setores": [],
        "modalidade_bolsas": [],
        "situacao_projeto": [],
    }


@then("deve preservar metadados da consulta")
def deve_preservar_metadados_da_consulta(context: dict[str, Any]) -> None:
    assert context["result"].metadata.success is True
    assert context["result"].metadata.steps == (
        "listar_setores",
        "listar_modalidade_bolsas",
        "listar_situacao_projeto",
    )
    assert context["result"].metadata.counts == {
        "setores": 0,
        "modalidade_bolsas": 0,
        "situacao_projeto": 0,
    }
