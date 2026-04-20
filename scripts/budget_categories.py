"""Budget category aggregates for the FAPES dashboard."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import TypeAlias

from scripts.report import (
    _decimal,
    _envelope_records,
    _institution_for_project,
    _is_not_contracted_project,
    _money,
    _projects_from_file,
)

BudgetCategoryRow: TypeAlias = dict[str, object]

_CATEGORY_COLUMN = "categoria_orcamento"
_BUDGET_COLUMN = "orcamento_contratado"
_BUDGET_VALUE_COLUMN = "orcamento_contratado_valor"
_COUNT_COLUMN = "total_lancamentos"
_UNKNOWN_CATEGORY = "Outros"


@dataclass(slots=True)
class BudgetCategoryTotals:
    categoria_orcamento: str
    orcamento_contratado: Decimal = Decimal("0")
    total_lancamentos: int = 0

    def add_item(self, item: Mapping[str, object]) -> None:
        self.orcamento_contratado += _decimal(item.get("valor_categoria"))
        self.total_lancamentos += 1

    def to_row(self) -> BudgetCategoryRow:
        return {
            _CATEGORY_COLUMN: self.categoria_orcamento,
            _BUDGET_COLUMN: _money(self.orcamento_contratado),
            _BUDGET_VALUE_COLUMN: float(self.orcamento_contratado),
            _COUNT_COLUMN: self.total_lancamentos,
        }


def load_budget_categories(
    input_dir: str | Path,
    institution_labels: Sequence[str],
    *,
    include_excluded_projects: bool = False,
) -> list[BudgetCategoryRow]:
    """Aggregate contracted budget by readable category for selected institutions."""

    selected_labels = set(institution_labels)
    totals: dict[str, BudgetCategoryTotals] = {}
    for path in sorted(Path(input_dir).glob("*.json")):
        for projeto in _projects_from_file(path):
            if _should_skip_project(projeto, include_excluded_projects):
                continue
            if selected_labels and _label_for_project(projeto) not in selected_labels:
                continue

            for item in _envelope_records(projeto.get("orcamento_contratado")):
                category = _readable_category(item.get("descricao_categoria"))
                if category not in totals:
                    totals[category] = BudgetCategoryTotals(
                        categoria_orcamento=category
                    )
                totals[category].add_item(item)

    return [
        totals[category].to_row()
        for category in sorted(
            totals,
            key=lambda name: (
                -totals[name].orcamento_contratado,
                name.casefold(),
            ),
        )
    ]


def _should_skip_project(
    projeto: Mapping[str, object],
    include_excluded_projects: bool,
) -> bool:
    return not include_excluded_projects and _is_not_contracted_project(projeto)


def _readable_category(value: object) -> str:
    description = _text(value).casefold()
    if not description:
        return _UNKNOWN_CATEGORY

    if "bolsa" in description:
        return "Bolsas"
    if "material de consumo" in description:
        return "Material"
    if "equipamento" in description or "permanente" in description:
        return "Capital"
    if _contains_any(
        description,
        ("diária", "diaria", "passagem", "passagen", "hospedagem"),
    ):
        return "Viagem"
    if (
        "serviço" in description
        or "servico" in description
        or "pessoa jurídica" in description
    ):
        return "Serviços"
    if "pessoal" in description or "encargo" in description:
        return "Pessoal e encargos"

    return _UNKNOWN_CATEGORY


def _contains_any(value: str, patterns: Sequence[str]) -> bool:
    return any(pattern in value for pattern in patterns)


def _label_for_project(projeto: Mapping[str, object]) -> str:
    institution_name, institution_acronym = _institution_for_project(projeto)
    if institution_name and institution_acronym:
        return f"{institution_name} | {institution_acronym}"
    if institution_name:
        return institution_name
    return institution_acronym


def _text(value: object) -> str:
    if value is None:
        return ""

    return str(value).strip()
