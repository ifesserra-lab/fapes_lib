"""Generate institution totals from downloaded FAPES edital project files."""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
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
_RESEARCHER_SCHOLARSHIP_FIELDS: Final = (
    "arquivo_origem",
    "pesquisador_id",
    "pesquisador_nome",
    "instituicao_nome",
    "instituicao_sigla",
    "projeto_id",
    "projeto_titulo",
    "situacao_descricao",
    "bolsa_sigla",
    "bolsa_nome",
    "quantidade",
    "duracao",
    "valor_unitario",
    "valor_total",
)
_RESEARCHER_SCHOLARSHIP_SUMMARY_FIELDS: Final = (
    "pesquisador_id",
    "pesquisador_nome",
    "instituicoes",
    "total_projetos",
    "total_lancamentos_bolsa",
    "quantidade_bolsas",
    "valor_total_bolsas",
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


@dataclass(slots=True)
class ResearcherScholarshipTotals:
    pesquisador_id: str
    pesquisador_nome: str
    instituicoes: set[str] = field(default_factory=set)
    projetos: set[str] = field(default_factory=set)
    total_lancamentos_bolsa: int = 0
    quantidade_bolsas: int = 0
    valor_total_bolsas: Decimal = Decimal("0")

    def add_scholarship(self, row: Mapping[str, object]) -> None:
        institution = _institution_label_from_parts(
            row.get("instituicao_nome"),
            row.get("instituicao_sigla"),
        )
        if institution:
            self.instituicoes.add(institution)

        project_key = _researcher_project_key(row)
        if project_key:
            self.projetos.add(project_key)

        self.total_lancamentos_bolsa += 1
        self.quantidade_bolsas += _int_quantity(row.get("quantidade"))
        self.valor_total_bolsas += _decimal(row.get("valor_total"))

    def to_row(self) -> ReportRow:
        return {
            "pesquisador_id": self.pesquisador_id,
            "pesquisador_nome": self.pesquisador_nome,
            "instituicoes": "; ".join(sorted(self.instituicoes, key=str.casefold)),
            "total_projetos": len(self.projetos),
            "total_lancamentos_bolsa": self.total_lancamentos_bolsa,
            "quantidade_bolsas": self.quantidade_bolsas,
            "valor_total_bolsas": _money(self.valor_total_bolsas),
        }


def generate_report(
    input_dir: str | Path = _DEFAULT_INPUT_DIR,
    *,
    include_excluded_projects: bool = False,
    selected_statuses: Sequence[str] = (),
) -> list[ReportRow]:
    """Aggregate scholarships and budget by institution name and acronym."""

    totals: dict[tuple[str, str], InstitutionTotals] = {}
    for path in sorted(Path(input_dir).glob("*.json")):
        for projeto in _projects_from_file(path):
            if _should_skip_project(
                projeto,
                include_excluded_projects,
                selected_statuses,
            ):
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
    *,
    selected_statuses: Sequence[str] = (),
) -> list[ReportRow]:
    """Return projects removed by the contracted-project rule for audit exports."""

    rows: list[ReportRow] = []
    for path in sorted(Path(input_dir).glob("*.json")):
        for projeto in _projects_from_file(path):
            if not _is_not_contracted_project(projeto):
                continue
            if not _project_matches_status(projeto, selected_statuses):
                continue
            rows.append(_excluded_project_audit_row(path, projeto))

    return rows


def load_project_status_options(
    input_dir: str | Path = _DEFAULT_INPUT_DIR,
    *,
    include_excluded_projects: bool = False,
) -> list[str]:
    """Return available project statuses for dashboard filters."""

    statuses: set[str] = set()
    for path in sorted(Path(input_dir).glob("*.json")):
        for projeto in _projects_from_file(path):
            if _should_skip_project(projeto, include_excluded_projects, ()):
                continue
            status = _text(projeto.get("situacao_descricao"))
            if status:
                statuses.add(status)

    return sorted(statuses, key=str.casefold)


def generate_researcher_scholarships_report(
    input_dir: str | Path = _DEFAULT_INPUT_DIR,
    *,
    include_excluded_projects: bool = False,
    selected_statuses: Sequence[str] = (),
) -> list[ReportRow]:
    """Return scholarship lines grouped with project researcher metadata."""

    rows: list[ReportRow] = []
    for path in sorted(Path(input_dir).glob("*.json")):
        for projeto in _projects_from_file(path):
            if _should_skip_project(
                projeto,
                include_excluded_projects,
                selected_statuses,
            ):
                continue
            for bolsa in _envelope_records(projeto.get("quadroBolsas")):
                rows.append(_researcher_scholarship_row(path, projeto, bolsa))

    return rows


def generate_researcher_scholarships_summary(
    input_dir: str | Path = _DEFAULT_INPUT_DIR,
    *,
    include_excluded_projects: bool = False,
    selected_statuses: Sequence[str] = (),
) -> list[ReportRow]:
    """Aggregate scholarship quantities and amounts by researcher."""

    scholarship_rows = generate_researcher_scholarships_report(
        input_dir,
        include_excluded_projects=include_excluded_projects,
        selected_statuses=selected_statuses,
    )
    return summarize_researcher_scholarships(scholarship_rows)


def summarize_researcher_scholarships(
    rows: Sequence[Mapping[str, object]],
) -> list[ReportRow]:
    """Aggregate already-loaded researcher scholarship rows."""

    totals: dict[tuple[str, str], ResearcherScholarshipTotals] = {}
    for row in rows:
        pesquisador_id = _text(row.get("pesquisador_id"))
        pesquisador_nome = _text(row.get("pesquisador_nome")) or _UNKNOWN_INSTITUTION
        key = (pesquisador_id, pesquisador_nome)
        if key not in totals:
            totals[key] = ResearcherScholarshipTotals(
                pesquisador_id=pesquisador_id,
                pesquisador_nome=pesquisador_nome,
            )
        totals[key].add_scholarship(row)

    ordered_totals = sorted(
        totals.values(),
        key=lambda total: (
            -total.valor_total_bolsas,
            total.pesquisador_nome.casefold(),
            total.pesquisador_id,
        ),
    )
    return [total.to_row() for total in ordered_totals]


def write_report(rows: Sequence[Mapping[str, object]], output: str | Path) -> Path:
    """Write a report as CSV or JSON according to the output file suffix."""

    return _write_rows(rows, output, _REPORT_FIELDS)


def write_researcher_scholarships_report(
    rows: Sequence[Mapping[str, object]],
    output: str | Path,
) -> Path:
    """Write researcher scholarship lines as CSV or JSON."""

    return _write_rows(rows, output, _RESEARCHER_SCHOLARSHIP_FIELDS)


def write_researcher_scholarships_summary_report(
    rows: Sequence[Mapping[str, object]],
    output: str | Path,
) -> Path:
    """Write researcher scholarship summary rows as CSV or JSON."""

    return _write_rows(rows, output, _RESEARCHER_SCHOLARSHIP_SUMMARY_FIELDS)


def _write_rows(
    rows: Sequence[Mapping[str, object]],
    output: str | Path,
    fields: Sequence[str],
) -> Path:
    """Write rows as CSV or JSON according to the output file suffix."""

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.suffix.lower() == ".json":
        destination.write_text(
            f"{json.dumps(list(rows), ensure_ascii=False, indent=2)}\n",
            encoding="utf-8",
        )
        return destination

    with destination.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(fields))
        writer.writeheader()
        writer.writerows(rows)

    return destination


def run(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    rows = generate_report(args.input_dir)
    output = write_report(rows, args.output)
    researcher_scholarships_output = None
    researcher_scholarships_summary_output = None
    if args.researcher_scholarships_output is not None:
        researcher_scholarship_rows = generate_researcher_scholarships_report(
            args.input_dir
        )
        researcher_scholarships_output = write_researcher_scholarships_report(
            researcher_scholarship_rows,
            args.researcher_scholarships_output,
        )

    if args.researcher_scholarships_summary_output is not None:
        researcher_scholarship_summary_rows = generate_researcher_scholarships_summary(
            args.input_dir
        )
        researcher_scholarships_summary_output = (
            write_researcher_scholarships_summary_report(
                researcher_scholarship_summary_rows,
                args.researcher_scholarships_summary_output,
            )
        )

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
    if researcher_scholarships_output is not None:
        print(
            "Relatorio de pesquisadores e bolsas gerado: "
            f"{researcher_scholarships_output}"
        )
    if researcher_scholarships_summary_output is not None:
        print(
            "Resumo de pesquisadores e bolsas gerado: "
            f"{researcher_scholarships_summary_output}"
        )
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
    parser.add_argument(
        "--researcher-scholarships-output",
        type=Path,
        default=None,
        help=(
            "Arquivo CSV ou JSON para detalhar pesquisadores e bolsas recebidas. "
            "Quando omitido, este relatorio nao e gerado."
        ),
    )
    parser.add_argument(
        "--researcher-scholarships-summary-output",
        type=Path,
        default=None,
        help=(
            "Arquivo CSV ou JSON para resumir bolsas por pesquisador. "
            "Quando omitido, este resumo nao e gerado."
        ),
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
    selected_statuses: Sequence[str],
) -> bool:
    if not include_excluded_projects and _is_not_contracted_project(projeto):
        return True

    return not _project_matches_status(projeto, selected_statuses)


def _project_matches_status(
    projeto: Mapping[str, object],
    selected_statuses: Sequence[str],
) -> bool:
    if not selected_statuses:
        return True

    statuses = {status.strip() for status in selected_statuses if status.strip()}
    if not statuses:
        return True

    return _text(projeto.get("situacao_descricao")) in statuses


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


def _researcher_scholarship_row(
    path: Path,
    projeto: Mapping[str, object],
    bolsa: Mapping[str, object],
) -> ReportRow:
    pesquisador_id, pesquisador_nome = _researcher_for_project(projeto)
    instituicao_nome, instituicao_sigla = _institution_for_project(projeto)
    quantity = _scholarship_item_quantity(bolsa)
    duration = _scholarship_item_duration(bolsa)
    total_amount = _scholarship_item_amount(bolsa)
    unit_amount = _scholarship_item_unit_amount(
        bolsa,
        total_amount,
        quantity,
        duration,
    )
    return {
        "arquivo_origem": path.name,
        "pesquisador_id": pesquisador_id,
        "pesquisador_nome": pesquisador_nome,
        "instituicao_nome": instituicao_nome,
        "instituicao_sigla": instituicao_sigla,
        "projeto_id": _text(projeto.get("projeto_id")),
        "projeto_titulo": _text(projeto.get("projeto_titulo")),
        "situacao_descricao": _text(projeto.get("situacao_descricao")),
        "bolsa_sigla": _scholarship_item_acronym(bolsa),
        "bolsa_nome": _scholarship_item_name(bolsa),
        "quantidade": quantity,
        "duracao": duration,
        "valor_unitario": _money(unit_amount),
        "valor_total": _money(total_amount),
    }


def _institution_label_from_parts(name: object, acronym: object) -> str:
    institution_name = _text(name)
    institution_acronym = _text(acronym)
    if institution_name and institution_acronym:
        return f"{institution_name} | {institution_acronym}"
    return institution_name or institution_acronym


def _researcher_project_key(row: Mapping[str, object]) -> str:
    project_id = _text(row.get("projeto_id"))
    if project_id:
        return project_id

    return "|".join(
        value
        for value in (
            _text(row.get("arquivo_origem")),
            _text(row.get("projeto_titulo")),
            _institution_label_from_parts(
                row.get("instituicao_nome"),
                row.get("instituicao_sigla"),
            ),
        )
        if value
    )


def _researcher_for_project(projeto: Mapping[str, object]) -> tuple[str, str]:
    for coordenador in _envelope_records(projeto.get("dados_coordenador")):
        pesquisador_id = _text(coordenador.get("pesquisador_id"))
        pesquisador_nome = _text(coordenador.get("pesquisador_nome"))
        if pesquisador_id or pesquisador_nome:
            return pesquisador_id, pesquisador_nome or _UNKNOWN_INSTITUTION

    return "", _text(projeto.get("coordenador_nome")) or _UNKNOWN_INSTITUTION


def _scholarship_item_acronym(item: Mapping[str, object]) -> str:
    return _text(item.get("sigla")) or _scholarship_item_name(item)


def _scholarship_item_name(item: Mapping[str, object]) -> str:
    return _text(item.get("nome")) or _UNKNOWN_INSTITUTION


def _scholarship_item_quantity(item: Mapping[str, object]) -> int:
    if "orcamento_quantidade" in item:
        return _int_quantity(item.get("orcamento_quantidade"))
    if "cotas" in item:
        return _int_quantity(item.get("cotas"))
    return 1


def _scholarship_item_duration(item: Mapping[str, object]) -> int:
    duration = _int_quantity(item.get("orcamento_duracao") or "1")
    return duration if duration > 0 else 1


def _scholarship_item_unit_amount(
    item: Mapping[str, object],
    total_amount: Decimal,
    quantity: int,
    duration: int,
) -> Decimal:
    unit_amount = _decimal(item.get("orcamento_custo"))
    if unit_amount != Decimal("0"):
        return unit_amount

    divisor = quantity * duration
    if divisor <= 0:
        return total_amount

    return total_amount / Decimal(divisor)


def _scholarship_item_amount(item: Mapping[str, object]) -> Decimal:
    amount = _decimal(item.get("vlrtot"))
    if amount != Decimal("0"):
        return amount

    return (
        _decimal(item.get("orcamento_custo"))
        * Decimal(_scholarship_item_duration(item))
        * Decimal(_scholarship_item_quantity(item))
    )


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
