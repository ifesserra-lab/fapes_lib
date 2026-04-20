"""Project detail aggregates for the FAPES dashboard."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import TypeAlias

from scripts.report import (
    _contracted_budget,
    _decimal,
    _institution_for_project,
    _money,
    _projects_from_file,
    _scholarship_amount,
    _scholarship_quantity,
    _should_skip_project,
)

ProjectDetailRow: TypeAlias = dict[str, object]
ProjectTimelineRow: TypeAlias = dict[str, object]

_BUDGET_COLUMN = "orcamento_contratado"
_BUDGET_VALUE_COLUMN = "orcamento_contratado_valor"
_SCHOLARSHIP_AMOUNT_COLUMN = "valor_bolsas"
_SCHOLARSHIP_AMOUNT_VALUE_COLUMN = "valor_bolsas_valor"


@dataclass(frozen=True, slots=True)
class ProjectDetail:
    ano: int | str
    projeto_id: str
    projeto_titulo: str
    projeto_data_envio: str
    projeto_data_inicio_previsto: str
    projeto_data_fim_previsto: str
    coordenador_nome: str
    situacao_descricao: str
    quantidade_bolsas: int
    valor_bolsas: Decimal
    orcamento_contratado: Decimal

    def to_row(self) -> ProjectDetailRow:
        return {
            "ano": self.ano,
            "projeto_id": self.projeto_id,
            "projeto_titulo": self.projeto_titulo,
            "projeto_data_envio": self.projeto_data_envio,
            "projeto_data_inicio_previsto": self.projeto_data_inicio_previsto,
            "projeto_data_fim_previsto": self.projeto_data_fim_previsto,
            "coordenador_nome": self.coordenador_nome,
            "situacao_descricao": self.situacao_descricao,
            "quantidade_bolsas": self.quantidade_bolsas,
            _SCHOLARSHIP_AMOUNT_COLUMN: _money(self.valor_bolsas),
            _BUDGET_COLUMN: _money(self.orcamento_contratado),
        }


@dataclass(slots=True)
class TimelineTotals:
    ano: int
    total_projetos: int = 0
    quantidade_bolsas: int = 0
    valor_bolsas: Decimal = Decimal("0")
    orcamento_contratado: Decimal = Decimal("0")

    def add_project(self, row: Mapping[str, object]) -> None:
        self.total_projetos += 1
        self.quantidade_bolsas += _int_value(row.get("quantidade_bolsas"))
        self.valor_bolsas += _decimal(row.get(_SCHOLARSHIP_AMOUNT_COLUMN))
        self.orcamento_contratado += _decimal(row.get(_BUDGET_COLUMN))

    def to_row(self) -> ProjectTimelineRow:
        return {
            "ano": self.ano,
            "total_projetos": self.total_projetos,
            "quantidade_bolsas": self.quantidade_bolsas,
            _SCHOLARSHIP_AMOUNT_COLUMN: _money(self.valor_bolsas),
            _SCHOLARSHIP_AMOUNT_VALUE_COLUMN: float(self.valor_bolsas),
            _BUDGET_COLUMN: _money(self.orcamento_contratado),
            _BUDGET_VALUE_COLUMN: float(self.orcamento_contratado),
        }


def load_project_details(
    input_dir: str | Path,
    institution_label: str,
    *,
    include_excluded_projects: bool = False,
    selected_statuses: Sequence[str] = (),
) -> list[ProjectDetailRow]:
    """Load project details for an institution name/acronym label."""

    details: list[ProjectDetail] = []
    for path in sorted(Path(input_dir).glob("*.json")):
        for projeto in _projects_from_file(path):
            if _should_skip_project(
                projeto,
                include_excluded_projects,
                selected_statuses,
            ):
                continue
            if _label_for_project(projeto) != institution_label:
                continue
            details.append(_project_detail(projeto))

    return [detail.to_row() for detail in sorted(details, key=_project_detail_sort_key)]


def load_researcher_project_details(
    input_dir: str | Path,
    researcher_query: str,
    *,
    include_excluded_projects: bool = False,
    selected_statuses: Sequence[str] = (),
) -> list[ProjectDetailRow]:
    """Load project details matching a researcher/coordinator name query."""

    normalized_query = researcher_query.casefold().strip()
    if not normalized_query:
        return []

    rows: list[ProjectDetailRow] = []
    for path in sorted(Path(input_dir).glob("*.json")):
        for projeto in _projects_from_file(path):
            if _should_skip_project(
                projeto,
                include_excluded_projects,
                selected_statuses,
            ):
                continue
            if (
                normalized_query
                not in _text(projeto.get("coordenador_nome")).casefold()
            ):
                continue

            row = _project_detail(projeto).to_row()
            institution_name, institution_acronym = _institution_for_project(projeto)
            row["instituicao_nome"] = institution_name
            row["instituicao_sigla"] = institution_acronym
            row["instituicao"] = _institution_label(
                institution_name, institution_acronym
            )
            rows.append(row)

    return sorted(rows, key=_project_row_sort_key)


def build_project_timeline(
    rows: Sequence[Mapping[str, object]],
) -> list[ProjectTimelineRow]:
    """Aggregate project counts, scholarships and budget by project year."""

    totals: dict[int, TimelineTotals] = {}
    for row in rows:
        year = row.get("ano")
        if not isinstance(year, int):
            continue
        if year not in totals:
            totals[year] = TimelineTotals(ano=year)
        totals[year].add_project(row)

    return [totals[year].to_row() for year in sorted(totals)]


def _project_detail(projeto: Mapping[str, object]) -> ProjectDetail:
    project_date = _project_date(projeto)
    return ProjectDetail(
        ano=project_date.year if project_date else "",
        projeto_id=_text(projeto.get("projeto_id")),
        projeto_titulo=_text(projeto.get("projeto_titulo")),
        projeto_data_envio=_text(projeto.get("projeto_data_envio")),
        projeto_data_inicio_previsto=_text(projeto.get("projeto_data_inicio_previsto")),
        projeto_data_fim_previsto=_text(projeto.get("projeto_data_fim_previsto")),
        coordenador_nome=_text(projeto.get("coordenador_nome")),
        situacao_descricao=_text(projeto.get("situacao_descricao")),
        quantidade_bolsas=_scholarship_quantity(projeto),
        valor_bolsas=_scholarship_amount(projeto),
        orcamento_contratado=_contracted_budget(projeto),
    )


def _project_detail_sort_key(detail: ProjectDetail) -> tuple[int, str]:
    year = detail.ano if isinstance(detail.ano, int) else 0
    return year, detail.projeto_id


def _project_row_sort_key(row: Mapping[str, object]) -> tuple[int, str]:
    year = row.get("ano")
    return year if isinstance(year, int) else 0, _text(row.get("projeto_id"))


def _label_for_project(projeto: Mapping[str, object]) -> str:
    institution_name, institution_acronym = _institution_for_project(projeto)
    return _institution_label(institution_name, institution_acronym)


def _institution_label(institution_name: str, institution_acronym: str) -> str:
    if institution_name and institution_acronym:
        return f"{institution_name} | {institution_acronym}"
    if institution_name:
        return institution_name
    return institution_acronym


def _project_date(projeto: Mapping[str, object]) -> date | None:
    for field in ("projeto_data_envio", "projeto_data_inicio_previsto"):
        parsed = _parse_date(projeto.get(field))
        if parsed is not None:
            return parsed

    return None


def _parse_date(value: object) -> date | None:
    raw_value = _text(value)
    if not raw_value:
        return None

    date_part = raw_value.split()[0]
    for date_format in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_part, date_format).date()
        except ValueError:
            continue

    return None


def _int_value(value: object) -> int:
    return int(_decimal(value))


def _text(value: object) -> str:
    if value is None:
        return ""

    return str(value).strip()
