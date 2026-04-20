"""Generate institution totals from downloaded FAPES edital project files."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Final, Protocol, TypeAlias, cast

JsonObject: TypeAlias = dict[str, object]
ReportRow: TypeAlias = dict[str, object]

_PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
_SRC_DIR: Final = _PROJECT_ROOT / "src"
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if _SRC_DIR.exists() and str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

_DEFAULT_INPUT_DIR: Final = Path("downloads/projetos_por_edital")
_DEFAULT_OUTPUT: Final = Path("downloads/relatorio_instituicoes.csv")
_DEFAULT_ALLOCATION_MAX_WORKERS: Final = 4
_DEFAULT_ALLOCATION_RETRIES: Final = 2
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
_SCHOLARSHIP_ALLOCATION_FIELDS: Final = (
    "arquivo_origem",
    "projeto_id",
    "projeto_titulo",
    "situacao_descricao",
    "coordenador_nome",
    "instituicao_nome",
    "instituicao_sigla",
    "bolsista_pesquisador_id",
    "bolsista_pesquisador_nome",
    "formulario_bolsa_id",
    "formulario_bolsa_situacao",
    "formulario_bolsa_inicio",
    "formulario_bolsa_termino",
    "formulario_cancel_bolsa_data",
    "formulario_subst_bolsa_data",
    "bolsa_sigla",
    "bolsa_nome",
    "bolsa_nivel_id",
    "bolsa_nivel_nome",
    "bolsa_nivel_valor",
    "qtd_bolsas_paga",
    "valor_alocado_total",
    "pagamentos",
    "valor_pago_total",
)
_UNKNOWN_INSTITUTION = "Sem informacao"
_EXCLUDED_PROJECT_STATUS_LABELS: Final = (
    "Projeto Não Contratado",
    "Proposta não Contratada mas Aprovada no Mérito",
)
_EXCLUDED_PROJECT_STATUSES: Final = frozenset(
    label.casefold() for label in _EXCLUDED_PROJECT_STATUS_LABELS
)


class ScholarshipAllocationEnvelope(Protocol):
    """Envelope returned by the FAPES scholarship-holder endpoint."""

    data: Sequence[Mapping[str, object]]


class ScholarshipAllocationApi(Protocol):
    """Subset of the FAPES API required by allocation reports."""

    def listar_bolsistas(self, codprj: str | int) -> ScholarshipAllocationEnvelope:
        """List scholarship holders allocated to a project."""


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


@dataclass(frozen=True, slots=True)
class ScholarshipAllocationProject:
    index: int
    path: Path
    projeto: Mapping[str, object]
    codprj: str


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


def generate_scholarship_allocations_report(
    input_dir: str | Path = _DEFAULT_INPUT_DIR,
    *,
    api_client: ScholarshipAllocationApi,
    include_excluded_projects: bool = False,
    selected_statuses: Sequence[str] = (),
    max_workers: int = _DEFAULT_ALLOCATION_MAX_WORKERS,
    retry_attempts: int = _DEFAULT_ALLOCATION_RETRIES,
    limit: int | None = None,
) -> list[ReportRow]:
    """Fetch scholarship-holder allocations from FAPES for downloaded projects."""

    projects = _scholarship_allocation_projects(
        input_dir,
        include_excluded_projects=include_excluded_projects,
        selected_statuses=selected_statuses,
        limit=limit,
    )
    if not projects:
        return []

    rows_by_index: dict[int, list[ReportRow]] = {}
    worker_count = min(_positive_worker_count(max_workers), len(projects))
    with ThreadPoolExecutor(
        max_workers=worker_count,
        thread_name_prefix="fapes-bolsistas",
    ) as executor:
        futures = {
            executor.submit(
                _fetch_scholarship_allocations_for_project,
                project,
                api_client,
                retry_attempts,
            ): project.index
            for project in projects
        }
        for future in as_completed(futures):
            rows_by_index[futures[future]] = future.result()

    return [row for index in sorted(rows_by_index) for row in rows_by_index[index]]


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


def write_scholarship_allocations_report(
    rows: Sequence[Mapping[str, object]],
    output: str | Path,
) -> Path:
    """Write scholarship allocation rows as CSV or JSON."""

    return _write_rows(rows, output, _SCHOLARSHIP_ALLOCATION_FIELDS)


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


def run(
    argv: Sequence[str] | None = None,
    *,
    api_client_factory: Callable[[], ScholarshipAllocationApi] | None = None,
) -> int:
    args = _parse_args(argv)
    rows = generate_report(args.input_dir)
    output = write_report(rows, args.output)
    researcher_scholarships_output = None
    researcher_scholarships_summary_output = None
    scholarship_allocations_output = None
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

    if args.scholarship_allocations_output is not None:
        factory = (
            api_client_factory if api_client_factory is not None else _build_api_client
        )
        scholarship_allocation_rows = generate_scholarship_allocations_report(
            args.input_dir,
            api_client=factory(),
            max_workers=args.scholarship_allocation_max_workers,
            retry_attempts=args.scholarship_allocation_retries,
            limit=args.scholarship_allocation_limit,
        )
        scholarship_allocations_output = write_scholarship_allocations_report(
            scholarship_allocation_rows,
            args.scholarship_allocations_output,
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
    if scholarship_allocations_output is not None:
        print(f"Alocacao de bolsas gerada: {scholarship_allocations_output}")
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
    parser.add_argument(
        "--scholarship-allocations-output",
        type=Path,
        default=None,
        help=(
            "Arquivo CSV ou JSON para buscar na FAPES as alocacoes reais "
            "de bolsas por projeto via endpoint bolsistas."
        ),
    )
    parser.add_argument(
        "--scholarship-allocation-max-workers",
        type=_positive_int,
        default=_DEFAULT_ALLOCATION_MAX_WORKERS,
        help=(
            "Quantidade maxima de consultas simultaneas de bolsistas. "
            f"Padrao: {_DEFAULT_ALLOCATION_MAX_WORKERS}"
        ),
    )
    parser.add_argument(
        "--scholarship-allocation-retries",
        type=_non_negative_int,
        default=_DEFAULT_ALLOCATION_RETRIES,
        help=(
            "Tentativas extras para cada consulta de bolsistas que falhar. "
            f"Padrao: {_DEFAULT_ALLOCATION_RETRIES}"
        ),
    )
    parser.add_argument(
        "--scholarship-allocation-limit",
        type=_positive_int,
        default=None,
        help=(
            "Limita a quantidade de projetos consultados no endpoint bolsistas. "
            "Use para validacoes rapidas; omitido consulta todos."
        ),
    )
    return parser.parse_args(argv)


def _build_api_client() -> ScholarshipAllocationApi:
    from fapes_lib.controllers import (  # noqa: PLC0415
        FapesApiClient,
        FapesAuthenticator,
        FapesQueryController,
    )
    from fapes_lib.infrastructure.http_client import FapesHttpClient  # noqa: PLC0415
    from fapes_lib.settings import FapesSettings  # noqa: PLC0415
    from scripts.main import _secure_http_transport  # noqa: PLC0415

    settings = FapesSettings.from_env()
    http_client = FapesHttpClient(
        base_url=settings.base_url,
        timeout=settings.timeout_seconds,
        transport=_secure_http_transport(settings),
    )
    authenticator = FapesAuthenticator(settings=settings, http_client=http_client)
    token = authenticator.authenticate()
    query_controller = FapesQueryController(http_client=http_client, token=token.value)
    return cast(
        ScholarshipAllocationApi,
        FapesApiClient(query_controller=query_controller),
    )


def _positive_int(raw_value: str) -> int:
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("deve ser um numero inteiro positivo") from exc

    if value < 1:
        raise argparse.ArgumentTypeError("deve ser um numero inteiro positivo")

    return value


def _non_negative_int(raw_value: str) -> int:
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "deve ser um numero inteiro nao negativo"
        ) from exc

    if value < 0:
        raise argparse.ArgumentTypeError("deve ser um numero inteiro nao negativo")

    return value


def _scholarship_allocation_projects(
    input_dir: str | Path,
    *,
    include_excluded_projects: bool,
    selected_statuses: Sequence[str],
    limit: int | None,
) -> list[ScholarshipAllocationProject]:
    projects: list[ScholarshipAllocationProject] = []
    for path in sorted(Path(input_dir).glob("*.json")):
        for projeto in _projects_from_file(path):
            if _should_skip_project(
                projeto,
                include_excluded_projects,
                selected_statuses,
            ):
                continue
            codprj = _project_identifier(projeto)
            if codprj is None:
                continue
            projects.append(
                ScholarshipAllocationProject(
                    index=len(projects),
                    path=path,
                    projeto=projeto,
                    codprj=codprj,
                )
            )
            if limit is not None and len(projects) >= limit:
                return projects

    return projects


def _fetch_scholarship_allocations_for_project(
    project: ScholarshipAllocationProject,
    api_client: ScholarshipAllocationApi,
    retry_attempts: int,
) -> list[ReportRow]:
    allocations = _list_bolsistas_with_retries(
        api_client,
        project.codprj,
        retry_attempts=retry_attempts,
    )
    return [
        _scholarship_allocation_row(project.path, project.projeto, allocation)
        for allocation in allocations
    ]


def _list_bolsistas_with_retries(
    api_client: ScholarshipAllocationApi,
    codprj: str,
    *,
    retry_attempts: int,
) -> list[Mapping[str, object]]:
    retry_count = max(retry_attempts, 0)
    for attempt in range(retry_count + 1):
        try:
            return _records_from_allocation_envelope(
                api_client.listar_bolsistas(codprj)
            )
        except Exception:
            if attempt >= retry_count:
                raise

    raise AssertionError("unreachable retry loop")


def _records_from_allocation_envelope(
    envelope: ScholarshipAllocationEnvelope,
) -> list[Mapping[str, object]]:
    return [item for item in envelope.data if isinstance(item, Mapping)]


def _scholarship_allocation_row(
    path: Path,
    projeto: Mapping[str, object],
    allocation: Mapping[str, object],
) -> ReportRow:
    instituicao_nome, instituicao_sigla = _institution_for_project(projeto)
    payment_records = _envelope_records(allocation.get("folhas_pagamentos"))
    scholarship_level_amount = _decimal(allocation.get("bolsa_nivel_valor"))
    paid_quantity = _int_quantity(allocation.get("qtd_bolsas_paga"))
    paid_amount = sum(
        (
            _decimal(payment.get("folha_pagamento_pesquisador_valor"))
            for payment in payment_records
        ),
        Decimal("0"),
    )
    return {
        "arquivo_origem": path.name,
        "projeto_id": _text(projeto.get("projeto_id")),
        "projeto_titulo": _text(projeto.get("projeto_titulo")),
        "situacao_descricao": _text(projeto.get("situacao_descricao")),
        "coordenador_nome": _text(projeto.get("coordenador_nome")),
        "instituicao_nome": instituicao_nome,
        "instituicao_sigla": instituicao_sigla,
        "bolsista_pesquisador_id": _text(allocation.get("bolsista_pesquisador_id")),
        "bolsista_pesquisador_nome": _text(allocation.get("bolsista_pesquisador_nome"))
        or _UNKNOWN_INSTITUTION,
        "formulario_bolsa_id": _text(allocation.get("formulario_bolsa_id")),
        "formulario_bolsa_situacao": _text(allocation.get("formulario_bolsa_situacao")),
        "formulario_bolsa_inicio": _text(allocation.get("formulario_bolsa_inicio")),
        "formulario_bolsa_termino": _text(allocation.get("formulario_bolsa_termino")),
        "formulario_cancel_bolsa_data": _text(
            allocation.get("formulario_cancel_bolsa_data")
        ),
        "formulario_subst_bolsa_data": _text(
            allocation.get("formulario_subst_bolsa_data")
        ),
        "bolsa_sigla": _text(allocation.get("bolsa_sigla")),
        "bolsa_nome": _text(allocation.get("bolsa_nome")),
        "bolsa_nivel_id": _text(allocation.get("bolsa_nivel_id")),
        "bolsa_nivel_nome": _text(allocation.get("bolsa_nivel_nome")),
        "bolsa_nivel_valor": _money(scholarship_level_amount),
        "qtd_bolsas_paga": paid_quantity,
        "valor_alocado_total": _money(
            scholarship_level_amount * Decimal(paid_quantity)
        ),
        "pagamentos": len(payment_records),
        "valor_pago_total": _money(paid_amount),
    }


def _project_identifier(projeto: Mapping[str, object]) -> str | None:
    for field_name in ("projeto_id", "codprj"):
        value = _text(projeto.get(field_name))
        if value:
            return value

    return None


def _positive_worker_count(max_workers: int) -> int:
    return max(max_workers, 1)


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
