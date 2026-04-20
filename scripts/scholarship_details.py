"""Scholarship detail aggregates for the FAPES dashboard."""

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
    _int_quantity,
    _is_not_contracted_project,
    _money,
    _projects_from_file,
)

ScholarshipDetailRow: TypeAlias = dict[str, object]

_TYPE_COLUMN = "tipo_bolsa"
_NAME_COLUMN = "nome_bolsa"
_QUANTITY_COLUMN = "quantidade_bolsas"
_AMOUNT_COLUMN = "valor_bolsas"
_AMOUNT_VALUE_COLUMN = "valor_bolsas_valor"
_COUNT_COLUMN = "total_lancamentos"
_UNKNOWN_SCHOLARSHIP = "Sem informacao"


@dataclass(slots=True)
class ScholarshipDetailTotals:
    tipo_bolsa: str
    nome_bolsa: str
    quantidade_bolsas: int = 0
    valor_bolsas: Decimal = Decimal("0")
    total_lancamentos: int = 0

    def add_item(self, item: Mapping[str, object]) -> None:
        self.quantidade_bolsas += _scholarship_quantity(item)
        self.valor_bolsas += _scholarship_amount(item)
        self.total_lancamentos += 1

    def to_row(self) -> ScholarshipDetailRow:
        return {
            _TYPE_COLUMN: self.tipo_bolsa,
            _NAME_COLUMN: self.nome_bolsa,
            _QUANTITY_COLUMN: self.quantidade_bolsas,
            _AMOUNT_COLUMN: _money(self.valor_bolsas),
            _AMOUNT_VALUE_COLUMN: float(self.valor_bolsas),
            _COUNT_COLUMN: self.total_lancamentos,
        }


def load_scholarship_details(
    input_dir: str | Path,
    institution_labels: Sequence[str],
    *,
    include_excluded_projects: bool = False,
) -> list[ScholarshipDetailRow]:
    """Aggregate scholarship quantity and amount by scholarship type."""

    selected_labels = set(institution_labels)
    totals: dict[str, ScholarshipDetailTotals] = {}
    for path in sorted(Path(input_dir).glob("*.json")):
        for projeto in _projects_from_file(path):
            if _should_skip_project(projeto, include_excluded_projects):
                continue
            if selected_labels and _label_for_project(projeto) not in selected_labels:
                continue

            for item in _envelope_records(projeto.get("quadroBolsas")):
                key = _scholarship_type(item)
                if key not in totals:
                    totals[key] = ScholarshipDetailTotals(
                        tipo_bolsa=key,
                        nome_bolsa=_scholarship_name(item),
                    )
                totals[key].add_item(item)

    return [
        totals[key].to_row()
        for key in sorted(
            totals,
            key=lambda value: (-totals[value].valor_bolsas, value.casefold()),
        )
    ]


def _should_skip_project(
    projeto: Mapping[str, object],
    include_excluded_projects: bool,
) -> bool:
    return not include_excluded_projects and _is_not_contracted_project(projeto)


def _scholarship_type(item: Mapping[str, object]) -> str:
    return _text(item.get("sigla")) or _scholarship_name(item)


def _scholarship_name(item: Mapping[str, object]) -> str:
    return _text(item.get("nome")) or _UNKNOWN_SCHOLARSHIP


def _scholarship_quantity(item: Mapping[str, object]) -> int:
    if "orcamento_quantidade" in item:
        return _int_quantity(item.get("orcamento_quantidade"))
    if "cotas" in item:
        return _int_quantity(item.get("cotas"))
    return 1


def _scholarship_amount(item: Mapping[str, object]) -> Decimal:
    amount = _decimal(item.get("vlrtot"))
    if amount != Decimal("0"):
        return amount

    return (
        _decimal(item.get("orcamento_custo"))
        * _decimal(item.get("orcamento_duracao") or "1")
        * Decimal(_scholarship_quantity(item))
    )


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
