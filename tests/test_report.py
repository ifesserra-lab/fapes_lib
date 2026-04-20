from __future__ import annotations

import csv
import importlib
import json
from pathlib import Path
from typing import Any, cast

import pytest


def test_report_aggregates_scholarships_and_budget_by_institution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    report = cast(Any, importlib.import_module("scripts.report"))

    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "2"}, {"orcamento_quantidade": "3"}],
                orcamento=[{"valor_categoria": "1234.25"}, {"valor_categoria": "50"}],
                valor_bolsa="2500.75",
            ),
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "1"}],
                orcamento=[{"valor_categoria": "25.75"}],
                valor_bolsa="499.25",
            ),
        ],
    )
    _write_project_file(
        input_dir / "edital_2_projetos.json",
        [
            _project(
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                bolsas=[{"orcamento_quantidade": "4"}],
                orcamento=[{"valor_categoria": "80"}],
                valor_bolsa="1500",
            )
        ],
    )

    rows = report.generate_report(input_dir)

    assert rows == [
        {
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "quantidade_bolsas": 6,
            "valor_bolsas": "3.000,00",
            "orcamento_contratado": "1.310,00",
            "total_projetos": 2,
        },
        {
            "instituicao_nome": "Instituto Federal do Espirito Santo",
            "instituicao_sigla": "IFES",
            "quantidade_bolsas": 4,
            "valor_bolsas": "1.500,00",
            "orcamento_contratado": "80,00",
            "total_projetos": 1,
        },
    ]


def test_report_cli_writes_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    report = cast(Any, importlib.import_module("scripts.report"))
    input_dir = tmp_path / "projetos_por_edital"
    output_file = tmp_path / "relatorio.csv"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "2"}],
                orcamento=[{"valor_categoria": "100"}],
                valor_bolsa="1000",
            )
        ],
    )

    exit_code = report.run(
        ["--input-dir", str(input_dir), "--output", str(output_file)]
    )

    assert exit_code == 0
    with output_file.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows == [
        {
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "quantidade_bolsas": "2",
            "valor_bolsas": "1.000,00",
            "orcamento_contratado": "100,00",
            "total_projetos": "1",
        }
    ]


def test_report_keeps_same_institution_name_with_different_acronyms_separate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    report = cast(Any, importlib.import_module("scripts.report"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "2"}],
                orcamento=[{"valor_categoria": "100"}],
                valor_bolsa="150",
            ),
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - SÃO MATEUS",
                bolsas=[{"orcamento_quantidade": "5"}],
                orcamento=[{"valor_categoria": "200"}],
                valor_bolsa="250",
            ),
        ],
    )

    rows = report.generate_report(input_dir)

    assert rows == [
        {
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "quantidade_bolsas": 2,
            "valor_bolsas": "150,00",
            "orcamento_contratado": "100,00",
            "total_projetos": 1,
        },
        {
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - SÃO MATEUS",
            "quantidade_bolsas": 5,
            "valor_bolsas": "250,00",
            "orcamento_contratado": "200,00",
            "total_projetos": 1,
        },
    ]


def test_report_excludes_not_contracted_projects_from_totals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    report = cast(Any, importlib.import_module("scripts.report"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "2"}],
                orcamento=[{"valor_categoria": "100"}],
                valor_bolsa="1000",
                situacao_descricao="Projeto Em Andamento",
            ),
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "10"}],
                orcamento=[{"valor_categoria": "9999"}],
                valor_bolsa="999",
                situacao_descricao="Projeto Não Contratado",
            ),
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "20"}],
                orcamento=[{"valor_categoria": "8888"}],
                valor_bolsa="888",
                situacao_descricao="Proposta não Contratada mas Aprovada no Mérito",
            ),
        ],
    )

    rows = report.generate_report(input_dir)

    assert rows == [
        {
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "quantidade_bolsas": 2,
            "valor_bolsas": "1.000,00",
            "orcamento_contratado": "100,00",
            "total_projetos": 1,
        }
    ]


def test_report_can_include_excluded_projects_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    report = cast(Any, importlib.import_module("scripts.report"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "2"}],
                orcamento=[{"valor_categoria": "100"}],
                valor_bolsa="1000",
                situacao_descricao="Projeto Em Andamento",
            ),
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "10"}],
                orcamento=[{"valor_categoria": "9999"}],
                valor_bolsa="999",
                situacao_descricao="Projeto Não Contratado",
            ),
        ],
    )

    rows = report.generate_report(input_dir, include_excluded_projects=True)

    assert rows == [
        {
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "quantidade_bolsas": 12,
            "valor_bolsas": "1.999,00",
            "orcamento_contratado": "10.099,00",
            "total_projetos": 2,
        }
    ]


def test_report_generates_excluded_project_audit_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    report = cast(Any, importlib.import_module("scripts.report"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                projeto_id="101",
                projeto_titulo="Projeto em andamento",
                coordenador_nome="Maria Silva",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "2"}],
                orcamento=[{"valor_categoria": "100"}],
                valor_bolsa="1000",
                situacao_descricao="Projeto Em Andamento",
            ),
            _project(
                projeto_id="102",
                projeto_titulo="Projeto nao contratado",
                coordenador_nome="Joao Souza",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "10"}],
                orcamento=[{"valor_categoria": "9999"}],
                valor_bolsa="999",
                situacao_descricao="Projeto Não Contratado",
            ),
            _project(
                projeto_id="103",
                projeto_titulo="Proposta aprovada no merito",
                coordenador_nome="Ana Souza",
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                bolsas=[{"orcamento_quantidade": "20"}],
                orcamento=[{"valor_categoria": "8888"}],
                valor_bolsa="888",
                situacao_descricao="Proposta não Contratada mas Aprovada no Mérito",
            ),
        ],
    )

    rows = report.generate_excluded_projects_audit(input_dir)

    assert rows == [
        {
            "arquivo_origem": "edital_1_projetos.json",
            "projeto_id": "102",
            "projeto_titulo": "Projeto nao contratado",
            "coordenador_nome": "Joao Souza",
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "situacao_descricao": "Projeto Não Contratado",
            "quantidade_bolsas": 10,
            "valor_bolsas": "999,00",
            "orcamento_contratado": "9.999,00",
        },
        {
            "arquivo_origem": "edital_1_projetos.json",
            "projeto_id": "103",
            "projeto_titulo": "Proposta aprovada no merito",
            "coordenador_nome": "Ana Souza",
            "instituicao_nome": "Instituto Federal do Espirito Santo",
            "instituicao_sigla": "IFES",
            "situacao_descricao": "Proposta não Contratada mas Aprovada no Mérito",
            "quantidade_bolsas": 20,
            "valor_bolsas": "888,00",
            "orcamento_contratado": "8.888,00",
        },
    ]


def _write_project_file(path: Path, projetos: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps({"data": {"projetos": projetos}}, ensure_ascii=False),
        encoding="utf-8",
    )


def _project(
    *,
    projeto_id: str = "",
    projeto_titulo: str = "",
    coordenador_nome: str = "",
    instituicao_nome: str,
    instituicao_sigla: str,
    bolsas: list[dict[str, str]],
    orcamento: list[dict[str, str]],
    valor_bolsa: str = "0",
    situacao_descricao: str = "Projeto aprovado",
) -> dict[str, object]:
    return {
        "projeto_id": projeto_id,
        "projeto_titulo": projeto_titulo,
        "coordenador_nome": coordenador_nome,
        "valor_bolsa": valor_bolsa,
        "situacao_descricao": situacao_descricao,
        "dados_coordenador": {
            "data": [
                {
                    "instituicao_nome": instituicao_nome,
                    "instituicao_sigla": instituicao_sigla,
                }
            ],
        },
        "quadroBolsas": {"data": bolsas, "qtd": len(bolsas)},
        "orcamento_contratado": {"data": orcamento, "qtd": len(orcamento)},
    }
