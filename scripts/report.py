"""Generate institution totals from downloaded FAPES edital project files."""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final, TypeAlias

JsonObject: TypeAlias = dict[str, object]
ReportRow: TypeAlias = dict[str, object]

_DEFAULT_INPUT_DIR: Final = Path("downloads/projetos_por_edital")
_DEFAULT_OUTPUT: Final = Path("downloads/relatorio_instituicoes.csv")
_REPORT_FIELDS: Final = (
    "instituicao_nome",
    "instituicao_sigla",
    "quantidade_bolsas",
    "valor_bolsas",
    "orcamento_contratado",
    "total_projetos",
)
_EXCLUDED_PROJECT_AUDIT_FIELDS: Final = (
    "arquivo_origem",
    "projeto_id",
    "projeto_titulo",
    "coordenador_nome",
    "instituicao_nome",
    "instituicao_sigla",
    "situacao_descricao",
    "quantidade_bolsas",
    "valor_bolsas",
    "orcamento_contratado",
)
_UNKNOWN_INSTITUTION = "Sem informacao"
_EXCLUDED_PROJECT_STATUS_LABELS: Final = (
    "Projeto Não Contratado",
    "Proposta não Contratada mas Aprovada no Mérito",
)
_EXCLUDED_PROJECT_STATUSES: Final = frozenset(
    label.casefold() for label in _EXCLUDED_PROJECT_STATUS_LABELS
)


@dataclass(slots=True)
class InstitutionTotals:
    instituicao_nome: str
    instituicao_sigla: str
    quantidade_bolsas: int = 0
    valor_bolsas: Decimal = Decimal("0")
    orcamento_contratado: Decimal = Decimal("0")
    total_projetos: int = 0

    def add_project(self, projeto: Mapping[str, object]) -> None:
        self.quantidade_bolsas += _scholarship_quantity(projeto)
        self.valor_bolsas += _scholarship_amount(projeto)
        self.orcamento_contratado += _contracted_budget(projeto)
        self.total_projetos += 1

    def to_row(self) -> ReportRow:
        return {
            "instituicao_nome": self.instituicao_nome,
            "instituicao_sigla": self.instituicao_sigla,
            "quantidade_bolsas": self.quantidade_bolsas,
            "valor_bolsas": _money(self.valor_bolsas),
            "orcamento_contratado": _money(self.orcamento_contratado),
            "total_projetos": self.total_projetos,
        }


def generate_report(
    input_dir: str | Path = _DEFAULT_INPUT_DIR,
    *,
    include_excluded_projects: bool = False,
) -> list[ReportRow]:
    """Aggregate scholarships and budget by institution name and acronym."""

    totals: dict[tuple[str, str], InstitutionTotals] = {}
    for path in sorted(Path(input_dir).glob("*.json")):
        for projeto in _projects_from_file(path):
            if _should_skip_project(projeto, include_excluded_projects):
                continue
            instituicao_nome, instituicao_sigla = _institution_for_project(projeto)
            key = (instituicao_nome, instituicao_sigla)
            if key not in totals:
                totals[key] = InstitutionTotals(
                    instituicao_nome=instituicao_nome,
                    instituicao_sigla=instituicao_sigla,
                )
            totals[key].add_project(projeto)

    return [total.to_row() for total in totals.values()]


def generate_excluded_projects_audit(
    input_dir: str | Path = _DEFAULT_INPUT_DIR,
) -> list[ReportRow]:
    """Return projects removed by the contracted-project rule for audit exports."""

    rows: list[ReportRow] = []
    for path in sorted(Path(input_dir).glob("*.json")):
        for projeto in _projects_from_file(path):
            if not _is_not_contracted_project(projeto):
                continue
            rows.append(_excluded_project_audit_row(path, projeto))

    return rows


def write_report(rows: Sequence[Mapping[str, object]], output: str | Path) -> Path:
    """Write a report as CSV or JSON according to the output file suffix."""

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.suffix.lower() == ".json":
        destination.write_text(
            f"{json.dumps(list(rows), ensure_ascii=False, indent=2)}\n",
            encoding="utf-8",
        )
        return destination

    with destination.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(_REPORT_FIELDS))
        writer.writeheader()
        writer.writerows(rows)

    return destination


def run(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    rows = generate_report(args.input_dir)
    output = write_report(rows, args.output)

    total_projects = sum(_int_quantity(row["total_projetos"]) for row in rows)
    total_scholarships = sum(_int_quantity(row["quantidade_bolsas"]) for row in rows)
    total_scholarship_amount = sum(
        (_decimal(row["valor_bolsas"]) for row in rows),
        Decimal("0"),
    )
    total_budget = sum(
        (_decimal(row["orcamento_contratado"]) for row in rows),
        Decimal("0"),
    )

    print(f"Relatorio gerado: {output}")
    print(f"Instituicoes: {len(rows)}")
    print(f"Projetos: {total_projects}")
    print(f"Bolsas: {total_scholarships}")
    print(f"Valor bolsas: {_money(total_scholarship_amount)}")
    print(f"Orcamento contratado: {_money(total_budget)}")
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gera relatorio por instituicao_nome e instituicao_sigla "
            "a partir dos projetos baixados por edital."
        ),
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=_DEFAULT_INPUT_DIR,
        help=(
            "Diretorio com arquivos edital_*_projetos.json. "
            f"Padrao: {_DEFAULT_INPUT_DIR}"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        help=f"Arquivo CSV ou JSON de saida. Padrao: {_DEFAULT_OUTPUT}",
    )
    return parser.parse_args(argv)


def _projects_from_file(path: Path) -> list[Mapping[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return []

    data = payload.get("data")
    if not isinstance(data, Mapping):
        return []

    projetos = data.get("projetos")
    if not isinstance(projetos, list):
        return []

    return [projeto for projeto in projetos if isinstance(projeto, Mapping)]


def _institution_for_project(projeto: Mapping[str, object]) -> tuple[str, str]:
    for coordenador in _envelope_records(projeto.get("dados_coordenador")):
        nome = _text(coordenador.get("instituicao_nome"))
        sigla = _text(coordenador.get("instituicao_sigla"))
        if nome or sigla:
            return nome or _UNKNOWN_INSTITUTION, sigla or _UNKNOWN_INSTITUTION

    return _UNKNOWN_INSTITUTION, _UNKNOWN_INSTITUTION


def _is_not_contracted_project(projeto: Mapping[str, object]) -> bool:
    return _is_not_contracted_status(projeto.get("situacao_descricao"))


def _should_skip_project(
    projeto: Mapping[str, object],
    include_excluded_projects: bool,
) -> bool:
    return not include_excluded_projects and _is_not_contracted_project(projeto)


def _is_not_contracted_status(value: object) -> bool:
    return _text(value).casefold() in _EXCLUDED_PROJECT_STATUSES


def excluded_project_status_labels() -> tuple[str, ...]:
    """Return project statuses excluded from contracted-project aggregates."""

    return _EXCLUDED_PROJECT_STATUS_LABELS


def _excluded_project_audit_row(path: Path, projeto: Mapping[str, object]) -> ReportRow:
    instituicao_nome, instituicao_sigla = _institution_for_project(projeto)
    return {
        "arquivo_origem": path.name,
        "projeto_id": _text(projeto.get("projeto_id")),
        "projeto_titulo": _text(projeto.get("projeto_titulo")),
        "coordenador_nome": _text(projeto.get("coordenador_nome")),
        "instituicao_nome": instituicao_nome,
        "instituicao_sigla": instituicao_sigla,
        "situacao_descricao": _text(projeto.get("situacao_descricao")),
        "quantidade_bolsas": _scholarship_quantity(projeto),
        "valor_bolsas": _money(_scholarship_amount(projeto)),
        "orcamento_contratado": _money(_contracted_budget(projeto)),
    }


def _scholarship_quantity(projeto: Mapping[str, object]) -> int:
    total = 0
    for bolsa in _envelope_records(projeto.get("quadroBolsas")):
        if "orcamento_quantidade" in bolsa:
            total += _int_quantity(bolsa.get("orcamento_quantidade"))
            continue
        total += 1

    return total


def _contracted_budget(projeto: Mapping[str, object]) -> Decimal:
    total = Decimal("0")
    for categoria in _envelope_records(projeto.get("orcamento_contratado")):
        total += _decimal(categoria.get("valor_categoria"))

    return total


def _scholarship_amount(projeto: Mapping[str, object]) -> Decimal:
    return _decimal(projeto.get("valor_bolsa"))


def _envelope_records(value: object) -> list[Mapping[str, object]]:
    if isinstance(value, Mapping):
        data = value.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, Mapping)]

    if isinstance(value, list):
        return [item for item in value if isinstance(item, Mapping)]

    return []


def _decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0")

    raw_value = str(value).strip()
    if not raw_value:
        return Decimal("0")

    normalized = raw_value.replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")

    try:
        return Decimal(normalized)
    except InvalidOperation:
        return Decimal("0")


def _int_quantity(value: object) -> int:
    return int(_decimal(value))


def _text(value: object) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _money(value: Decimal) -> str:
    formatted = f"{value.quantize(Decimal('0.01')):,.2f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


if __name__ == "__main__":
    raise SystemExit(run())
