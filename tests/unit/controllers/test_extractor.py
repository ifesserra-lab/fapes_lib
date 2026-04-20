from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
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


class ConcurrentProjetosApiClient(FakeApiClient):
    def __init__(self) -> None:
        super().__init__()
        self._barrier = threading.Barrier(3)
        self.project_thread_names: list[str] = []

    def listar_editais(self) -> FapesResponseEnvelope:
        self.calls.append(("listar_editais", {}))
        return envelope(
            {"edital_id": 756, "edital_nome": "Edital 756"},
            {"edital_id": 757, "edital_nome": "Edital 757"},
            {"edital_id": 758, "edital_nome": "Edital 758"},
        )

    def listar_projetos(self, codedt: int | str) -> FapesResponseEnvelope:
        self.calls.append(("listar_projetos", {"codedt": codedt}))
        self.project_thread_names.append(threading.current_thread().name)
        self._barrier.wait(timeout=2)
        return envelope({"projeto_id": int(codedt) * 10, "edital_id": codedt})


class FlakyProjetosApiClient(FakeApiClient):
    def __init__(self) -> None:
        super().__init__()
        self.attempts: dict[int | str, int] = {}

    def listar_editais(self) -> FapesResponseEnvelope:
        self.calls.append(("listar_editais", {}))
        return envelope(
            {"edital_id": 756, "edital_nome": "Edital 756"},
            {"edital_id": 757, "edital_nome": "Edital 757"},
        )

    def listar_projetos(self, codedt: int | str) -> FapesResponseEnvelope:
        self.calls.append(("listar_projetos", {"codedt": codedt}))
        self.attempts[codedt] = self.attempts.get(codedt, 0) + 1

        if self.attempts[codedt] == 1:
            raise FapesRequestError("FAPES request failed")

        return envelope({"projeto_id": int(codedt) * 10, "edital_id": codedt})


class TwoEditaisApiClient(FakeApiClient):
    def listar_editais(self) -> FapesResponseEnvelope:
        self.calls.append(("listar_editais", {}))
        return envelope(
            {"edital_id": 756, "edital_nome": "Edital 756"},
            {"edital_id": 757, "edital_nome": "Edital 757"},
        )

    def listar_projetos(self, codedt: int | str) -> FapesResponseEnvelope:
        self.calls.append(("listar_projetos", {"codedt": codedt}))
        return envelope({"projeto_id": int(codedt) * 10, "edital_id": codedt})


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
    assert result.metadata.steps == ("listar_editais", "listar_edital_chamadas:756")


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
    assert result.metadata.steps == ("listar_editais", "listar_projetos:756")


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
    assert result.metadata.steps == (
        "listar_projeto_bolsas:48409",
        "listar_bolsistas:48409",
    )


def test_extractor_extracts_projects_by_edital_in_threads_and_saves_files(
    tmp_path: Path,
) -> None:
    from fapes_lib.controllers.extractor import FapesExtractor

    api_client = ConcurrentProjetosApiClient()
    extractor = FapesExtractor(api_client=api_client)

    result = extractor.extrair_projetos_dos_editais_em_threads(
        destination_dir=tmp_path,
        max_workers=3,
    )

    project_calls = [call for call in api_client.calls if call[0] == "listar_projetos"]

    assert sorted(project_calls, key=lambda call: call[1]["codedt"]) == [
        ("listar_projetos", {"codedt": 756}),
        ("listar_projetos", {"codedt": 757}),
        ("listar_projetos", {"codedt": 758}),
    ]
    assert len(set(api_client.project_thread_names)) == 3
    assert "MainThread" not in api_client.project_thread_names
    assert result.metadata.counts == {
        "editais": 3,
        "projetos": 3,
        "arquivos": 3,
    }
    assert result.metadata.steps == (
        "listar_editais",
        "listar_projetos:756",
        "listar_projetos:757",
        "listar_projetos:758",
    )

    for codedt in (756, 757, 758):
        destination = tmp_path / f"edital_{codedt}_projetos.json"
        payload = json.loads(destination.read_text(encoding="utf-8"))

        assert payload["data"]["edital"]["edital_id"] == codedt
        assert payload["data"]["projetos"] == [
            {"projeto_id": codedt * 10, "edital_id": codedt}
        ]

    assert [item["arquivo_projetos"] for item in result.data["editais"]] == [
        str(tmp_path / "edital_756_projetos.json"),
        str(tmp_path / "edital_757_projetos.json"),
        str(tmp_path / "edital_758_projetos.json"),
    ]


def test_extractor_retries_threaded_project_requests_before_saving_files(
    tmp_path: Path,
) -> None:
    from fapes_lib.controllers.extractor import FapesExtractor

    api_client = FlakyProjetosApiClient()
    extractor = FapesExtractor(api_client=api_client)

    result = extractor.extrair_projetos_dos_editais_em_threads(
        destination_dir=tmp_path,
        max_workers=2,
        retry_attempts=1,
    )

    assert api_client.attempts == {756: 2, 757: 2}
    assert result.metadata.counts == {
        "editais": 2,
        "projetos": 2,
        "arquivos": 2,
    }
    assert (tmp_path / "edital_756_projetos.json").exists()
    assert (tmp_path / "edital_757_projetos.json").exists()


def test_extractor_skips_existing_project_files_without_overwriting(
    tmp_path: Path,
) -> None:
    from fapes_lib.controllers.extractor import FapesExtractor

    existing_file = tmp_path / "edital_756_projetos.json"
    existing_file.write_text("existing-content\n", encoding="utf-8")
    api_client = TwoEditaisApiClient()
    extractor = FapesExtractor(api_client=api_client)

    result = extractor.extrair_projetos_dos_editais_em_threads(
        destination_dir=tmp_path,
        max_workers=2,
        skip_existing=True,
    )

    assert existing_file.read_text(encoding="utf-8") == "existing-content\n"
    assert [call for call in api_client.calls if call[0] == "listar_projetos"] == [
        ("listar_projetos", {"codedt": 757})
    ]
    assert result.metadata.counts == {
        "editais": 2,
        "projetos": 1,
        "arquivos": 1,
        "arquivos_existentes": 1,
    }
    assert result.data["editais"] == [
        {
            "edital_id": 756,
            "edital_nome": "Edital 756",
            "projetos": [],
            "arquivo_projetos": str(existing_file),
            "arquivo_projetos_existente": True,
        },
        {
            "edital_id": 757,
            "edital_nome": "Edital 757",
            "projetos": [{"projeto_id": 7570, "edital_id": 757}],
            "arquivo_projetos": str(tmp_path / "edital_757_projetos.json"),
        },
    ]


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


def test_extractor_logs_step_lifecycle_with_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from fapes_lib.controllers.extractor import FapesExtractor

    logger = logging.getLogger("fapes_lib.tests.extractor.lifecycle")
    api_client = FakeApiClient()
    extractor = FapesExtractor(api_client=api_client, logger=logger)

    with caplog.at_level(logging.INFO, logger=logger.name):
        extractor.extrair_editais_com_projetos()

    logged_steps = [
        getattr(record, "fapes_step", None)
        for record in caplog.records
        if getattr(record, "fapes_event", None) == "step_finished"
    ]

    assert logged_steps == ["listar_editais", "listar_projetos:756"]
    assert "FAPES extraction step finished" in caplog.text


def test_extractor_logs_step_failures_without_leaking_secrets(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from fapes_lib.controllers.extractor import FapesExtractor
    from fapes_lib.exceptions import FapesExtractionError

    logger = logging.getLogger("fapes_lib.tests.extractor.failure")
    api_client = FailingProjetosApiClient()
    extractor = FapesExtractor(api_client=api_client, logger=logger)

    with (
        caplog.at_level(logging.INFO, logger=logger.name),
        pytest.raises(FapesExtractionError),
    ):
        extractor.extrair_editais_com_projetos()

    failed_steps = [
        getattr(record, "fapes_step", None)
        for record in caplog.records
        if getattr(record, "fapes_event", None) == "step_failed"
    ]

    assert failed_steps == ["listar_projetos:756"]
    assert "FAPES extraction step failed" in caplog.text
    assert "jwt-secret" not in caplog.text
    assert "secret-password" not in caplog.text


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
