from __future__ import annotations

import csv
import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pytest


@dataclass(frozen=True, slots=True)
class FakeAllocationEnvelope:
    data: list[dict[str, object]]


class FakeScholarshipAllocationApi:
    def __init__(self) -> None:
        self.calls: list[str | int] = []

    def listar_bolsistas(self, codprj: str | int) -> FakeAllocationEnvelope:
        self.calls.append(codprj)
        if str(codprj) != "101":
            return FakeAllocationEnvelope([])

        return FakeAllocationEnvelope(
            [
                {
                    "formulario_bolsa_id": "9001",
                    "formulario_bolsa_situacao": "1",
                    "bolsista_pesquisador_id": "501",
                    "bolsista_pesquisador_nome": "Aluno Bolsista",
                    "bolsista_pesquisador_cpf": "00000000000",
                    "formulario_bolsa_inicio": "01/02/2024",
                    "formulario_bolsa_termino": "01/02/2025",
                    "banco_id": "1",
                    "formulario_numero_agencia": "123",
                    "formulario_numero_conta": "456",
                    "bolsa_nivel_id": "51",
                    "bolsa_nivel_nome": "ICT",
                    "bolsa_nivel_valor": "700,00",
                    "bolsa_nome": "Iniciacao Cientifica",
                    "bolsa_sigla": "ICT",
                    "qtd_bolsas_paga": "2",
                    "folhas_pagamentos": [
                        {"folha_pagamento_pesquisador_valor": "700"},
                        {"folha_pagamento_pesquisador_valor": "700,50"},
                    ],
                }
            ]
        )


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


def test_report_cli_writes_researcher_scholarships_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    report = cast(Any, importlib.import_module("scripts.report"))
    input_dir = tmp_path / "projetos_por_edital"
    output_file = tmp_path / "relatorio.csv"
    researcher_scholarships_file = tmp_path / "pesquisadores_bolsas.csv"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                projeto_id="101",
                projeto_titulo="Projeto com bolsas",
                coordenador_nome="Maria Silva",
                pesquisador_id="99",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[
                    {
                        "sigla": "ICT",
                        "nome": "Iniciacao Cientifica",
                        "orcamento_quantidade": "2",
                        "orcamento_custo": "300",
                        "orcamento_duracao": "2",
                    }
                ],
                orcamento=[{"valor_categoria": "100"}],
            )
        ],
    )

    exit_code = report.run(
        [
            "--input-dir",
            str(input_dir),
            "--output",
            str(output_file),
            "--researcher-scholarships-output",
            str(researcher_scholarships_file),
        ]
    )

    assert exit_code == 0
    with researcher_scholarships_file.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows == [
        {
            "arquivo_origem": "edital_1_projetos.json",
            "pesquisador_id": "99",
            "pesquisador_nome": "Maria Silva",
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "projeto_id": "101",
            "projeto_titulo": "Projeto com bolsas",
            "situacao_descricao": "Projeto aprovado",
            "bolsa_sigla": "ICT",
            "bolsa_nome": "Iniciacao Cientifica",
            "quantidade": "2",
            "duracao": "2",
            "valor_unitario": "300,00",
            "valor_total": "1.200,00",
        }
    ]


def test_report_cli_writes_researcher_scholarships_summary_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    report = cast(Any, importlib.import_module("scripts.report"))
    input_dir = tmp_path / "projetos_por_edital"
    output_file = tmp_path / "relatorio.csv"
    summary_file = tmp_path / "pesquisadores_bolsas_resumo.csv"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                projeto_id="101",
                projeto_titulo="Projeto com bolsas",
                coordenador_nome="Maria Silva",
                pesquisador_id="99",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[
                    {
                        "sigla": "ICT",
                        "nome": "Iniciacao Cientifica",
                        "orcamento_quantidade": "2",
                        "orcamento_custo": "300",
                        "orcamento_duracao": "2",
                    }
                ],
                orcamento=[{"valor_categoria": "100"}],
            )
        ],
    )

    exit_code = report.run(
        [
            "--input-dir",
            str(input_dir),
            "--output",
            str(output_file),
            "--researcher-scholarships-summary-output",
            str(summary_file),
        ]
    )

    assert exit_code == 0
    with summary_file.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows == [
        {
            "pesquisador_id": "99",
            "pesquisador_nome": "Maria Silva",
            "instituicoes": "Universidade Federal do Espirito Santo | UFES - VITÓRIA",
            "total_projetos": "1",
            "total_lancamentos_bolsa": "1",
            "quantidade_bolsas": "2",
            "valor_total_bolsas": "1.200,00",
        }
    ]


def test_report_cli_writes_scholarship_allocations_from_fapes_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    report = cast(Any, importlib.import_module("scripts.report"))
    input_dir = tmp_path / "projetos_por_edital"
    output_file = tmp_path / "relatorio.csv"
    allocations_file = tmp_path / "alocacao_bolsas.csv"
    allocations_json_file = tmp_path / "alocacao_bolsas.json"
    api_client = FakeScholarshipAllocationApi()
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                projeto_id="101",
                projeto_titulo="Projeto com bolsista",
                coordenador_nome="Maria Silva",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[],
                orcamento=[],
                situacao_descricao="Projeto Em Andamento",
            )
        ],
    )

    exit_code = report.run(
        [
            "--input-dir",
            str(input_dir),
            "--output",
            str(output_file),
            "--scholarship-allocations-output",
            str(allocations_file),
            "--scholarship-allocations-json-output",
            str(allocations_json_file),
            "--scholarship-allocation-max-workers",
            "1",
        ],
        api_client_factory=lambda: api_client,
    )

    assert exit_code == 0
    assert api_client.calls == ["101"]
    with allocations_file.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows == [
        {
            "arquivo_origem": "edital_1_projetos.json",
            "projeto_id": "101",
            "projeto_titulo": "Projeto com bolsista",
            "situacao_descricao": "Projeto Em Andamento",
            "coordenador_nome": "Maria Silva",
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "bolsista_pesquisador_id": "501",
            "bolsista_pesquisador_nome": "Aluno Bolsista",
            "formulario_bolsa_id": "9001",
            "formulario_bolsa_situacao": "1",
            "formulario_bolsa_inicio": "01/02/2024",
            "formulario_bolsa_termino": "01/02/2025",
            "formulario_cancel_bolsa_data": "",
            "formulario_subst_bolsa_data": "",
            "bolsa_sigla": "ICT",
            "bolsa_nome": "Iniciacao Cientifica",
            "bolsa_nivel_id": "51",
            "bolsa_nivel_nome": "ICT",
            "bolsa_nivel_valor": "700,00",
            "qtd_bolsas_paga": "2",
            "valor_alocado_total": "1.400,00",
            "pagamentos": "2",
            "valor_pago_total": "1.400,50",
        }
    ]
    assert "bolsista_pesquisador_cpf" not in rows[0]
    assert "formulario_numero_conta" not in rows[0]

    json_rows = json.loads(allocations_json_file.read_text(encoding="utf-8"))
    assert json_rows == [
        {
            "arquivo_origem": "edital_1_projetos.json",
            "projeto_id": "101",
            "projeto_titulo": "Projeto com bolsista",
            "situacao_descricao": "Projeto Em Andamento",
            "coordenador_nome": "Maria Silva",
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "bolsista_pesquisador_id": "501",
            "bolsista_pesquisador_nome": "Aluno Bolsista",
            "formulario_bolsa_id": "9001",
            "formulario_bolsa_situacao": "1",
            "formulario_bolsa_inicio": "01/02/2024",
            "formulario_bolsa_termino": "01/02/2025",
            "formulario_cancel_bolsa_data": "",
            "formulario_subst_bolsa_data": "",
            "bolsa_sigla": "ICT",
            "bolsa_nome": "Iniciacao Cientifica",
            "bolsa_nivel_id": "51",
            "bolsa_nivel_nome": "ICT",
            "bolsa_nivel_valor": "700,00",
            "qtd_bolsas_paga": 2,
            "valor_alocado_total": "1.400,00",
            "pagamentos": 2,
            "valor_pago_total": "1.400,50",
        }
    ]
    assert "bolsista_pesquisador_cpf" not in json_rows[0]
    assert "formulario_numero_conta" not in json_rows[0]


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


def test_report_filters_totals_by_project_status(
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
                bolsas=[{"orcamento_quantidade": "5"}],
                orcamento=[{"valor_categoria": "500"}],
                valor_bolsa="250",
                situacao_descricao="Projeto Concluído e homologado",
            ),
        ],
    )

    rows = report.generate_report(
        input_dir,
        selected_statuses=["Projeto Em Andamento"],
    )

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


def test_report_loads_project_status_options(
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
                bolsas=[],
                orcamento=[],
                situacao_descricao="Projeto Em Andamento",
            ),
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[],
                orcamento=[],
                situacao_descricao="Projeto Não Contratado",
            ),
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[],
                orcamento=[],
                situacao_descricao="Projeto Concluído e homologado",
            ),
        ],
    )

    contracted_options = report.load_project_status_options(input_dir)
    all_options = report.load_project_status_options(
        input_dir,
        include_excluded_projects=True,
    )

    assert contracted_options == [
        "Projeto Concluído e homologado",
        "Projeto Em Andamento",
    ]
    assert all_options == [
        "Projeto Concluído e homologado",
        "Projeto Em Andamento",
        "Projeto Não Contratado",
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


def test_report_generates_researcher_scholarships_rows(
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
                projeto_titulo="Projeto com bolsas",
                coordenador_nome="Maria Silva",
                pesquisador_id="99",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[
                    {
                        "sigla": "ICT",
                        "nome": "Iniciacao Cientifica",
                        "orcamento_quantidade": "2",
                        "orcamento_custo": "300",
                        "orcamento_duracao": "2",
                    },
                    {
                        "sigla": "MSC",
                        "nome": "Mestrado",
                        "orcamento_quantidade": "1",
                        "vlrtot": "1200",
                    },
                ],
                orcamento=[{"valor_categoria": "100"}],
                situacao_descricao="Projeto Em Andamento",
            ),
            _project(
                projeto_id="102",
                projeto_titulo="Projeto sem contrato",
                coordenador_nome="Joao Souza",
                pesquisador_id="77",
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                bolsas=[
                    {
                        "sigla": "ICT",
                        "nome": "Iniciacao Cientifica",
                        "orcamento_quantidade": "10",
                        "vlrtot": "9999",
                    }
                ],
                orcamento=[{"valor_categoria": "9999"}],
                situacao_descricao="Projeto Não Contratado",
            ),
        ],
    )

    rows = report.generate_researcher_scholarships_report(input_dir)
    all_rows = report.generate_researcher_scholarships_report(
        input_dir,
        include_excluded_projects=True,
    )

    assert rows == [
        {
            "arquivo_origem": "edital_1_projetos.json",
            "pesquisador_id": "99",
            "pesquisador_nome": "Maria Silva",
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "projeto_id": "101",
            "projeto_titulo": "Projeto com bolsas",
            "situacao_descricao": "Projeto Em Andamento",
            "bolsa_sigla": "ICT",
            "bolsa_nome": "Iniciacao Cientifica",
            "quantidade": 2,
            "duracao": 2,
            "valor_unitario": "300,00",
            "valor_total": "1.200,00",
        },
        {
            "arquivo_origem": "edital_1_projetos.json",
            "pesquisador_id": "99",
            "pesquisador_nome": "Maria Silva",
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "projeto_id": "101",
            "projeto_titulo": "Projeto com bolsas",
            "situacao_descricao": "Projeto Em Andamento",
            "bolsa_sigla": "MSC",
            "bolsa_nome": "Mestrado",
            "quantidade": 1,
            "duracao": 1,
            "valor_unitario": "1.200,00",
            "valor_total": "1.200,00",
        },
    ]
    assert len(all_rows) == 3


def test_report_generates_researcher_scholarships_summary_rows(
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
                projeto_titulo="Projeto com bolsas",
                coordenador_nome="Maria Silva",
                pesquisador_id="99",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[
                    {
                        "sigla": "ICT",
                        "nome": "Iniciacao Cientifica",
                        "orcamento_quantidade": "2",
                        "orcamento_custo": "300",
                        "orcamento_duracao": "2",
                    },
                    {
                        "sigla": "MSC",
                        "nome": "Mestrado",
                        "orcamento_quantidade": "1",
                        "vlrtot": "1200",
                    },
                ],
                orcamento=[{"valor_categoria": "100"}],
                situacao_descricao="Projeto Em Andamento",
            ),
            _project(
                projeto_id="102",
                projeto_titulo="Outro projeto",
                coordenador_nome="Maria Silva",
                pesquisador_id="99",
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                bolsas=[
                    {
                        "sigla": "ICT",
                        "nome": "Iniciacao Cientifica",
                        "orcamento_quantidade": "3",
                        "vlrtot": "900",
                    }
                ],
                orcamento=[{"valor_categoria": "50"}],
                situacao_descricao="Projeto Em Andamento",
            ),
            _project(
                projeto_id="103",
                projeto_titulo="Projeto sem contrato",
                coordenador_nome="Joao Souza",
                pesquisador_id="77",
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                bolsas=[
                    {
                        "sigla": "ICT",
                        "nome": "Iniciacao Cientifica",
                        "orcamento_quantidade": "10",
                        "vlrtot": "9999",
                    }
                ],
                orcamento=[{"valor_categoria": "9999"}],
                situacao_descricao="Projeto Não Contratado",
            ),
        ],
    )

    rows = report.generate_researcher_scholarships_summary(input_dir)
    all_rows = report.generate_researcher_scholarships_summary(
        input_dir,
        include_excluded_projects=True,
    )

    assert rows == [
        {
            "pesquisador_id": "99",
            "pesquisador_nome": "Maria Silva",
            "instituicoes": (
                "Instituto Federal do Espirito Santo | IFES; "
                "Universidade Federal do Espirito Santo | UFES - VITÓRIA"
            ),
            "total_projetos": 2,
            "total_lancamentos_bolsa": 3,
            "quantidade_bolsas": 6,
            "valor_total_bolsas": "3.300,00",
        }
    ]
    assert len(all_rows) == 2
    assert all_rows[0]["pesquisador_nome"] == "Joao Souza"
    assert all_rows[1]["pesquisador_nome"] == "Maria Silva"


def test_report_fetches_scholarship_allocations_from_fapes_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    report = cast(Any, importlib.import_module("scripts.report"))
    api_client = FakeScholarshipAllocationApi()
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                projeto_id="101",
                projeto_titulo="Projeto com bolsista",
                coordenador_nome="Maria Silva",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[],
                orcamento=[],
                situacao_descricao="Projeto Em Andamento",
            ),
            _project(
                projeto_id="102",
                projeto_titulo="Projeto nao contratado",
                coordenador_nome="Joao Souza",
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                bolsas=[],
                orcamento=[],
                situacao_descricao="Projeto Não Contratado",
            ),
        ],
    )

    rows = report.generate_scholarship_allocations_report(
        input_dir,
        api_client=api_client,
        max_workers=1,
    )

    assert api_client.calls == ["101"]
    assert rows == [
        {
            "arquivo_origem": "edital_1_projetos.json",
            "projeto_id": "101",
            "projeto_titulo": "Projeto com bolsista",
            "situacao_descricao": "Projeto Em Andamento",
            "coordenador_nome": "Maria Silva",
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "bolsista_pesquisador_id": "501",
            "bolsista_pesquisador_nome": "Aluno Bolsista",
            "formulario_bolsa_id": "9001",
            "formulario_bolsa_situacao": "1",
            "formulario_bolsa_inicio": "01/02/2024",
            "formulario_bolsa_termino": "01/02/2025",
            "formulario_cancel_bolsa_data": "",
            "formulario_subst_bolsa_data": "",
            "bolsa_sigla": "ICT",
            "bolsa_nome": "Iniciacao Cientifica",
            "bolsa_nivel_id": "51",
            "bolsa_nivel_nome": "ICT",
            "bolsa_nivel_valor": "700,00",
            "qtd_bolsas_paga": 2,
            "valor_alocado_total": "1.400,00",
            "pagamentos": 2,
            "valor_pago_total": "1.400,50",
        }
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
    pesquisador_id: str = "",
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
                    "pesquisador_id": pesquisador_id,
                    "pesquisador_nome": coordenador_nome,
                    "instituicao_nome": instituicao_nome,
                    "instituicao_sigla": instituicao_sigla,
                }
            ],
        },
        "quadroBolsas": {"data": bolsas, "qtd": len(bolsas)},
        "orcamento_contratado": {"data": orcamento, "qtd": len(orcamento)},
    }
