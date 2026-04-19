from __future__ import annotations

from typing import Any

import pytest

from fapes_lib.exceptions import FapesRequestError
from fapes_lib.models import FapesResponseEnvelope, JsonObject


def envelope(*records: JsonObject) -> FapesResponseEnvelope:
    data = list(records)
    return FapesResponseEnvelope(
        data=data,
        encontrado=1 if data else 0,
        msg="",
        erro="",
        qtd=len(data),
    )


class FakeApiClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def listar_setores(self) -> FapesResponseEnvelope:
        self.calls.append(("listar_setores", {}))
        return envelope({"sigla": "DIR"})

    def listar_modalidade_bolsas(self) -> FapesResponseEnvelope:
        self.calls.append(("listar_modalidade_bolsas", {}))
        return envelope({"bolsa_id": 1})

    def listar_situacao_projeto(self) -> FapesResponseEnvelope:
        self.calls.append(("listar_situacao_projeto", {}))
        return envelope({"situacao_id": 2})

    def listar_editais(self) -> FapesResponseEnvelope:
        self.calls.append(("listar_editais", {}))
        return envelope(
            {"edital_id": 756, "edital_nome": "Edital com id"},
            {"edital_nome": "Edital sem id"},
        )

    def listar_edital_chamadas(self, codedt: int | str) -> FapesResponseEnvelope:
        self.calls.append(("listar_edital_chamadas", {"codedt": codedt}))
        return envelope({"edital_id": codedt, "edital_chamada_id": 10})

    def listar_projetos(self, codedt: int | str) -> FapesResponseEnvelope:
        self.calls.append(("listar_projetos", {"codedt": codedt}))
        return envelope({"projeto_id": 48409, "edital_id": codedt})

    def listar_projeto_bolsas(self, codprj: int | str) -> FapesResponseEnvelope:
        self.calls.append(("listar_projeto_bolsas", {"codprj": codprj}))
        return envelope({"projeto_id": codprj, "bolsa_id": 1})

    def listar_bolsistas(self, codprj: int | str) -> FapesResponseEnvelope:
        self.calls.append(("listar_bolsistas", {"codprj": codprj}))
        return envelope({"projeto_id": codprj, "bolsista_id": 99})


class FailingProjetosApiClient(FakeApiClient):
    def listar_projetos(self, codedt: int | str) -> FapesResponseEnvelope:
        self.calls.append(("listar_projetos", {"codedt": codedt}))
        raise FapesRequestError(
            "FAPES request failed",
            context={
                "step": "listar_projetos",
                "token": "jwt-secret",
                "senha": "secret-password",
            },
        )


def test_extractor_extracts_auxiliary_catalogs_in_order() -> None:
    from fapes_lib.controllers.extractor import FapesExtractor

    api_client = FakeApiClient()
    extractor = FapesExtractor(api_client=api_client)

    result = extractor.extrair_cadastros_auxiliares()

    assert api_client.calls == [
        ("listar_setores", {}),
        ("listar_modalidade_bolsas", {}),
        ("listar_situacao_projeto", {}),
    ]
    assert result.data == {
        "setores": [{"sigla": "DIR"}],
        "modalidade_bolsas": [{"bolsa_id": 1}],
        "situacao_projeto": [{"situacao_id": 2}],
    }
    assert result.metadata.success is True
    assert result.metadata.counts == {
        "setores": 1,
        "modalidade_bolsas": 1,
        "situacao_projeto": 1,
    }


def test_extractor_extracts_editais_with_chamadas_and_preserves_missing_ids() -> None:
    from fapes_lib.controllers.extractor import FapesExtractor

    api_client = FakeApiClient()
    extractor = FapesExtractor(api_client=api_client)

    result = extractor.extrair_editais_com_chamadas()

    assert api_client.calls == [
        ("listar_editais", {}),
        ("listar_edital_chamadas", {"codedt": 756}),
    ]
    assert result.data["editais"] == [
        {
            "edital_id": 756,
            "edital_nome": "Edital com id",
            "chamadas": [{"edital_id": 756, "edital_chamada_id": 10}],
        },
        {"edital_nome": "Edital sem id", "chamadas": []},
    ]
    assert result.metadata.counts == {"editais": 2, "chamadas": 1}


def test_extractor_extracts_editais_with_projects() -> None:
    from fapes_lib.controllers.extractor import FapesExtractor

    api_client = FakeApiClient()
    extractor = FapesExtractor(api_client=api_client)

    result = extractor.extrair_editais_com_projetos()

    assert api_client.calls == [
        ("listar_editais", {}),
        ("listar_projetos", {"codedt": 756}),
    ]
    assert result.data["editais"][0]["projetos"] == [
        {"projeto_id": 48409, "edital_id": 756}
    ]
    assert result.data["editais"][1]["projetos"] == []
    assert result.metadata.counts == {"editais": 2, "projetos": 1}


def test_extractor_extracts_projects_with_grants_and_holders() -> None:
    from fapes_lib.controllers.extractor import FapesExtractor

    api_client = FakeApiClient()
    extractor = FapesExtractor(api_client=api_client)

    result = extractor.extrair_projetos_com_bolsas_bolsistas(
        [{"projeto_id": 48409}, {"projeto_titulo": "Sem codigo"}]
    )

    assert api_client.calls == [
        ("listar_projeto_bolsas", {"codprj": 48409}),
        ("listar_bolsistas", {"codprj": 48409}),
    ]
    assert result.data["projetos"][0]["bolsas"] == [
        {"projeto_id": 48409, "bolsa_id": 1}
    ]
    assert result.data["projetos"][0]["bolsistas"] == [
        {"projeto_id": 48409, "bolsista_id": 99}
    ]
    assert result.data["projetos"][1]["bolsas"] == []
    assert result.data["projetos"][1]["bolsistas"] == []
    assert result.metadata.counts == {
        "projetos": 2,
        "bolsas": 1,
        "bolsistas": 1,
    }


def test_extractor_wraps_step_failures_without_leaking_secrets() -> None:
    from fapes_lib.controllers.extractor import FapesExtractor
    from fapes_lib.exceptions import FapesExtractionError

    api_client = FailingProjetosApiClient()
    extractor = FapesExtractor(api_client=api_client)

    with pytest.raises(FapesExtractionError) as exc_info:
        extractor.extrair_editais_com_projetos()

    message = str(exc_info.value)

    assert "listar_projetos:756" in message
    assert "jwt-secret" not in message
    assert "secret-password" not in message


def test_extractor_runs_complete_extraction_in_predictable_order() -> None:
    from fapes_lib.controllers.extractor import FapesExtractor

    api_client = FakeApiClient()
    extractor = FapesExtractor(api_client=api_client)

    result = extractor.extrair_completa()

    assert [name for name, _ in api_client.calls] == [
        "listar_setores",
        "listar_modalidade_bolsas",
        "listar_situacao_projeto",
        "listar_editais",
        "listar_edital_chamadas",
        "listar_editais",
        "listar_projetos",
        "listar_projeto_bolsas",
        "listar_bolsistas",
    ]
    assert set(result.data) == {
        "cadastros_auxiliares",
        "editais_com_chamadas",
        "editais_com_projetos",
        "projetos_com_bolsas_bolsistas",
    }
    assert result.metadata.success is True
