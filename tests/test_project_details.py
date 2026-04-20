from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, cast

import pytest


def test_project_details_loads_projects_for_selected_institution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    project_details = cast(Any, importlib.import_module("scripts.project_details"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                projeto_id="101",
                projeto_titulo="Projeto de energia solar",
                projeto_data_envio="24/07/2015",
                projeto_data_inicio_previsto="01/08/2015",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "2"}],
                orcamento=[{"valor_categoria": "1234.56"}],
                valor_bolsa="4500",
            ),
            _project(
                projeto_id="202",
                projeto_titulo="Projeto de saneamento",
                projeto_data_envio="02/03/2016",
                projeto_data_inicio_previsto="01/04/2016",
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES",
                bolsas=[{"orcamento_quantidade": "7"}],
                orcamento=[{"valor_categoria": "900"}],
                valor_bolsa="7000",
            ),
        ],
    )

    rows = project_details.load_project_details(
        input_dir,
        "Universidade Federal do Espirito Santo | UFES - VITÓRIA",
    )

    assert rows == [
        {
            "ano": 2015,
            "projeto_id": "101",
            "projeto_titulo": "Projeto de energia solar",
            "projeto_data_envio": "24/07/2015",
            "projeto_data_inicio_previsto": "01/08/2015",
            "projeto_data_fim_previsto": "",
            "coordenador_nome": "Coordenador 101",
            "situacao_descricao": "Projeto aprovado",
            "quantidade_bolsas": 2,
            "valor_bolsas": "4.500,00",
            "orcamento_contratado": "1.234,56",
        }
    ]


def test_project_timeline_groups_projects_by_year(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    project_details = cast(Any, importlib.import_module("scripts.project_details"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                projeto_id="101",
                projeto_titulo="Projeto A",
                projeto_data_envio="24/07/2015",
                projeto_data_inicio_previsto="01/08/2015",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "2"}],
                orcamento=[{"valor_categoria": "1000"}],
                valor_bolsa="2000",
            ),
            _project(
                projeto_id="102",
                projeto_titulo="Projeto B",
                projeto_data_envio="30/09/2015",
                projeto_data_inicio_previsto="01/10/2015",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "3"}],
                orcamento=[{"valor_categoria": "250.5"}],
                valor_bolsa="3000.5",
            ),
            _project(
                projeto_id="103",
                projeto_titulo="Projeto C",
                projeto_data_envio="",
                projeto_data_inicio_previsto="01/02/2016",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "4"}],
                orcamento=[{"valor_categoria": "80"}],
                valor_bolsa="400",
            ),
        ],
    )
    rows = project_details.load_project_details(
        input_dir,
        "Universidade Federal do Espirito Santo | UFES - VITÓRIA",
    )

    timeline = project_details.build_project_timeline(rows)

    assert timeline == [
        {
            "ano": 2015,
            "total_projetos": 2,
            "quantidade_bolsas": 5,
            "valor_bolsas": "5.000,50",
            "valor_bolsas_valor": 5000.5,
            "orcamento_contratado": "1.250,50",
            "orcamento_contratado_valor": 1250.5,
        },
        {
            "ano": 2016,
            "total_projetos": 1,
            "quantidade_bolsas": 4,
            "valor_bolsas": "400,00",
            "valor_bolsas_valor": 400.0,
            "orcamento_contratado": "80,00",
            "orcamento_contratado_valor": 80.0,
        },
    ]


def test_project_details_exclude_not_contracted_projects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    project_details = cast(Any, importlib.import_module("scripts.project_details"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                projeto_id="101",
                projeto_titulo="Projeto em andamento",
                projeto_data_envio="24/07/2015",
                projeto_data_inicio_previsto="01/08/2015",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "2"}],
                orcamento=[{"valor_categoria": "1000"}],
                valor_bolsa="2000",
                situacao_descricao="Projeto Em Andamento",
            ),
            _project(
                projeto_id="102",
                projeto_titulo="Projeto nao contratado",
                projeto_data_envio="24/07/2015",
                projeto_data_inicio_previsto="01/08/2015",
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
                projeto_data_envio="24/07/2015",
                projeto_data_inicio_previsto="01/08/2015",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "20"}],
                orcamento=[{"valor_categoria": "8888"}],
                valor_bolsa="888",
                situacao_descricao="Proposta não Contratada mas Aprovada no Mérito",
            ),
        ],
    )

    rows = project_details.load_project_details(
        input_dir,
        "Universidade Federal do Espirito Santo | UFES - VITÓRIA",
    )
    all_rows = project_details.load_project_details(
        input_dir,
        "Universidade Federal do Espirito Santo | UFES - VITÓRIA",
        include_excluded_projects=True,
    )

    assert [row["projeto_id"] for row in rows] == ["101"]
    assert [row["projeto_id"] for row in all_rows] == ["101", "102", "103"]


def test_project_details_loads_projects_for_researcher_query(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    project_details = cast(Any, importlib.import_module("scripts.project_details"))
    input_dir = tmp_path / "projetos_por_edital"
    input_dir.mkdir()
    _write_project_file(
        input_dir / "edital_1_projetos.json",
        [
            _project(
                projeto_id="101",
                projeto_titulo="ConectaFapes",
                projeto_data_envio="26/10/2023",
                projeto_data_inicio_previsto="07/11/2023",
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES - SERRA",
                bolsas=[{"orcamento_quantidade": "2"}],
                orcamento=[{"valor_categoria": "1000"}],
                valor_bolsa="2000",
                coordenador_nome="Paulo Santos",
                situacao_descricao="Projeto Em Andamento",
            ),
            _project(
                projeto_id="102",
                projeto_titulo="Outro projeto",
                projeto_data_envio="26/10/2023",
                projeto_data_inicio_previsto="07/11/2023",
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES - SERRA",
                bolsas=[{"orcamento_quantidade": "10"}],
                orcamento=[{"valor_categoria": "9999"}],
                valor_bolsa="999",
                coordenador_nome="Paulo Santos",
                situacao_descricao="Projeto Não Contratado",
            ),
            _project(
                projeto_id="104",
                projeto_titulo="Proposta aprovada no merito",
                projeto_data_envio="26/10/2023",
                projeto_data_inicio_previsto="07/11/2023",
                instituicao_nome="Instituto Federal do Espirito Santo",
                instituicao_sigla="IFES - SERRA",
                bolsas=[{"orcamento_quantidade": "20"}],
                orcamento=[{"valor_categoria": "8888"}],
                valor_bolsa="888",
                coordenador_nome="Paulo Santos",
                situacao_descricao="Proposta não Contratada mas Aprovada no Mérito",
            ),
            _project(
                projeto_id="103",
                projeto_titulo="Pesquisa aplicada",
                projeto_data_envio="26/10/2023",
                projeto_data_inicio_previsto="07/11/2023",
                instituicao_nome="Universidade Federal do Espirito Santo",
                instituicao_sigla="UFES - VITÓRIA",
                bolsas=[{"orcamento_quantidade": "1"}],
                orcamento=[{"valor_categoria": "500"}],
                valor_bolsa="300",
                coordenador_nome="Maria Silva",
            ),
        ],
    )

    rows = project_details.load_researcher_project_details(input_dir, "paulo")
    all_rows = project_details.load_researcher_project_details(
        input_dir,
        "paulo",
        include_excluded_projects=True,
    )

    assert rows == [
        {
            "ano": 2023,
            "projeto_id": "101",
            "projeto_titulo": "ConectaFapes",
            "projeto_data_envio": "26/10/2023",
            "projeto_data_inicio_previsto": "07/11/2023",
            "projeto_data_fim_previsto": "",
            "coordenador_nome": "Paulo Santos",
            "situacao_descricao": "Projeto Em Andamento",
            "quantidade_bolsas": 2,
            "valor_bolsas": "2.000,00",
            "orcamento_contratado": "1.000,00",
            "instituicao_nome": "Instituto Federal do Espirito Santo",
            "instituicao_sigla": "IFES - SERRA",
            "instituicao": "Instituto Federal do Espirito Santo | IFES - SERRA",
        }
    ]
    assert [row["projeto_id"] for row in all_rows] == ["101", "102", "104"]


def _write_project_file(path: Path, projetos: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps({"data": {"projetos": projetos}}, ensure_ascii=False),
        encoding="utf-8",
    )


def _project(
    *,
    projeto_id: str,
    projeto_titulo: str,
    projeto_data_envio: str,
    projeto_data_inicio_previsto: str,
    instituicao_nome: str,
    instituicao_sigla: str,
    bolsas: list[dict[str, str]],
    orcamento: list[dict[str, str]],
    valor_bolsa: str = "0",
    situacao_descricao: str = "Projeto aprovado",
    coordenador_nome: str | None = None,
) -> dict[str, object]:
    return {
        "projeto_id": projeto_id,
        "projeto_titulo": projeto_titulo,
        "valor_bolsa": valor_bolsa,
        "projeto_data_envio": projeto_data_envio,
        "projeto_data_inicio_previsto": projeto_data_inicio_previsto,
        "projeto_data_fim_previsto": "",
        "coordenador_nome": coordenador_nome or f"Coordenador {projeto_id}",
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
