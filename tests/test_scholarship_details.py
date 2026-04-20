from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, cast

import pytest


def test_scholarship_details_group_scholarships_by_type(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    scholarship_details = cast(
        Any,
        importlib.import_module("scripts.scholarship_details"),
    )
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[
                    {
                        "sigla": "ICT",
                        "nome": "Iniciacao Cientifica",
                        "orcamento_quantidade": "2",
                        "vlrtot": "1200",
                    },
                    {
                        "sigla": "MSC",
                        "nome": "Mestrado",
                        "orcamento_quantidade": "1",
                        "orcamento_custo": "500",
                        "orcamento_duracao": "2",
                    },
                ],
            ),
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[
                    {
                        "sigla": "ICT",
                        "nome": "Iniciacao Cientifica",
                        "orcamento_quantidade": "1",
                        "vlrtot": "600",
                    }
                ],
            ),
            _project(
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                bolsas=[
                    {
                        "sigla": "DOC",
                        "nome": "Doutorado",
                        "orcamento_quantidade": "4",
                        "vlrtot": "4000",
                    }
                ],
            ),
        ],
    )

    rows = scholarship_details.load_scholarship_details(
        input_dir,
        ["Universidade Federal do Espirito Santo | UFES - VITÓRIA"],
    )

    assert rows == [
        {
            "tipo_bolsa": "ICT",
            "nome_bolsa": "Iniciacao Cientifica",
            "quantidade_bolsas": 3,
            "valor_bolsas": "1.800,00",
            "valor_bolsas_valor": 1800.0,
            "total_lancamentos": 2,
        },
        {
            "tipo_bolsa": "MSC",
            "nome_bolsa": "Mestrado",
            "quantidade_bolsas": 1,
            "valor_bolsas": "1.000,00",
            "valor_bolsas_valor": 1000.0,
            "total_lancamentos": 1,
        },
    ]


def test_scholarship_details_load_all_institutions_when_no_filter_is_selected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    scholarship_details = cast(
        Any,
        importlib.import_module("scripts.scholarship_details"),
    )
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[
                    {
                        "sigla": "ICT",
                        "nome": "Iniciacao Cientifica",
                        "orcamento_quantidade": "2",
                        "vlrtot": "1200",
                    }
                ],
            ),
            _project(
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                bolsas=[
                    {
                        "sigla": "ICT",
                        "nome": "Iniciacao Cientifica",
                        "orcamento_quantidade": "1",
                        "vlrtot": "500",
                    }
                ],
            ),
        ],
    )

    rows = scholarship_details.load_scholarship_details(input_dir, [])

    assert rows == [
        {
            "tipo_bolsa": "ICT",
            "nome_bolsa": "Iniciacao Cientifica",
            "quantidade_bolsas": 3,
            "valor_bolsas": "1.700,00",
            "valor_bolsas_valor": 1700.0,
            "total_lancamentos": 2,
        }
    ]


def test_scholarship_details_exclude_not_contracted_projects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    scholarship_details = cast(
        Any,
        importlib.import_module("scripts.scholarship_details"),
    )
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[
                    {
                        "sigla": "ICT",
                        "nome": "Iniciacao Cientifica",
                        "orcamento_quantidade": "2",
                        "vlrtot": "1200",
                    }
                ],
                situacao_descricao="Projeto Em Andamento",
            ),
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[
                    {
                        "sigla": "ICT",
                        "nome": "Iniciacao Cientifica",
                        "orcamento_quantidade": "10",
                        "vlrtot": "9999",
                    }
                ],
                situacao_descricao="Projeto Não Contratado",
            ),
            _project(
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[
                    {
                        "sigla": "ICT",
                        "nome": "Iniciacao Cientifica",
                        "orcamento_quantidade": "20",
                        "vlrtot": "8888",
                    }
                ],
                situacao_descricao="Proposta não Contratada mas Aprovada no Mérito",
            ),
        ],
    )

    rows = scholarship_details.load_scholarship_details(
        input_dir,
        ["Universidade Federal do Espirito Santo | UFES - VITÓRIA"],
    )
    all_rows = scholarship_details.load_scholarship_details(
        input_dir,
        ["Universidade Federal do Espirito Santo | UFES - VITÓRIA"],
        include_excluded_projects=True,
    )

    assert rows == [
        {
            "tipo_bolsa": "ICT",
            "nome_bolsa": "Iniciacao Cientifica",
            "quantidade_bolsas": 2,
            "valor_bolsas": "1.200,00",
            "valor_bolsas_valor": 1200.0,
            "total_lancamentos": 1,
        }
    ]
    assert all_rows == [
        {
            "tipo_bolsa": "ICT",
            "nome_bolsa": "Iniciacao Cientifica",
            "quantidade_bolsas": 32,
            "valor_bolsas": "20.087,00",
            "valor_bolsas_valor": 20087.0,
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
    instituicao_nome: str,
    instituicao_sigla: str,
    bolsas: list[dict[str, str]],
    situacao_descricao: str = "Projeto aprovado",
) -> dict[str, object]:
    return {
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
    }
