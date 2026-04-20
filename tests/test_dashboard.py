from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, cast

import pytest


def test_dashboard_loads_summary_from_project_json_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "2"}],
                orcamento=[{"valor_categoria": "150"}],
                valor_bolsa="1000",
            ),
            _project(
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                bolsas=[{"orcamento_quantidade": "3"}],
                orcamento=[{"valor_categoria": "80"}],
                valor_bolsa="500",
            ),
        ],
    )

    data = dashboard.load_dashboard_data(input_dir)

    assert data.file_count == 1
    assert data.total_institutions == 2
    assert data.total_projects == 2
    assert data.total_scholarships == 5
    assert data.total_scholarship_amount == "1.500,00"
    assert data.total_budget == "230,00"
    assert data.institution_rows[0]["instituicao_nome"] == (
        "Universidade Federal do Espirito Santo"
    )
    assert data.excluded_project_count == 0
    assert data.excluded_project_rows == []


def test_dashboard_loads_summary_with_all_projects_when_requested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "2"}],
                orcamento=[{"valor_categoria": "150"}],
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
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                bolsas=[{"orcamento_quantidade": "20"}],
                orcamento=[{"valor_categoria": "8888"}],
                valor_bolsa="888",
                situacao_descricao="Proposta não Contratada mas Aprovada no Mérito",
            ),
        ],
    )

    contracted_data = dashboard.load_dashboard_data(input_dir)
    all_projects_data = dashboard.load_dashboard_data(
        input_dir,
        include_excluded_projects=True,
    )

    assert contracted_data.total_projects == 1
    assert contracted_data.total_scholarships == 2
    assert contracted_data.excluded_project_count == 2
    assert all_projects_data.total_projects == 3
    assert all_projects_data.total_scholarships == 32
    assert all_projects_data.total_budget == "19.037,00"
    assert all_projects_data.excluded_project_count == 2
    assert len(all_projects_data.excluded_project_rows) == 2


def test_dashboard_loads_summary_filtered_by_global_project_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "2"}],
                orcamento=[{"valor_categoria": "150"}],
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

    data = dashboard.load_dashboard_data(
        input_dir,
        selected_statuses=["Projeto Em Andamento"],
    )

    assert data.total_projects == 1
    assert data.total_scholarships == 2
    assert data.total_scholarship_amount == "1.000,00"
    assert data.total_budget == "150,00"


def test_dashboard_loads_researcher_scholarship_exports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                projeto_id="101",
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
                orcamento=[{"valor_categoria": "150"}],
                valor_bolsa="1200",
                situacao_descricao="Projeto Em Andamento",
            ),
            _project(
                projeto_id="102",
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
                valor_bolsa="9999",
                situacao_descricao="Projeto Não Contratado",
            ),
        ],
    )

    data = dashboard.load_dashboard_data(input_dir)
    all_projects_data = dashboard.load_dashboard_data(
        input_dir,
        include_excluded_projects=True,
    )

    assert data.researcher_scholarship_rows == [
        {
            "arquivo_origem": "edital_1_projetos.json",
            "pesquisador_id": "99",
            "pesquisador_nome": "Maria Silva",
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "projeto_id": "101",
            "projeto_titulo": "",
            "situacao_descricao": "Projeto Em Andamento",
            "bolsa_sigla": "ICT",
            "bolsa_nome": "Iniciacao Cientifica",
            "quantidade": 2,
            "duracao": 2,
            "valor_unitario": "300,00",
            "valor_total": "1.200,00",
        }
    ]
    assert data.researcher_scholarship_summary_rows == [
        {
            "pesquisador_id": "99",
            "pesquisador_nome": "Maria Silva",
            "instituicoes": "Universidade Federal do Espirito Santo | UFES - VITÓRIA",
            "total_projetos": 1,
            "total_lancamentos_bolsa": 1,
            "quantidade_bolsas": 2,
            "valor_total_bolsas": "1.200,00",
        }
    ]
    assert len(all_projects_data.researcher_scholarship_rows) == 2
    assert len(all_projects_data.researcher_scholarship_summary_rows) == 2


def test_dashboard_loads_scholarship_allocation_json_exports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                projeto_id="101",
                coordenador_nome="Maria Silva",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[],
                orcamento=[{"valor_categoria": "150"}],
                situacao_descricao="Projeto Em Andamento",
            )
        ],
    )
    allocation_file = tmp_path / "relatorio_alocacao_bolsas.json"
    allocation_file.write_text(
        json.dumps(
            [
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
                    "bolsa_sigla": "ICT",
                    "bolsa_nome": "Iniciacao Cientifica",
                    "bolsa_nivel_nome": "ICT",
                    "qtd_bolsas_paga": 2,
                    "valor_alocado_total": "1.400,00",
                    "pagamentos": 2,
                    "valor_pago_total": "1.400,50",
                },
                {
                    "arquivo_origem": "edital_1_projetos.json",
                    "projeto_id": "102",
                    "projeto_titulo": "Projeto nao contratado",
                    "situacao_descricao": "Projeto Não Contratado",
                    "coordenador_nome": "Joao Souza",
                    "instituicao_nome": "Instituto Federal do Espirito Santo",
                    "instituicao_sigla": "IFES",
                    "bolsista_pesquisador_id": "502",
                    "bolsista_pesquisador_nome": "Outro Bolsista",
                    "bolsa_sigla": "MSC",
                    "bolsa_nome": "Mestrado",
                    "bolsa_nivel_nome": "MSC",
                    "qtd_bolsas_paga": 4,
                    "valor_alocado_total": "4.000,00",
                    "pagamentos": 4,
                    "valor_pago_total": "4.000,00",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    data = dashboard.load_dashboard_data(input_dir)
    all_projects_data = dashboard.load_dashboard_data(
        input_dir,
        include_excluded_projects=True,
    )
    filtered_data = dashboard.load_dashboard_data(
        input_dir,
        include_excluded_projects=True,
        selected_statuses=["Projeto Não Contratado"],
    )

    assert [row["projeto_id"] for row in data.scholarship_allocation_rows] == ["101"]
    assert [
        row["projeto_id"] for row in all_projects_data.scholarship_allocation_rows
    ] == [
        "101",
        "102",
    ]
    assert [row["projeto_id"] for row in filtered_data.scholarship_allocation_rows] == [
        "102"
    ]


def test_dashboard_filters_and_summarizes_scholarship_allocations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "projeto_id": "101",
            "projeto_titulo": "Projeto com bolsista",
            "situacao_descricao": "Projeto Em Andamento",
            "coordenador_nome": "Maria Silva",
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "bolsista_pesquisador_id": "501",
            "bolsista_pesquisador_nome": "Aluno Bolsista",
            "bolsa_sigla": "ICT",
            "bolsa_nome": "Iniciacao Cientifica",
            "bolsa_nivel_nome": "ICT",
            "formulario_bolsa_inicio": "01/02/2024",
            "formulario_bolsa_termino": "01/02/2025",
            "qtd_bolsas_paga": 2,
            "valor_alocado_total": "1.400,00",
            "pagamentos": 2,
            "valor_pago_total": "1.400,50",
        },
        {
            "projeto_id": "102",
            "projeto_titulo": "Outro projeto",
            "situacao_descricao": "Projeto Em Andamento",
            "coordenador_nome": "Joao Souza",
            "instituicao_nome": "Instituto Federal do Espirito Santo",
            "instituicao_sigla": "IFES",
            "bolsista_pesquisador_id": "502",
            "bolsista_pesquisador_nome": "Outro Bolsista",
            "bolsa_sigla": "MSC",
            "bolsa_nome": "Mestrado",
            "bolsa_nivel_nome": "MSC",
            "formulario_bolsa_inicio": "01/03/2024",
            "formulario_bolsa_termino": "01/03/2025",
            "qtd_bolsas_paga": 4,
            "valor_alocado_total": "4.000,00",
            "pagamentos": 4,
            "valor_pago_total": "4.000,00",
        },
    ]

    institution_options = dashboard._scholarship_allocation_institution_options(rows)
    scholarship_type_options = dashboard._scholarship_allocation_type_options(rows)
    filtered_rows = dashboard._filter_scholarship_allocation_rows(
        rows,
        selected_institutions=[
            "Universidade Federal do Espirito Santo | UFES - VITÓRIA"
        ],
        selected_scholarship_types=["ICT | Iniciacao Cientifica"],
        query="aluno",
    )
    filtered_by_institution_query = dashboard._filter_scholarship_allocation_rows(
        rows,
        institution_query="ufes vitoria",
    )
    totals = dashboard._scholarship_allocation_totals(filtered_rows)
    summary_rows = dashboard._scholarship_allocation_holder_summary_rows(filtered_rows)
    summary_table_rows = dashboard._scholarship_allocation_summary_table_rows(
        summary_rows
    )
    table_rows = dashboard._scholarship_allocation_table_rows(filtered_rows)

    assert institution_options == [
        "Instituto Federal do Espirito Santo | IFES",
        "Universidade Federal do Espirito Santo | UFES - VITÓRIA",
    ]
    assert scholarship_type_options == ["ICT | Iniciacao Cientifica", "MSC | Mestrado"]
    assert totals.total_holders == 1
    assert totals.total_projects == 1
    assert totals.total_paid_scholarships == 2
    assert totals.total_allocated_amount == "1.400,00"
    assert totals.total_paid_amount == "1.400,50"
    assert filtered_by_institution_query == [rows[0]]
    assert summary_table_rows == [
        {
            "Bolsista": "Aluno Bolsista",
            "Projetos": 1,
            "Nomes dos projetos": "Projeto com bolsista",
            "Instituicoes": 1,
            "Instituicoes vinculadas": (
                "Universidade Federal do Espirito Santo | UFES - VITÓRIA"
            ),
            "Bolsas pagas": 2,
            "Valor alocado": "R$ 1.400,00",
            "Valor pago": "R$ 1.400,50",
        }
    ]
    assert table_rows == [
        {
            "Bolsista": "Aluno Bolsista",
            "Projeto ID": "101",
            "Projeto": "Projeto com bolsista",
            "Responsavel": "Maria Silva",
            "Instituicao": "Universidade Federal do Espirito Santo",
            "Sigla": "UFES - VITÓRIA",
            "Tipo bolsa": "ICT | Iniciacao Cientifica",
            "Nivel": "ICT",
            "Inicio": "01/02/2024",
            "Termino": "01/02/2025",
            "Situacao": "Projeto Em Andamento",
            "Bolsas pagas": 2,
            "Valor alocado": "R$ 1.400,00",
            "Pagamentos": 2,
            "Valor pago": "R$ 1.400,50",
        }
    ]


def test_dashboard_ranks_scholarship_allocation_chart_by_allocated_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "bolsista": "Bolsista menor",
            "valor_alocado_total": "1.000,00",
            "valor_pago_total": "0,00",
        },
        {
            "bolsista": "Bolsista maior",
            "valor_alocado_total": "9.000,00",
            "valor_pago_total": "0,00",
        },
    ]

    ranked_rows = dashboard._top_scholarship_allocation_holder_rows(rows, 2)

    assert [row["bolsista"] for row in ranked_rows] == [
        "Bolsista maior",
        "Bolsista menor",
    ]


def test_dashboard_filters_researcher_scholarships_for_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "pesquisador_nome": "Maria Silva",
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "bolsa_sigla": "ICT",
            "bolsa_nome": "Iniciacao Cientifica",
            "valor_total": "1.200,00",
        },
        {
            "pesquisador_nome": "Joao Souza",
            "instituicao_nome": "Instituto Federal do Espirito Santo",
            "instituicao_sigla": "IFES",
            "bolsa_sigla": "MSC",
            "bolsa_nome": "Mestrado",
            "valor_total": "3.000,00",
        },
        {
            "pesquisador_nome": "Ana Costa",
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "bolsa_sigla": "ICT",
            "bolsa_nome": "Iniciacao Cientifica",
            "valor_total": "500,00",
        },
    ]

    institution_options = dashboard._researcher_scholarship_institution_options(rows)
    type_options = dashboard._researcher_scholarship_type_options(rows)
    filtered_rows = dashboard._filter_researcher_scholarship_rows(
        rows,
        selected_institutions=[
            "Universidade Federal do Espirito Santo | UFES - VITÓRIA"
        ],
        selected_scholarship_types=["ICT | Iniciacao Cientifica"],
        min_value=1000.0,
        max_value=2000.0,
    )

    assert institution_options == [
        "Instituto Federal do Espirito Santo | IFES",
        "Universidade Federal do Espirito Santo | UFES - VITÓRIA",
    ]
    assert type_options == ["ICT | Iniciacao Cientifica", "MSC | Mestrado"]
    assert filtered_rows == [rows[0]]


def test_dashboard_splits_unknown_researchers_and_sorts_top_scholarship_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "pesquisador_nome": "Ana Costa",
            "valor_total_bolsas": "5.000,00",
        },
        {
            "pesquisador_nome": "Sem informacao",
            "valor_total_bolsas": "50.000,00",
        },
        {
            "pesquisador_nome": "Joao Souza",
            "valor_total_bolsas": "7.500,00",
        },
    ]

    known_rows = dashboard._known_researcher_summary_rows(rows)
    unknown_rows = dashboard._unknown_researcher_summary_rows(rows)
    top_rows = dashboard._top_researcher_scholarship_summary_rows(known_rows, 1)

    assert known_rows == [rows[0], rows[2]]
    assert unknown_rows == [rows[1]]
    assert top_rows == [rows[2]]


def test_dashboard_filters_and_sorts_rows_by_metric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "quantidade_bolsas": 5,
            "valor_bolsas": "500,00",
            "orcamento_contratado": "999,99",
            "total_projetos": 3,
        },
        {
            "instituicao_nome": "Instituto Federal do Espirito Santo",
            "instituicao_sigla": "IFES",
            "quantidade_bolsas": 9,
            "valor_bolsas": "1.500,00",
            "orcamento_contratado": "1.234,56",
            "total_projetos": 2,
        },
    ]

    filtered = dashboard.filter_rows(rows, "ufes")
    sorted_rows = dashboard.top_rows(rows, "quantidade_bolsas", 1)
    sorted_budget_rows = dashboard.top_rows(rows, "orcamento_contratado", 1)
    sorted_scholarship_amount_rows = dashboard.top_rows(rows, "valor_bolsas", 1)

    assert filtered == [rows[0]]
    assert sorted_rows == [rows[1]]
    assert sorted_budget_rows == [rows[1]]
    assert sorted_scholarship_amount_rows == [rows[1]]


def test_dashboard_maps_financial_scholarship_label_to_scholarship_amount_metric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))

    metric = dashboard._metric_from_label("Bolsas concedidas financeiro")

    assert metric == "valor_bolsas"


def test_dashboard_detail_tabs_include_budget_and_scholarship_sections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))

    tabs = dashboard._institution_detail_tabs()

    assert tabs == [
        "Orcamentos",
        "Bolsas",
        "Detalhe de orcamentos",
        "Detalhe de bolsas",
        "Projetos",
    ]


def test_dashboard_builds_options_and_filters_selected_institutions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "quantidade_bolsas": 5,
            "valor_bolsas": "500,00",
            "orcamento_contratado": "100,00",
            "total_projetos": 3,
        },
        {
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - SÃO MATEUS",
            "quantidade_bolsas": 2,
            "valor_bolsas": "200,00",
            "orcamento_contratado": "80,00",
            "total_projetos": 1,
        },
        {
            "instituicao_nome": "Instituto Federal do Espirito Santo",
            "instituicao_sigla": "IFES",
            "quantidade_bolsas": 9,
            "valor_bolsas": "900,00",
            "orcamento_contratado": "50,00",
            "total_projetos": 2,
        },
    ]

    options = dashboard.institution_options(rows)
    filtered = dashboard.filter_selected_institutions(
        rows,
        ["Universidade Federal do Espirito Santo | UFES - SÃO MATEUS"],
    )

    assert options == [
        "Instituto Federal do Espirito Santo | IFES",
        "Universidade Federal do Espirito Santo | UFES - SÃO MATEUS",
        "Universidade Federal do Espirito Santo | UFES - VITÓRIA",
    ]
    assert filtered == [rows[1]]


def test_dashboard_summary_totals_follow_filtered_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "quantidade_bolsas": 5,
            "valor_bolsas": "500,00",
            "orcamento_contratado": "100,00",
            "total_projetos": 3,
        },
        {
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - SÃO MATEUS",
            "quantidade_bolsas": 2,
            "valor_bolsas": "200,00",
            "orcamento_contratado": "80,00",
            "total_projetos": 1,
        },
        {
            "instituicao_nome": "Instituto Federal do Espirito Santo",
            "instituicao_sigla": "IFES",
            "quantidade_bolsas": 9,
            "valor_bolsas": "900,00",
            "orcamento_contratado": "50,00",
            "total_projetos": 2,
        },
    ]
    filtered_rows = dashboard.filter_selected_institutions(
        rows,
        [
            "Universidade Federal do Espirito Santo | UFES - VITÓRIA",
            "Instituto Federal do Espirito Santo | IFES",
        ],
    )

    totals = dashboard._summary_totals(filtered_rows)

    assert totals.total_institutions == 2
    assert totals.total_projects == 5
    assert totals.total_scholarships == 14
    assert totals.total_scholarship_amount == "1.400,00"
    assert totals.total_budget == "150,00"


def test_dashboard_filters_unknown_institutions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "instituicao_nome": "Sem informacao",
            "instituicao_sigla": "Sem informacao",
        },
        {
            "instituicao_nome": "Instituto Federal do Espirito Santo",
            "instituicao_sigla": "IFES",
        },
    ]

    filtered_rows = dashboard._known_institution_rows(rows)

    assert filtered_rows == [rows[1]]


def test_dashboard_builds_detail_filter_labels_for_summary_budget_categories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "instituicao_nome": "Instituto Federal do Espirito Santo",
            "instituicao_sigla": "IFES",
        }
    ]

    selected_labels = dashboard._detail_filter_labels(
        rows,
        [],
        False,
        False,
    )
    no_match_labels = dashboard._detail_filter_labels([], [], False, True)

    assert selected_labels == ["Instituto Federal do Espirito Santo | IFES"]
    assert no_match_labels == ["__sem_instituicao__"]


def test_dashboard_formats_financial_values_for_display(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "quantidade_bolsas": 5,
            "valor_bolsas": "1234.56",
            "orcamento_contratado": "1234.56",
            "total_projetos": 3,
        }
    ]

    display_rows = dashboard._display_rows(rows)

    assert display_rows[0]["orcamento_contratado"] == "1.234,56"
    assert display_rows[0]["valor_bolsas"] == "1.234,56"


def test_dashboard_converts_financial_table_columns_to_numeric_for_sorting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    pd = importlib.import_module("pandas")
    frame = pd.DataFrame(
        [
            {
                "Bolsista": "Valor menor",
                "Valor alocado": "R$ 900,00",
                "Valor pago": "0,00",
            },
            {
                "Bolsista": "Valor maior",
                "Valor alocado": "R$ 10.000,00",
                "Valor pago": "R$ 1.500,50",
            },
        ]
    )

    sortable_frame = dashboard._sortable_table_dataframe(frame)

    assert list(sortable_frame["Valor alocado"]) == [900.0, 10000.0]
    assert list(sortable_frame["Valor pago"]) == [0.0, 1500.5]
    assert list(sortable_frame.sort_values("Valor alocado")["Bolsista"]) == [
        "Valor menor",
        "Valor maior",
    ]


def test_dashboard_builds_chart_rows_with_total_value_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "instituicao_sigla": "UFES - VITÓRIA",
            "quantidade_bolsas": "12345",
            "valor_bolsas": "1.125.781.121,20",
            "valor_bolsas_valor": 1125781121.2,
            "orcamento_contratado": "782.561.708,70",
            "orcamento_contratado_valor": 782561708.7,
            "total_projetos": "99",
        }
    ]

    budget_rows = dashboard._chart_rows_with_labels(rows, "orcamento_contratado")
    scholarship_rows = dashboard._chart_rows_with_labels(rows, "quantidade_bolsas")
    scholarship_amount_rows = dashboard._chart_rows_with_labels(rows, "valor_bolsas")
    timeline_scholarship_amount_rows = dashboard._chart_rows_with_labels(
        rows,
        "valor_bolsas_valor",
    )
    timeline_budget_rows = dashboard._chart_rows_with_labels(
        rows,
        "orcamento_contratado_valor",
    )
    researcher_scholarship_rows = dashboard._chart_rows_with_labels(
        [{"pesquisador_nome": "Maria Silva", "valor_total_bolsas": "1.200,00"}],
        "valor_total_bolsas",
    )

    assert budget_rows[0]["valor_total"] == "R$ 782,6 mi"
    assert budget_rows[0]["orcamento_contratado"] == 782561708.7
    assert budget_rows[0]["orcamento_contratado_tooltip"] == "R$ 782.561.708,70"
    assert scholarship_rows[0]["valor_total"] == "12.345"
    assert scholarship_rows[0]["quantidade_bolsas"] == 12345
    assert scholarship_amount_rows[0]["valor_total"] == "R$ 1,1 bi"
    assert scholarship_amount_rows[0]["valor_bolsas"] == 1125781121.2
    assert scholarship_amount_rows[0]["valor_bolsas_tooltip"] == ("R$ 1.125.781.121,20")
    assert timeline_scholarship_amount_rows[0]["valor_total"] == "R$ 1,1 bi"
    assert timeline_budget_rows[0]["valor_total"] == "R$ 782,6 mi"
    assert researcher_scholarship_rows[0]["valor_total"] == "R$ 1,2 mil"
    assert researcher_scholarship_rows[0]["valor_total_bolsas"] == 1200.0


def test_dashboard_builds_researcher_financial_timeline_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    timeline_rows = [
        {
            "ano": 2024,
            "total_projetos": 2,
            "quantidade_bolsas": 3,
            "orcamento_contratado": "1.234,50",
            "orcamento_contratado_valor": 1234.5,
            "valor_bolsas": "500,00",
            "valor_bolsas_valor": 500.0,
        },
        {
            "ano": 2025,
            "total_projetos": 1,
            "quantidade_bolsas": 4,
            "orcamento_contratado": "2.000.000,00",
            "orcamento_contratado_valor": 2000000.0,
            "valor_bolsas": "750.000,00",
            "valor_bolsas_valor": 750000.0,
        },
    ]

    financial_rows = dashboard._researcher_financial_timeline_rows(timeline_rows)

    assert financial_rows == [
        {
            "ano": 2024,
            "tipo_volume_financeiro": "Orcamento contratado",
            "valor_financeiro": 1234.5,
            "valor_total": "R$ 1,2 mil",
            "total_projetos": 2,
            "quantidade_bolsas": 3,
        },
        {
            "ano": 2024,
            "tipo_volume_financeiro": "Valor bolsas",
            "valor_financeiro": 500.0,
            "valor_total": "R$ 500,00",
            "total_projetos": 2,
            "quantidade_bolsas": 3,
        },
        {
            "ano": 2025,
            "tipo_volume_financeiro": "Orcamento contratado",
            "valor_financeiro": 2000000.0,
            "valor_total": "R$ 2 mi",
            "total_projetos": 1,
            "quantidade_bolsas": 4,
        },
        {
            "ano": 2025,
            "tipo_volume_financeiro": "Valor bolsas",
            "valor_financeiro": 750000.0,
            "valor_total": "R$ 750 mil",
            "total_projetos": 1,
            "quantidade_bolsas": 4,
        },
    ]


def test_dashboard_builds_researcher_financial_timeline_table_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    timeline_rows = [
        {
            "ano": 2024,
            "total_projetos": 2,
            "quantidade_bolsas": 3,
            "orcamento_contratado": "1.234,50",
            "orcamento_contratado_valor": 1234.5,
            "valor_bolsas": "500,00",
            "valor_bolsas_valor": 500.0,
        },
        {
            "ano": 2025,
            "total_projetos": 1,
            "quantidade_bolsas": 4,
            "orcamento_contratado": "2.000.000,00",
            "orcamento_contratado_valor": 2000000.0,
            "valor_bolsas": "750.000,00",
            "valor_bolsas_valor": 750000.0,
        },
    ]

    table_rows = dashboard._researcher_financial_timeline_table_rows(timeline_rows)

    assert table_rows == [
        {
            "Ano": 2024,
            "Projetos": 2,
            "Bolsas": 3,
            "Orcamento contratado": "R$ 1.234,50",
            "Valor bolsas": "R$ 500,00",
            "Total financeiro": "R$ 1.734,50",
        },
        {
            "Ano": 2025,
            "Projetos": 1,
            "Bolsas": 4,
            "Orcamento contratado": "R$ 2.000.000,00",
            "Valor bolsas": "R$ 750.000,00",
            "Total financeiro": "R$ 2.750.000,00",
        },
    ]


def test_dashboard_builds_financial_chart_tooltip_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))

    tooltip_fields = dashboard._financial_chart_tooltip_fields(
        [
            "ano",
            "tipo_volume_financeiro",
            "valor_total",
            "total_projetos",
            "quantidade_bolsas",
        ],
        "ano",
        "tipo_volume_financeiro",
    )

    assert tooltip_fields == [
        ("ano", "ano"),
        ("tipo_volume_financeiro", "Tipo"),
        ("valor_total", "Total"),
        ("total_projetos", "Projetos"),
        ("quantidade_bolsas", "Bolsas"),
    ]


def test_dashboard_maps_financial_chart_mode_to_stack_option(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))

    assert dashboard._financial_chart_stack_from_mode("Barras agrupadas") is None
    assert dashboard._financial_chart_stack_from_mode("Barras empilhadas") == "zero"


def test_dashboard_builds_rich_chart_tooltip_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))

    tooltip_fields = dashboard._chart_tooltip_fields(
        [
            "instituicao_sigla",
            "valor_total",
            "total_projetos",
            "quantidade_bolsas",
            "valor_bolsas_tooltip",
            "valor_bolsas",
            "orcamento_contratado_tooltip",
            "orcamento_contratado",
        ],
        "instituicao_sigla",
    )

    assert tooltip_fields == [
        ("instituicao_sigla", "instituicao_sigla"),
        ("valor_total", "Total"),
        ("total_projetos", "Projetos"),
        ("quantidade_bolsas", "Bolsas"),
        ("valor_bolsas_tooltip", "Valor bolsas"),
        ("orcamento_contratado_tooltip", "Orcamento"),
    ]


def test_dashboard_builds_project_detail_table_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "projeto_id": "123",
            "projeto_titulo": "Pesquisa aplicada",
            "coordenador_nome": "Maria Silva",
            "projeto_data_inicio_previsto": "01/02/2024",
            "projeto_data_fim_previsto": "01/02/2026",
            "situacao_descricao": "Projeto Em Andamento",
            "quantidade_bolsas": 4,
            "valor_bolsas": "12.345,67",
            "orcamento_contratado": "98.765,43",
        }
    ]

    table_rows = dashboard._project_detail_table_rows(rows)

    assert table_rows == [
        {
            "Projeto ID": "123",
            "Projeto": "Pesquisa aplicada",
            "Responsavel": "Maria Silva",
            "Inicio previsto": "01/02/2024",
            "Conclusao prevista": "01/02/2026",
            "Situacao": "Projeto Em Andamento",
            "Bolsas": 4,
            "Valor bolsas": "R$ 12.345,67",
            "Orcamento contratado": "R$ 98.765,43",
        }
    ]


def test_dashboard_builds_researcher_project_table_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "projeto_id": "123",
            "projeto_titulo": "ConectaFapes",
            "coordenador_nome": "Paulo Santos",
            "instituicao_nome": "Instituto Federal do Espirito Santo",
            "instituicao_sigla": "IFES - SERRA",
            "projeto_data_inicio_previsto": "07/11/2023",
            "projeto_data_fim_previsto": "07/11/2026",
            "situacao_descricao": "Projeto Em Andamento",
            "quantidade_bolsas": 67,
            "valor_bolsas": "7.095.600,00",
            "orcamento_contratado": "11.645.680,00",
        }
    ]

    table_rows = dashboard._researcher_project_table_rows(rows)

    assert table_rows == [
        {
            "Projeto ID": "123",
            "Projeto": "ConectaFapes",
            "Responsavel": "Paulo Santos",
            "Instituicao": "Instituto Federal do Espirito Santo",
            "Sigla": "IFES - SERRA",
            "Inicio previsto": "07/11/2023",
            "Conclusao prevista": "07/11/2026",
            "Situacao": "Projeto Em Andamento",
            "Bolsas": 67,
            "Valor bolsas": "R$ 7.095.600,00",
            "Orcamento contratado": "R$ 11.645.680,00",
        }
    ]


def test_dashboard_builds_researcher_name_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "coordenador_nome": "Paulo Santos",
            "instituicao": "Instituto Federal do Espirito Santo | IFES - SERRA",
        },
        {
            "coordenador_nome": "Paulo Santos",
            "instituicao": "Universidade Federal do Espirito Santo | UFES - VITORIA",
        },
        {
            "coordenador_nome": "Paulo Sergio Santos",
            "instituicao": "Instituto Federal do Espirito Santo | IFES - SERRA",
        },
        {
            "coordenador_nome": "",
            "instituicao": "Sem informacao | Sem informacao",
        },
    ]

    name_rows = dashboard._researcher_name_rows(rows)

    assert name_rows == [
        {
            "Pesquisador": "Paulo Santos",
            "Projetos": 2,
            "Instituicoes": 2,
        },
        {
            "Pesquisador": "Paulo Sergio Santos",
            "Projetos": 1,
            "Instituicoes": 1,
        },
        {
            "Pesquisador": "Sem informacao",
            "Projetos": 1,
            "Instituicoes": 1,
        },
    ]


def test_dashboard_filters_researcher_projects_by_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "projeto_id": "1",
            "situacao_descricao": "Projeto Em Andamento",
        },
        {
            "projeto_id": "2",
            "situacao_descricao": "Projeto Concluído e homologado",
        },
        {
            "projeto_id": "3",
            "situacao_descricao": "Projeto Em Andamento",
        },
    ]

    filtered_rows = dashboard._filter_researcher_project_rows(
        rows,
        selected_statuses=["Projeto Em Andamento"],
    )
    unfiltered_rows = dashboard._filter_researcher_project_rows(
        rows,
        selected_statuses=[],
    )

    assert [row["projeto_id"] for row in filtered_rows] == ["1", "3"]
    assert unfiltered_rows == rows


def test_dashboard_builds_responsible_financial_volume_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "coordenador_nome": "Maria Silva",
            "quantidade_bolsas": 2,
            "valor_bolsas": "100,00",
            "orcamento_contratado": "1.000,00",
            "situacao_descricao": "Projeto Em Andamento",
        },
        {
            "coordenador_nome": "Joao Souza",
            "quantidade_bolsas": 1,
            "valor_bolsas": "25,00",
            "orcamento_contratado": "2.000,00",
            "situacao_descricao": "Projeto Em Andamento",
        },
        {
            "coordenador_nome": "Maria Silva",
            "quantidade_bolsas": 3,
            "valor_bolsas": "50,00",
            "orcamento_contratado": "500,00",
            "situacao_descricao": "Projeto Em Andamento",
        },
        {
            "coordenador_nome": "Maria Silva",
            "quantidade_bolsas": 10,
            "valor_bolsas": "999,00",
            "orcamento_contratado": "9.999,00",
            "situacao_descricao": "Projeto Não Contratado",
        },
        {
            "coordenador_nome": "Maria Silva",
            "quantidade_bolsas": 20,
            "valor_bolsas": "888,00",
            "orcamento_contratado": "8.888,00",
            "situacao_descricao": "Proposta não Contratada mas Aprovada no Mérito",
        },
    ]

    table_rows = dashboard._responsible_financial_volume_rows(rows)

    assert table_rows == [
        {
            "Responsavel": "Joao Souza",
            "Projetos": 1,
            "Bolsas": 1,
            "Valor bolsas": "R$ 25,00",
            "Volume financeiro": "R$ 2.000,00",
        },
        {
            "Responsavel": "Maria Silva",
            "Projetos": 2,
            "Bolsas": 5,
            "Valor bolsas": "R$ 150,00",
            "Volume financeiro": "R$ 1.500,00",
        },
    ]


def test_dashboard_explains_excluded_project_statuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))

    note = dashboard._excluded_project_status_note()

    assert "Projeto Não Contratado" in note
    assert "Proposta não Contratada mas Aprovada no Mérito" in note
    assert "volume financeiro" in note


def test_dashboard_filters_active_project_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {"projeto_id": "1", "situacao_descricao": "Projeto Em Andamento"},
        {"projeto_id": "2", "situacao_descricao": "Projeto Concluído e homologado"},
        {"projeto_id": "3", "situacao_descricao": "Sob Avaliação Final"},
    ]

    active_rows = dashboard._active_project_rows(rows)

    assert active_rows == [rows[0]]


def test_dashboard_filters_project_rows_by_query_status_year_and_activity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "ano": 2023,
            "projeto_id": "1",
            "projeto_titulo": "ConectaFapes",
            "coordenador_nome": "Paulo Santos",
            "situacao_descricao": "Projeto Em Andamento",
        },
        {
            "ano": 2024,
            "projeto_id": "2",
            "projeto_titulo": "Projeto encerrado",
            "coordenador_nome": "Maria Silva",
            "situacao_descricao": "Projeto Concluído e homologado",
        },
        {
            "ano": 2023,
            "projeto_id": "3",
            "projeto_titulo": "Outro projeto",
            "coordenador_nome": "Ana Souza",
            "situacao_descricao": "Projeto Em Andamento",
        },
    ]

    filtered_rows = dashboard._filter_project_rows(
        rows,
        query="paulo",
        selected_statuses=["Projeto Em Andamento"],
        selected_years=[2023],
        only_active=True,
    )

    assert filtered_rows == [rows[0]]


def test_dashboard_builds_project_filter_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {"ano": 2024, "situacao_descricao": "Projeto Em Andamento"},
        {"ano": 2023, "situacao_descricao": "Sob Avaliação Final"},
        {"ano": "", "situacao_descricao": ""},
    ]

    assert dashboard._project_year_options(rows) == [2023, 2024]
    assert dashboard._project_status_options(rows) == [
        "Projeto Em Andamento",
        "Sob Avaliação Final",
    ]


def test_dashboard_builds_scholarship_detail_table_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    dashboard = cast(Any, importlib.import_module("scripts.dashboard"))
    rows = [
        {
            "tipo_bolsa": "BPIG-III",
            "nome_bolsa": "Bolsa em Projeto Institucional de Governo",
            "quantidade_bolsas": 7,
            "valor_bolsas": "363.000,00",
            "total_lancamentos": 3,
        }
    ]

    table_rows = dashboard._scholarship_detail_table_rows(rows)

    assert table_rows == [
        {
            "Tipo de bolsa": "BPIG-III",
            "Nome da bolsa": "Bolsa em Projeto Institucional de Governo",
            "Quantidade": 7,
            "Valor contratado": "R$ 363.000,00",
            "Lancamentos": 3,
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
