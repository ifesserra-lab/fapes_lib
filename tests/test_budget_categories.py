from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, cast

import pytest


def test_budget_categories_group_budget_by_readable_category(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    budget_categories = cast(Any, importlib.import_module("scripts.budget_categories"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                orcamento=[
                    {
                        "descricao_categoria": "Material de Consumo",
                        "valor_categoria": "1000",
                    },
                    {
                        "descricao_categoria": "Equipamentos e Material Permanente",
                        "valor_categoria": "2000",
                    },
                    {"descricao_categoria": "Diárias", "valor_categoria": "300"},
                    {"descricao_categoria": "Passagens", "valor_categoria": "700"},
                    {
                        "descricao_categoria": "Outros Serviços de Terceiros",
                        "valor_categoria": "500",
                    },
                ],
            ),
            _project(
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                orcamento=[
                    {"descricao_categoria": "Bolsas", "valor_categoria": "9000"},
                ],
            ),
        ],
    )

    rows = budget_categories.load_budget_categories(
        input_dir,
        ["Universidade Federal do Espirito Santo | UFES - VITÓRIA"],
    )

    assert rows == [
        {
            "categoria_orcamento": "Equipamentos e material permanente",
            "orcamento_contratado": "2.000,00",
            "orcamento_contratado_valor": 2000.0,
            "total_lancamentos": 1,
        },
        {
            "categoria_orcamento": "Material de consumo",
            "orcamento_contratado": "1.000,00",
            "orcamento_contratado_valor": 1000.0,
            "total_lancamentos": 1,
        },
        {
            "categoria_orcamento": "Viagem",
            "orcamento_contratado": "1.000,00",
            "orcamento_contratado_valor": 1000.0,
            "total_lancamentos": 2,
        },
        {
            "categoria_orcamento": "Serviços de terceiros",
            "orcamento_contratado": "500,00",
            "orcamento_contratado_valor": 500.0,
            "total_lancamentos": 1,
        },
    ]


def test_budget_categories_load_all_institutions_when_no_filter_is_selected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    budget_categories = cast(Any, importlib.import_module("scripts.budget_categories"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                orcamento=[
                    {"descricao_categoria": "Bolsas", "valor_categoria": "1000"},
                ],
            ),
            _project(
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                orcamento=[
                    {"descricao_categoria": "Bolsas", "valor_categoria": "500"},
                ],
            ),
        ],
    )

    rows = budget_categories.load_budget_categories(input_dir, [])

    assert rows == [
        {
            "categoria_orcamento": "Bolsas",
            "orcamento_contratado": "1.500,00",
            "orcamento_contratado_valor": 1500.0,
            "total_lancamentos": 2,
        }
    ]


def test_budget_categories_group_budget_by_researcher_query(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    budget_categories = cast(Any, importlib.import_module("scripts.budget_categories"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                coordenador_nome="Maria Silva",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                orcamento=[
                    {
                        "descricao_categoria": "Material de Consumo",
                        "valor_categoria": "1000",
                    },
                    {
                        "descricao_categoria": "Equipamentos e Material Permanente",
                        "valor_categoria": "2000",
                    },
                ],
            ),
            _project(
                coordenador_nome="Joao Souza",
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                orcamento=[
                    {
                        "descricao_categoria": "Material de Consumo",
                        "valor_categoria": "9999",
                    },
                ],
            ),
        ],
    )

    rows = budget_categories.load_researcher_budget_categories(input_dir, "maria")

    assert rows == [
        {
            "categoria_orcamento": "Equipamentos e material permanente",
            "orcamento_contratado": "2.000,00",
            "orcamento_contratado_valor": 2000.0,
            "total_lancamentos": 1,
        },
        {
            "categoria_orcamento": "Material de consumo",
            "orcamento_contratado": "1.000,00",
            "orcamento_contratado_valor": 1000.0,
            "total_lancamentos": 1,
        },
    ]


def test_budget_categories_load_researcher_budget_items(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    budget_categories = cast(Any, importlib.import_module("scripts.budget_categories"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                projeto_id="101",
                projeto_titulo="Projeto da Maria",
                coordenador_nome="Maria Silva",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                orcamento=[
                    {
                        "descricao_categoria": "Material de Consumo",
                        "valor_categoria": "1000",
                    },
                    {
                        "descricao_categoria": "Equipamentos e Material Permanente",
                        "valor_categoria": "2000",
                    },
                ],
            ),
            _project(
                projeto_id="202",
                projeto_titulo="Projeto do Joao",
                coordenador_nome="Joao Souza",
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                orcamento=[
                    {
                        "descricao_categoria": "Material de Consumo",
                        "valor_categoria": "9999",
                    },
                ],
            ),
        ],
    )

    rows = budget_categories.load_researcher_budget_items(input_dir, "maria")

    assert rows == [
        {
            "projeto_id": "101",
            "projeto_titulo": "Projeto da Maria",
            "coordenador_nome": "Maria Silva",
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "categoria_orcamento": "Equipamentos e material permanente",
            "descricao_categoria": "Equipamentos e Material Permanente",
            "orcamento_contratado": "2.000,00",
            "orcamento_contratado_valor": 2000.0,
        },
        {
            "projeto_id": "101",
            "projeto_titulo": "Projeto da Maria",
            "coordenador_nome": "Maria Silva",
            "instituicao_nome": "Universidade Federal do Espirito Santo",
            "instituicao_sigla": "UFES - VITÓRIA",
            "categoria_orcamento": "Material de consumo",
            "descricao_categoria": "Material de Consumo",
            "orcamento_contratado": "1.000,00",
            "orcamento_contratado_valor": 1000.0,
        },
    ]


def test_budget_categories_exclude_not_contracted_projects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    budget_categories = cast(Any, importlib.import_module("scripts.budget_categories"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                orcamento=[
                    {"descricao_categoria": "Bolsas", "valor_categoria": "1000"},
                ],
                situacao_descricao="Projeto Em Andamento",
            ),
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                orcamento=[
                    {"descricao_categoria": "Bolsas", "valor_categoria": "9999"},
                ],
                situacao_descricao="Projeto Não Contratado",
            ),
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                orcamento=[
                    {"descricao_categoria": "Bolsas", "valor_categoria": "8888"},
                ],
                situacao_descricao="Proposta não Contratada mas Aprovada no Mérito",
            ),
        ],
    )

    rows = budget_categories.load_budget_categories(
        input_dir,
        ["Universidade Federal do Espirito Santo | UFES - VITÓRIA"],
    )
    all_rows = budget_categories.load_budget_categories(
        input_dir,
        ["Universidade Federal do Espirito Santo | UFES - VITÓRIA"],
        include_excluded_projects=True,
    )

    assert rows == [
        {
            "categoria_orcamento": "Bolsas",
            "orcamento_contratado": "1.000,00",
            "orcamento_contratado_valor": 1000.0,
            "total_lancamentos": 1,
        }
    ]
    assert all_rows == [
        {
            "categoria_orcamento": "Bolsas",
            "orcamento_contratado": "19.887,00",
            "orcamento_contratado_valor": 19887.0,
            "total_lancamentos": 3,
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
    instituicao_nome: str,
    instituicao_sigla: str,
    orcamento: list[dict[str, str]],
    situacao_descricao: str = "Projeto aprovado",
) -> dict[str, object]:
    return {
        "projeto_id": projeto_id,
        "projeto_titulo": projeto_titulo,
        "coordenador_nome": coordenador_nome,
        "situacao_descricao": situacao_descricao,
        "dados_coordenador": {
            "data": [
                {
                    "instituicao_nome": instituicao_nome,
                    "instituicao_sigla": instituicao_sigla,
                }
            ],
        },
        "orcamento_contratado": {"data": orcamento, "qtd": len(orcamento)},
    }
