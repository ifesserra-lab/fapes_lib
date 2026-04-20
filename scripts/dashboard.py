"""Streamlit dashboard for downloaded FAPES edital project JSON files."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from importlib import import_module
from pathlib import Path
from typing import Any, Final, TypeAlias, cast
from unicodedata import combining, normalize

from scripts.budget_categories import load_budget_categories
from scripts.project_details import (
    build_project_timeline,
    load_project_details,
    load_researcher_project_details,
)
from scripts.report import (
    _is_not_contracted_status as _report_is_not_contracted_status,
)
from scripts.report import (
    excluded_project_status_labels,
    generate_excluded_projects_audit,
    generate_report,
    generate_researcher_scholarships_report,
    load_project_status_options,
    summarize_researcher_scholarships,
)
from scripts.scholarship_details import load_scholarship_details

ReportRow: TypeAlias = dict[str, object]

_DEFAULT_INPUT_DIR: Final = Path("downloads/projetos_por_edital")
_DEFAULT_SCHOLARSHIP_ALLOCATIONS_JSON_NAME: Final = "relatorio_alocacao_bolsas.json"
_DEFAULT_TOP_N: Final = 15
_BUDGET_CATEGORY_COLUMN = "categoria_orcamento"
_BUDGET_COLUMN = "orcamento_contratado"
_BUDGET_TOOLTIP_COLUMN = "orcamento_contratado_tooltip"
_BUDGET_VALUE_COLUMN = "orcamento_contratado_valor"
_CHART_LABEL_COLUMN = "valor_total"
_SCHOLARSHIPS_COLUMN = "quantidade_bolsas"
_SCHOLARSHIP_AMOUNT_COLUMN = "valor_bolsas"
_SCHOLARSHIP_AMOUNT_TOOLTIP_COLUMN = "valor_bolsas_tooltip"
_SCHOLARSHIP_AMOUNT_VALUE_COLUMN = "valor_bolsas_valor"
_SCHOLARSHIP_TYPE_COLUMN = "tipo_bolsa"
_PROJECTS_COLUMN = "total_projetos"
_FINANCIAL_VOLUME_TYPE_COLUMN = "tipo_volume_financeiro"
_FINANCIAL_VOLUME_VALUE_COLUMN = "valor_financeiro"
_RESEARCHER_SCHOLARSHIP_TOTAL_COLUMN = "valor_total_bolsas"
_SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN = "valor_alocado_total"
_SCHOLARSHIP_ALLOCATION_PAID_AMOUNT_COLUMN = "valor_pago_total"
_TABLE_MONEY_COLUMNS: Final = frozenset(
    {
        _BUDGET_COLUMN,
        _SCHOLARSHIP_AMOUNT_COLUMN,
        _RESEARCHER_SCHOLARSHIP_TOTAL_COLUMN,
        _SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN,
        _SCHOLARSHIP_ALLOCATION_PAID_AMOUNT_COLUMN,
        "Orcamento contratado",
        "Valor bolsas",
        "Valor contratado",
        "Valor alocado",
        "Valor pago",
        "Valor total",
        "Valor unitario",
        "Total financeiro",
        "Volume financeiro",
        "valor_total",
        "valor_unitario",
        "valor_total_bolsas",
    }
)
_UNKNOWN_INSTITUTION = "Sem informacao"
_NO_MATCH_INSTITUTION_LABEL = "__sem_instituicao__"
_TOOLTIP_FIELD_GROUPS: Final = (
    ((_CHART_LABEL_COLUMN,), "Total"),
    ((_PROJECTS_COLUMN,), "Projetos"),
    ((_SCHOLARSHIPS_COLUMN,), "Bolsas"),
    ((_SCHOLARSHIP_AMOUNT_TOOLTIP_COLUMN, _SCHOLARSHIP_AMOUNT_COLUMN), "Valor bolsas"),
    ((_BUDGET_TOOLTIP_COLUMN, _BUDGET_COLUMN), "Orcamento"),
)


@dataclass(frozen=True, slots=True)
class DashboardData:
    input_dir: Path
    file_count: int
    institution_rows: list[ReportRow]
    excluded_project_count: int
    excluded_project_rows: list[ReportRow]
    researcher_scholarship_rows: list[ReportRow]
    researcher_scholarship_summary_rows: list[ReportRow]
    scholarship_allocation_rows: list[ReportRow]
    total_institutions: int
    total_projects: int
    total_scholarships: int
    total_scholarship_amount: str
    total_budget: str


@dataclass(frozen=True, slots=True)
class DashboardTotals:
    total_institutions: int
    total_projects: int
    total_scholarships: int
    total_scholarship_amount: str
    total_budget: str


@dataclass(frozen=True, slots=True)
class ScholarshipAllocationTotals:
    total_holders: int
    total_projects: int
    total_institutions: int
    total_paid_scholarships: int
    total_allocated_amount: str
    total_paid_amount: str


def load_dashboard_data(
    input_dir: str | Path = _DEFAULT_INPUT_DIR,
    *,
    include_excluded_projects: bool = False,
    selected_statuses: Sequence[str] = (),
    scholarship_allocations_path: str | Path | None = None,
) -> DashboardData:
    """Load aggregated dashboard data from downloaded edital project JSON files."""

    path = Path(input_dir)
    rows = top_rows(
        generate_report(
            path,
            include_excluded_projects=include_excluded_projects,
            selected_statuses=selected_statuses,
        ),
        _BUDGET_COLUMN,
        limit=None,
    )
    excluded_project_rows = generate_excluded_projects_audit(
        path,
        selected_statuses=selected_statuses,
    )
    researcher_scholarship_rows = generate_researcher_scholarships_report(
        path,
        include_excluded_projects=include_excluded_projects,
        selected_statuses=selected_statuses,
    )
    researcher_scholarship_summary_rows = summarize_researcher_scholarships(
        researcher_scholarship_rows
    )
    scholarship_allocation_rows = load_scholarship_allocation_rows(
        path,
        allocation_path=scholarship_allocations_path,
        include_excluded_projects=include_excluded_projects,
        selected_statuses=selected_statuses,
    )
    totals = _summary_totals(rows)

    return DashboardData(
        input_dir=path,
        file_count=len(list(path.glob("*.json"))),
        institution_rows=rows,
        excluded_project_count=len(excluded_project_rows),
        excluded_project_rows=excluded_project_rows,
        researcher_scholarship_rows=researcher_scholarship_rows,
        researcher_scholarship_summary_rows=researcher_scholarship_summary_rows,
        scholarship_allocation_rows=scholarship_allocation_rows,
        total_institutions=totals.total_institutions,
        total_projects=totals.total_projects,
        total_scholarships=totals.total_scholarships,
        total_scholarship_amount=totals.total_scholarship_amount,
        total_budget=totals.total_budget,
    )


def load_scholarship_allocation_rows(
    input_dir: str | Path = _DEFAULT_INPUT_DIR,
    *,
    allocation_path: str | Path | None = None,
    include_excluded_projects: bool = False,
    selected_statuses: Sequence[str] = (),
) -> list[ReportRow]:
    """Load real scholarship-holder allocations exported by scripts/report.py."""

    path = (
        Path(allocation_path)
        if allocation_path is not None
        else _default_scholarship_allocations_path(input_dir)
    )
    if not path.exists():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(payload, list):
        return []

    rows: list[ReportRow] = []
    for item in payload:
        if not isinstance(item, Mapping):
            continue
        row = dict(item)
        if _should_skip_scholarship_allocation_row(
            row,
            include_excluded_projects=include_excluded_projects,
            selected_statuses=selected_statuses,
        ):
            continue
        rows.append(row)

    return rows


def filter_rows(rows: Sequence[Mapping[str, object]], query: str) -> list[ReportRow]:
    """Filter institution rows by name or acronym."""

    normalized_query = query.casefold().strip()
    if not normalized_query:
        return [dict(row) for row in rows]

    filtered: list[ReportRow] = []
    for row in rows:
        name = str(row.get("instituicao_nome", "")).casefold()
        acronym = str(row.get("instituicao_sigla", "")).casefold()
        if normalized_query in name or normalized_query in acronym:
            filtered.append(dict(row))

    return filtered


def institution_options(rows: Sequence[Mapping[str, object]]) -> list[str]:
    """Return institution name/acronym labels for list-based filtering."""

    labels = {_institution_label(row) for row in rows}
    return sorted(labels, key=str.casefold)


def filter_selected_institutions(
    rows: Sequence[Mapping[str, object]],
    selected_options: Sequence[str],
) -> list[ReportRow]:
    """Filter rows by selected institution name/acronym labels."""

    if not selected_options:
        return [dict(row) for row in rows]

    selected = set(selected_options)
    return [dict(row) for row in rows if _institution_label(row) in selected]


def top_rows(
    rows: Sequence[Mapping[str, object]],
    metric: str,
    limit: int | None,
) -> list[ReportRow]:
    """Return rows sorted by the selected numeric metric in descending order."""

    ordered = sorted(
        (dict(row) for row in rows),
        key=lambda row: _decimal(row.get(metric)),
        reverse=True,
    )
    if limit is None:
        return ordered

    return ordered[:limit]


def run_app() -> None:
    """Render the Streamlit application."""

    alt = cast(Any, import_module("altair"))
    pd = cast(Any, import_module("pandas"))
    st = cast(Any, import_module("streamlit"))

    st.set_page_config(
        page_title="FAPES - Projetos Por Instituicao",
        page_icon="chart_with_upwards_trend",
        layout="wide",
    )

    st.title("FAPES - Projetos Por Instituicao")
    st.caption("Dados carregados dos JSONs baixados por edital.")

    with st.sidebar:
        st.header("Navegacao")
        page_label = st.radio(
            "Pagina",
            options=(
                "Resumo",
                "Detalhes da instituicao",
                "Projetos por pesquisador",
                "Bolsistas alocados",
            ),
        )
        st.header("Dados")
        input_dir = Path(
            st.text_input(
                "Diretorio dos JSONs",
                value=str(_DEFAULT_INPUT_DIR),
            )
        )
        scholarship_allocations_path = Path(
            st.text_input(
                "JSON de bolsistas",
                value=str(_default_scholarship_allocations_path(input_dir)),
            )
        )
        show_chart_values = bool(
            st.toggle(
                "Mostrar valores nos graficos",
                value=True,
            )
        )
        project_scope_label = st.radio(
            "Base dos projetos",
            options=("Somente contratados", "Todos os projetos"),
        )

    include_excluded_projects = str(project_scope_label) == "Todos os projetos"
    with st.sidebar:
        selected_project_statuses = st.multiselect(
            "Status do projeto",
            options=load_project_status_options(
                input_dir,
                include_excluded_projects=include_excluded_projects,
            ),
            key="global_project_statuses",
        )

    data = load_dashboard_data(
        input_dir,
        include_excluded_projects=include_excluded_projects,
        selected_statuses=selected_project_statuses,
        scholarship_allocations_path=scholarship_allocations_path,
    )
    if not data.institution_rows:
        st.warning(f"Nenhum JSON encontrado em {data.input_dir}.")
        return

    if page_label == "Detalhes da instituicao":
        _render_institution_detail_page(
            st,
            pd,
            alt,
            data.input_dir,
            data.institution_rows,
            include_excluded_projects=include_excluded_projects,
            selected_statuses=selected_project_statuses,
            show_chart_values=show_chart_values,
        )
        return

    if page_label == "Projetos por pesquisador":
        _render_researcher_page(
            st,
            pd,
            alt,
            data.input_dir,
            include_excluded_projects=include_excluded_projects,
            selected_statuses=selected_project_statuses,
            show_chart_values=show_chart_values,
        )
        return

    if page_label == "Bolsistas alocados":
        _render_scholarship_allocations_page(
            st,
            pd,
            alt,
            data.scholarship_allocation_rows,
            scholarship_allocations_path,
            show_chart_values=show_chart_values,
        )
        return

    _render_summary_page(
        st,
        pd,
        alt,
        data,
        include_excluded_projects=include_excluded_projects,
        selected_statuses=selected_project_statuses,
        show_chart_values=show_chart_values,
    )


def _render_summary_page(
    st: Any,
    pd: Any,
    alt: Any,
    data: DashboardData,
    *,
    include_excluded_projects: bool,
    selected_statuses: Sequence[str],
    show_chart_values: bool,
) -> None:
    with st.sidebar:
        st.header("Filtros")
        include_unknown_institutions = bool(
            st.toggle(
                "Incluir Sem informacao",
                value=False,
                key="summary_include_unknown_institutions",
            )
        )
        institution_query = st.text_input("Buscar instituicao")
        top_n = st.slider("Top instituicoes", min_value=5, max_value=50, value=15)
        metric_label = st.selectbox(
            "Ordenar rankings por",
            options=(
                "Orcamento contratado",
                "Quantidade de bolsas",
                "Bolsas concedidas financeiro",
                "Total de projetos",
            ),
        )
        available_rows = _available_institution_rows(
            data.institution_rows,
            include_unknown_institutions,
            institution_query,
        )
        selected_institutions = st.multiselect(
            "Instituicao e sigla",
            options=institution_options(available_rows),
            placeholder="Selecione uma ou mais instituicoes",
        )

    metric = _metric_from_label(str(metric_label))
    filtered_rows = filter_selected_institutions(
        available_rows,
        selected_institutions,
    )
    ranking_rows = top_rows(filtered_rows, metric, top_n)
    summary_totals = _summary_totals(filtered_rows)
    budget_category_labels = _detail_filter_labels(
        filtered_rows,
        selected_institutions,
        include_unknown_institutions,
        bool(institution_query.strip()),
    )
    budget_category_rows = load_budget_categories(
        data.input_dir,
        budget_category_labels,
        include_excluded_projects=include_excluded_projects,
        selected_statuses=selected_statuses,
    )

    metric_columns = st.columns(7)
    metric_columns[0].metric("Arquivos JSON", data.file_count)
    metric_columns[1].metric("Instituicoes", summary_totals.total_institutions)
    metric_columns[2].metric("Projetos", summary_totals.total_projects)
    metric_columns[3].metric("Projetos excluidos", data.excluded_project_count)
    metric_columns[4].metric("Bolsas", summary_totals.total_scholarships)
    metric_columns[5].metric(
        "Valor bolsas",
        _currency_label(summary_totals.total_scholarship_amount),
    )
    metric_columns[6].metric("Orcamento", _currency_label(summary_totals.total_budget))

    budget_frame = _chart_dataframe(pd, ranking_rows, _BUDGET_COLUMN)
    table_frame = _display_dataframe(pd, filtered_rows)
    audit_frame = pd.DataFrame(data.excluded_project_rows)

    tab_overview, tab_table, tab_researchers, tab_audit = st.tabs(
        ["Visao geral", "Tabela", "Pesquisadores e bolsas", "Auditoria"]
    )
    with tab_overview:
        left, right = st.columns(2)
        with left:
            st.subheader("Orcamento contratado")
            _bar_chart_with_total_labels(
                st,
                alt,
                budget_frame,
                x="instituicao_sigla",
                y=_BUDGET_COLUMN,
                color="#28666E",
                show_values=show_chart_values,
            )

        with right:
            st.subheader("Bolsas concedidas")
            scholarship_rows = top_rows(filtered_rows, _SCHOLARSHIPS_COLUMN, top_n)
            _bar_chart_with_total_labels(
                st,
                alt,
                _chart_dataframe(pd, scholarship_rows, _SCHOLARSHIPS_COLUMN),
                x="instituicao_sigla",
                y=_SCHOLARSHIPS_COLUMN,
                color="#7C9885",
                show_values=show_chart_values,
            )

        st.subheader("Detalhamento do orcamento contratado")
        _bar_chart_with_total_labels(
            st,
            alt,
            _chart_dataframe(pd, budget_category_rows, _BUDGET_VALUE_COLUMN),
            x=_BUDGET_CATEGORY_COLUMN,
            y=_BUDGET_VALUE_COLUMN,
            color="#6A4C93",
            show_values=show_chart_values,
        )

        st.subheader("Bolsas concedidas financeiro")
        scholarship_amount_rows = top_rows(
            filtered_rows,
            _SCHOLARSHIP_AMOUNT_COLUMN,
            top_n,
        )
        _bar_chart_with_total_labels(
            st,
            alt,
            _chart_dataframe(pd, scholarship_amount_rows, _SCHOLARSHIP_AMOUNT_COLUMN),
            x="instituicao_sigla",
            y=_SCHOLARSHIP_AMOUNT_COLUMN,
            color="#8B5E34",
            show_values=show_chart_values,
        )

        st.subheader("Projetos por instituicao")
        project_rows = top_rows(filtered_rows, _PROJECTS_COLUMN, top_n)
        _bar_chart_with_total_labels(
            st,
            alt,
            _chart_dataframe(pd, project_rows, _PROJECTS_COLUMN),
            x="instituicao_sigla",
            y=_PROJECTS_COLUMN,
            color="#F2A541",
            show_values=show_chart_values,
        )

    with tab_table:
        _render_sortable_dataframe(st, table_frame)
        csv_payload = table_frame.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Baixar CSV",
            data=csv_payload,
            file_name="relatorio_instituicoes.csv",
            mime="text/csv",
        )

    with tab_researchers:
        scholarship_institution_options = _researcher_scholarship_institution_options(
            data.researcher_scholarship_rows
        )
        scholarship_type_options = _researcher_scholarship_type_options(
            data.researcher_scholarship_rows
        )
        max_scholarship_value = _researcher_scholarship_max_value(
            data.researcher_scholarship_rows
        )
        filter_columns = st.columns(4)
        with filter_columns[0]:
            selected_scholarship_institutions = st.multiselect(
                "Instituicao",
                options=scholarship_institution_options,
                key="researcher_scholarship_institutions",
            )
        with filter_columns[1]:
            selected_scholarship_types = st.multiselect(
                "Tipo de bolsa",
                options=scholarship_type_options,
                key="researcher_scholarship_types",
            )
        with filter_columns[2]:
            min_scholarship_value = float(
                st.number_input(
                    "Valor minimo",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    format="%.2f",
                    key="researcher_scholarship_min_value",
                )
            )
        with filter_columns[3]:
            max_scholarship_filter_value = float(
                st.number_input(
                    "Valor maximo",
                    min_value=0.0,
                    value=max_scholarship_value,
                    step=1000.0,
                    format="%.2f",
                    key="researcher_scholarship_max_value",
                )
            )
        researcher_top_n = st.slider(
            "Top pesquisadores",
            min_value=5,
            max_value=50,
            value=15,
            key="researcher_scholarship_top_n",
        )

        filtered_scholarship_rows = _filter_researcher_scholarship_rows(
            data.researcher_scholarship_rows,
            selected_institutions=selected_scholarship_institutions,
            selected_scholarship_types=selected_scholarship_types,
            min_value=min_scholarship_value,
            max_value=max_scholarship_filter_value,
        )
        filtered_summary_rows = summarize_researcher_scholarships(
            filtered_scholarship_rows
        )
        known_summary_rows = _known_researcher_summary_rows(filtered_summary_rows)
        unknown_summary_rows = _unknown_researcher_summary_rows(filtered_summary_rows)
        researcher_summary_frame = pd.DataFrame(known_summary_rows)
        researcher_scholarship_frame = pd.DataFrame(filtered_scholarship_rows)
        unknown_researcher_frame = pd.DataFrame(unknown_summary_rows)

        if researcher_summary_frame.empty:
            st.info("Nenhuma bolsa encontrada para os filtros selecionados.")
        else:
            st.subheader("Top pesquisadores por valor de bolsas")
            top_researcher_rows = _top_researcher_scholarship_summary_rows(
                known_summary_rows,
                researcher_top_n,
            )
            _bar_chart_with_total_labels(
                st,
                alt,
                _chart_dataframe(
                    pd,
                    top_researcher_rows,
                    _RESEARCHER_SCHOLARSHIP_TOTAL_COLUMN,
                ),
                x="pesquisador_nome",
                y=_RESEARCHER_SCHOLARSHIP_TOTAL_COLUMN,
                color="#28666E",
                show_values=show_chart_values,
            )

            st.subheader("Resumo por pesquisador")
            _render_sortable_dataframe(st, researcher_summary_frame)

        summary_csv_payload = researcher_summary_frame.to_csv(index=False).encode(
            "utf-8"
        )
        st.download_button(
            "Baixar resumo por pesquisador",
            data=summary_csv_payload,
            file_name="relatorio_pesquisadores_bolsas_resumo.csv",
            mime="text/csv",
        )
        scholarship_csv_payload = researcher_scholarship_frame.to_csv(
            index=False
        ).encode("utf-8")
        st.download_button(
            "Baixar pesquisadores e bolsas",
            data=scholarship_csv_payload,
            file_name="relatorio_pesquisadores_bolsas.csv",
            mime="text/csv",
        )
        if not unknown_researcher_frame.empty:
            st.subheader("Auditoria de pesquisadores sem informacao")
            _render_sortable_dataframe(st, unknown_researcher_frame)
            unknown_csv_payload = unknown_researcher_frame.to_csv(index=False).encode(
                "utf-8"
            )
            st.download_button(
                "Baixar pesquisadores sem informacao",
                data=unknown_csv_payload,
                file_name="pesquisadores_sem_informacao.csv",
                mime="text/csv",
            )

    with tab_audit:
        if audit_frame.empty:
            st.info("Nenhum projeto encontrado pela regra de exclusao.")
        else:
            _render_sortable_dataframe(st, audit_frame)
            audit_csv_payload = audit_frame.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Baixar projetos excluidos",
                data=audit_csv_payload,
                file_name="projetos_excluidos_auditoria.csv",
                mime="text/csv",
            )


def _render_institution_detail_page(
    st: Any,
    pd: Any,
    alt: Any,
    input_dir: Path,
    institution_rows: Sequence[Mapping[str, object]],
    *,
    include_excluded_projects: bool,
    selected_statuses: Sequence[str],
    show_chart_values: bool,
) -> None:
    with st.sidebar:
        include_unknown_institutions = bool(
            st.toggle(
                "Incluir Sem informacao",
                value=False,
                key="detail_include_unknown_institutions",
            )
        )
        institution_selection_rows = _available_institution_rows(
            institution_rows,
            include_unknown_institutions,
            "",
        )
        options = institution_options(institution_selection_rows)
        if not options:
            st.warning("Nenhuma instituicao encontrada para os filtros selecionados.")
            return
        institution_label = st.selectbox(
            "Instituicao e sigla",
            options=options,
        )

    project_rows = load_project_details(
        input_dir,
        str(institution_label),
        include_excluded_projects=include_excluded_projects,
        selected_statuses=selected_statuses,
    )

    st.header(str(institution_label))
    if not project_rows:
        st.warning("Nenhum projeto encontrado para a instituicao selecionada.")
        return

    with st.sidebar:
        st.header("Filtros dos projetos")
        project_query = st.text_input("Buscar projeto ou responsavel")
        selected_years = st.multiselect(
            "Ano",
            options=_project_year_options(project_rows),
        )
        show_only_active_projects = bool(
            st.toggle(
                "Mostrar apenas projetos ativos",
                value=False,
                key="show_only_active_projects",
            )
        )

    filtered_project_rows = _filter_project_rows(
        project_rows,
        query=project_query,
        selected_statuses=(),
        selected_years=selected_years,
        only_active=show_only_active_projects,
    )
    timeline_rows = build_project_timeline(filtered_project_rows)

    total_budget = sum(
        (_decimal(row.get(_BUDGET_COLUMN)) for row in filtered_project_rows),
        Decimal("0"),
    )
    total_scholarship_amount = sum(
        (
            _decimal(row.get(_SCHOLARSHIP_AMOUNT_COLUMN))
            for row in filtered_project_rows
        ),
        Decimal("0"),
    )
    metric_columns = st.columns(5)
    metric_columns[0].metric("Projetos", len(filtered_project_rows))
    metric_columns[1].metric(
        "Anos",
        len({row["ano"] for row in timeline_rows}),
    )
    metric_columns[2].metric(
        "Bolsas",
        sum(_int_value(row.get(_SCHOLARSHIPS_COLUMN)) for row in filtered_project_rows),
    )
    metric_columns[3].metric("Valor bolsas", _currency_label(total_scholarship_amount))
    metric_columns[4].metric("Orcamento", _currency_label(total_budget))

    if not filtered_project_rows:
        st.warning("Nenhum projeto encontrado para os filtros selecionados.")

    timeline_frame = pd.DataFrame(timeline_rows)
    budget_category_rows = load_budget_categories(
        input_dir,
        [str(institution_label)],
        include_excluded_projects=include_excluded_projects,
        selected_statuses=selected_statuses,
    )
    scholarship_detail_rows = load_scholarship_details(
        input_dir,
        [str(institution_label)],
        include_excluded_projects=include_excluded_projects,
        selected_statuses=selected_statuses,
    )

    (
        tab_budgets,
        tab_scholarships,
        tab_budget_details,
        tab_scholarship_details,
        tab_projects,
    ) = st.tabs(_institution_detail_tabs())
    with tab_budgets:
        if timeline_frame.empty:
            st.warning("Os projetos selecionados nao possuem data para agrupamento.")
        else:
            st.subheader("Orcamento por ano")
            _bar_chart_with_total_labels(
                st,
                alt,
                _chart_dataframe(pd, timeline_rows, _BUDGET_VALUE_COLUMN),
                x="ano",
                y=_BUDGET_VALUE_COLUMN,
                color="#F2A541",
                show_values=show_chart_values,
            )

            _render_sortable_dataframe(
                st,
                timeline_frame[["ano", _BUDGET_COLUMN, _BUDGET_VALUE_COLUMN]].drop(
                    columns=[_BUDGET_VALUE_COLUMN]
                ),
            )

    with tab_scholarships:
        if timeline_frame.empty:
            st.warning("Os projetos selecionados nao possuem data para agrupamento.")
        else:
            left, right = st.columns(2)
            with left:
                st.subheader("Bolsas por ano")
                _bar_chart_with_total_labels(
                    st,
                    alt,
                    _chart_dataframe(pd, timeline_rows, _SCHOLARSHIPS_COLUMN),
                    x="ano",
                    y=_SCHOLARSHIPS_COLUMN,
                    color="#7C9885",
                    show_values=show_chart_values,
                )
            with right:
                st.subheader("Bolsas concedidas financeiro por ano")
                _bar_chart_with_total_labels(
                    st,
                    alt,
                    _chart_dataframe(
                        pd,
                        timeline_rows,
                        _SCHOLARSHIP_AMOUNT_VALUE_COLUMN,
                    ),
                    x="ano",
                    y=_SCHOLARSHIP_AMOUNT_VALUE_COLUMN,
                    color="#8B5E34",
                    show_values=show_chart_values,
                )

            _render_sortable_dataframe(
                st,
                timeline_frame[
                    [
                        "ano",
                        _SCHOLARSHIPS_COLUMN,
                        _SCHOLARSHIP_AMOUNT_COLUMN,
                        _SCHOLARSHIP_AMOUNT_VALUE_COLUMN,
                    ]
                ].drop(columns=[_SCHOLARSHIP_AMOUNT_VALUE_COLUMN]),
            )

    with tab_budget_details:
        st.subheader("Detalhe de orcamentos")
        _bar_chart_with_total_labels(
            st,
            alt,
            _chart_dataframe(pd, budget_category_rows, _BUDGET_VALUE_COLUMN),
            x=_BUDGET_CATEGORY_COLUMN,
            y=_BUDGET_VALUE_COLUMN,
            color="#6A4C93",
            show_values=show_chart_values,
        )
        _render_sortable_dataframe(
            st,
            _drop_existing_columns(
                pd.DataFrame(budget_category_rows),
                [_BUDGET_VALUE_COLUMN],
            ),
        )

    with tab_scholarship_details:
        st.subheader("Detalhe de bolsas")
        if scholarship_detail_rows:
            left, right = st.columns(2)
            with left:
                st.subheader("Quantidade por tipo")
                _bar_chart_with_total_labels(
                    st,
                    alt,
                    _chart_dataframe(
                        pd,
                        scholarship_detail_rows,
                        _SCHOLARSHIPS_COLUMN,
                    ),
                    x=_SCHOLARSHIP_TYPE_COLUMN,
                    y=_SCHOLARSHIPS_COLUMN,
                    color="#7C9885",
                    show_values=show_chart_values,
                )
            with right:
                st.subheader("Valor por tipo")
                _bar_chart_with_total_labels(
                    st,
                    alt,
                    _chart_dataframe(
                        pd,
                        scholarship_detail_rows,
                        _SCHOLARSHIP_AMOUNT_VALUE_COLUMN,
                    ),
                    x=_SCHOLARSHIP_TYPE_COLUMN,
                    y=_SCHOLARSHIP_AMOUNT_VALUE_COLUMN,
                    color="#8B5E34",
                    show_values=show_chart_values,
                )
        else:
            st.info("Nenhuma bolsa encontrada para a instituicao selecionada.")

        scholarship_details_frame = pd.DataFrame(scholarship_detail_rows)
        if not scholarship_details_frame.empty:
            st.subheader("Tipos de bolsas contratadas")
            _render_sortable_dataframe(
                st,
                pd.DataFrame(_scholarship_detail_table_rows(scholarship_detail_rows)),
            )

    with tab_projects:
        st.caption(_excluded_project_status_note())
        responsible_volume_frame = pd.DataFrame(
            _responsible_financial_volume_rows(filtered_project_rows)
        )
        if not responsible_volume_frame.empty:
            st.subheader("Volume financeiro por responsavel")
            _render_sortable_dataframe(st, responsible_volume_frame)

        st.subheader("Projetos")
        project_detail_frame = pd.DataFrame(
            _project_detail_table_rows(filtered_project_rows)
        )
        _render_sortable_dataframe(st, project_detail_frame)
        csv_payload = project_detail_frame.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Baixar projetos",
            data=csv_payload,
            file_name="projetos_instituicao.csv",
            mime="text/csv",
        )


def _render_researcher_page(
    st: Any,
    pd: Any,
    alt: Any,
    input_dir: Path,
    *,
    include_excluded_projects: bool,
    selected_statuses: Sequence[str],
    show_chart_values: bool,
) -> None:
    with st.sidebar:
        st.header("Filtro do pesquisador")
        researcher_query = st.text_input("Nome do pesquisador")

    st.header("Projetos por pesquisador")
    if not researcher_query.strip():
        st.info("Digite parte do nome do pesquisador para carregar os projetos.")
        return

    project_rows = load_researcher_project_details(
        input_dir,
        researcher_query,
        include_excluded_projects=include_excluded_projects,
        selected_statuses=selected_statuses,
    )
    if not project_rows:
        st.warning("Nenhum projeto encontrado para o pesquisador informado.")
        return

    with st.sidebar:
        financial_chart_mode = st.radio(
            "Visual do grafico financeiro",
            options=("Barras agrupadas", "Barras empilhadas"),
            key="researcher_financial_chart_mode",
        )

    filtered_project_rows = _filter_researcher_project_rows(project_rows)
    if not filtered_project_rows:
        st.warning("Nenhum projeto encontrado para os status selecionados.")
        return

    timeline_rows = build_project_timeline(filtered_project_rows)
    total_budget = sum(
        (_decimal(row.get(_BUDGET_COLUMN)) for row in filtered_project_rows),
        Decimal("0"),
    )
    total_scholarship_amount = sum(
        (
            _decimal(row.get(_SCHOLARSHIP_AMOUNT_COLUMN))
            for row in filtered_project_rows
        ),
        Decimal("0"),
    )

    metric_columns = st.columns(5)
    metric_columns[0].metric("Projetos", len(filtered_project_rows))
    metric_columns[1].metric(
        "Instituicoes", len(_researcher_institutions(filtered_project_rows))
    )
    metric_columns[2].metric(
        "Bolsas",
        sum(_int_value(row.get(_SCHOLARSHIPS_COLUMN)) for row in filtered_project_rows),
    )
    metric_columns[3].metric("Valor bolsas", _currency_label(total_scholarship_amount))
    metric_columns[4].metric("Orcamento", _currency_label(total_budget))

    researcher_name_frame = pd.DataFrame(_researcher_name_rows(filtered_project_rows))
    if not researcher_name_frame.empty:
        st.subheader("Pesquisadores encontrados")
        _render_sortable_dataframe(st, researcher_name_frame)

    timeline_frame = pd.DataFrame(timeline_rows)
    if not timeline_frame.empty:
        financial_timeline_frame = pd.DataFrame(
            _researcher_financial_timeline_rows(timeline_rows)
        )
        financial_timeline_table_frame = pd.DataFrame(
            _researcher_financial_timeline_table_rows(timeline_rows)
        )
        left, right = st.columns(2)
        with left:
            st.subheader("Projetos por ano")
            _bar_chart_with_total_labels(
                st,
                alt,
                _chart_dataframe(pd, timeline_rows, _PROJECTS_COLUMN),
                x="ano",
                y=_PROJECTS_COLUMN,
                color="#28666E",
                show_values=show_chart_values,
            )
        with right:
            st.subheader("Volume financeiro por ano")
            _grouped_bar_chart_with_total_labels(
                st,
                alt,
                financial_timeline_frame,
                x="ano",
                y=_FINANCIAL_VOLUME_VALUE_COLUMN,
                color=_FINANCIAL_VOLUME_TYPE_COLUMN,
                color_domain=("Orcamento contratado", "Valor bolsas"),
                color_range=("#F2A541", "#8B5E34"),
                stack=_financial_chart_stack_from_mode(str(financial_chart_mode)),
                show_values=show_chart_values,
            )
            _render_sortable_dataframe(st, financial_timeline_table_frame)

    st.subheader("Projetos")
    project_frame = pd.DataFrame(_researcher_project_table_rows(filtered_project_rows))
    _render_sortable_dataframe(st, project_frame)
    csv_payload = project_frame.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Baixar projetos do pesquisador",
        data=csv_payload,
        file_name="projetos_pesquisador.csv",
        mime="text/csv",
    )


def _render_scholarship_allocations_page(
    st: Any,
    pd: Any,
    alt: Any,
    rows: Sequence[Mapping[str, object]],
    allocation_path: Path,
    *,
    show_chart_values: bool,
) -> None:
    st.header("Bolsistas alocados")
    st.caption(f"Dados carregados de {allocation_path}.")
    if not rows:
        st.info("Gere o arquivo relatorio_alocacao_bolsas.json para ver os bolsistas.")
        return

    with st.sidebar:
        st.header("Filtros dos bolsistas")
        allocation_query = st.text_input("Buscar bolsista, projeto ou responsavel")
        allocation_institution_query = st.text_input("Buscar instituicao")
        selected_institutions = st.multiselect(
            "Instituicao",
            options=_scholarship_allocation_institution_options(rows),
            key="scholarship_allocation_institutions",
        )
        selected_scholarship_types = st.multiselect(
            "Tipo de bolsa",
            options=_scholarship_allocation_type_options(rows),
            key="scholarship_allocation_types",
        )
        top_n = st.slider(
            "Top bolsistas",
            min_value=5,
            max_value=50,
            value=15,
            key="scholarship_allocation_top_n",
        )

    filtered_rows = _filter_scholarship_allocation_rows(
        rows,
        selected_institutions=selected_institutions,
        selected_scholarship_types=selected_scholarship_types,
        query=allocation_query,
        institution_query=allocation_institution_query,
    )
    totals = _scholarship_allocation_totals(filtered_rows)

    metric_columns = st.columns(6)
    metric_columns[0].metric("Bolsistas", totals.total_holders)
    metric_columns[1].metric("Projetos", totals.total_projects)
    metric_columns[2].metric("Instituicoes", totals.total_institutions)
    metric_columns[3].metric("Bolsas pagas", totals.total_paid_scholarships)
    metric_columns[4].metric(
        "Valor alocado",
        _currency_label(totals.total_allocated_amount),
    )
    metric_columns[5].metric("Valor pago", _currency_label(totals.total_paid_amount))

    if not filtered_rows:
        st.warning("Nenhum bolsista encontrado para os filtros selecionados.")
        return

    summary_rows = _scholarship_allocation_holder_summary_rows(filtered_rows)
    table_rows = _scholarship_allocation_table_rows(filtered_rows)
    summary_frame = pd.DataFrame(
        _scholarship_allocation_summary_table_rows(summary_rows)
    )
    table_frame = pd.DataFrame(table_rows)
    tab_summary, tab_table = st.tabs(["Resumo", "Tabela"])

    with tab_summary:
        st.subheader("Top bolsistas por valor alocado")
        _bar_chart_with_total_labels(
            st,
            alt,
            _chart_dataframe(
                pd,
                _top_scholarship_allocation_holder_rows(
                    summary_rows,
                    top_n,
                ),
                _SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN,
            ),
            x="bolsista",
            y=_SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN,
            color="#28666E",
            show_values=show_chart_values,
        )
        _render_sortable_dataframe(st, summary_frame)

    with tab_table:
        _render_sortable_dataframe(st, table_frame)
        csv_payload = table_frame.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Baixar CSV de bolsistas",
            data=csv_payload,
            file_name="relatorio_alocacao_bolsas.csv",
            mime="text/csv",
        )
        st.download_button(
            "Baixar JSON de bolsistas",
            data=_json_payload(filtered_rows),
            file_name="relatorio_alocacao_bolsas.json",
            mime="application/json",
        )


def _institution_detail_tabs() -> list[str]:
    return [
        "Orcamentos",
        "Bolsas",
        "Detalhe de orcamentos",
        "Detalhe de bolsas",
        "Projetos",
    ]


def _drop_existing_columns(dataframe: Any, columns: Sequence[str]) -> Any:
    existing_columns = [column for column in columns if column in dataframe]
    if not existing_columns:
        return dataframe

    return dataframe.drop(columns=existing_columns)


def _available_institution_rows(
    rows: Sequence[Mapping[str, object]],
    include_unknown: bool,
    query: str,
) -> list[ReportRow]:
    available_rows = (
        [dict(row) for row in rows]
        if include_unknown
        else _known_institution_rows(rows)
    )
    return filter_rows(available_rows, query)


def _known_institution_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[ReportRow]:
    return [dict(row) for row in rows if not _is_unknown_institution(row)]


def _is_unknown_institution(row: Mapping[str, object]) -> bool:
    return (
        str(row.get("instituicao_nome", "")).strip() == _UNKNOWN_INSTITUTION
        and str(row.get("instituicao_sigla", "")).strip() == _UNKNOWN_INSTITUTION
    )


def _detail_filter_labels(
    filtered_rows: Sequence[Mapping[str, object]],
    selected_options: Sequence[str],
    include_unknown: bool,
    query_applied: bool,
) -> list[str]:
    if selected_options:
        return list(selected_options)
    if include_unknown and not query_applied:
        return []
    labels = institution_options(filtered_rows)
    return labels if labels else [_NO_MATCH_INSTITUTION_LABEL]


def _project_detail_table_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[ReportRow]:
    return [
        {
            "Projeto ID": row.get("projeto_id", ""),
            "Projeto": row.get("projeto_titulo", ""),
            "Responsavel": row.get("coordenador_nome", ""),
            "Inicio previsto": row.get("projeto_data_inicio_previsto", ""),
            "Conclusao prevista": row.get("projeto_data_fim_previsto", ""),
            "Situacao": row.get("situacao_descricao", ""),
            "Bolsas": _int_value(row.get(_SCHOLARSHIPS_COLUMN)),
            "Valor bolsas": _currency_label(row.get(_SCHOLARSHIP_AMOUNT_COLUMN)),
            "Orcamento contratado": _currency_label(row.get(_BUDGET_COLUMN)),
        }
        for row in rows
    ]


def _researcher_project_table_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[ReportRow]:
    table_rows: list[ReportRow] = []
    for row in rows:
        table_row = _project_detail_table_rows([row])[0]
        table_row = {
            "Projeto ID": table_row["Projeto ID"],
            "Projeto": table_row["Projeto"],
            "Responsavel": table_row["Responsavel"],
            "Instituicao": row.get("instituicao_nome", ""),
            "Sigla": row.get("instituicao_sigla", ""),
            "Inicio previsto": table_row["Inicio previsto"],
            "Conclusao prevista": table_row["Conclusao prevista"],
            "Situacao": table_row["Situacao"],
            "Bolsas": table_row["Bolsas"],
            "Valor bolsas": table_row["Valor bolsas"],
            "Orcamento contratado": table_row["Orcamento contratado"],
        }
        table_rows.append(table_row)

    return table_rows


def _researcher_institutions(rows: Sequence[Mapping[str, object]]) -> set[str]:
    return {
        str(row.get("instituicao") or row.get("instituicao_nome") or "").strip()
        for row in rows
        if str(row.get("instituicao") or row.get("instituicao_nome") or "").strip()
    }


def _researcher_name_rows(rows: Sequence[Mapping[str, object]]) -> list[ReportRow]:
    totals: dict[str, dict[str, object]] = {}
    for row in rows:
        researcher = str(row.get("coordenador_nome") or _UNKNOWN_INSTITUTION).strip()
        if not researcher:
            researcher = _UNKNOWN_INSTITUTION
        if researcher not in totals:
            totals[researcher] = {
                "pesquisador": researcher,
                "projetos": 0,
                "instituicoes": set(),
            }

        total = totals[researcher]
        total["projetos"] = _int_value(total["projetos"]) + 1
        institution = str(
            row.get("instituicao") or row.get("instituicao_nome") or ""
        ).strip()
        if institution:
            cast(set[str], total["instituicoes"]).add(institution)

    ordered_totals = sorted(
        totals.values(),
        key=lambda total: (
            -_int_value(total["projetos"]),
            str(total["pesquisador"]).casefold(),
        ),
    )
    return [
        {
            "Pesquisador": total["pesquisador"],
            "Projetos": _int_value(total["projetos"]),
            "Instituicoes": len(cast(set[str], total["instituicoes"])),
        }
        for total in ordered_totals
    ]


def _researcher_scholarship_institution_options(
    rows: Sequence[Mapping[str, object]],
) -> list[str]:
    labels = {_institution_label(row) for row in rows}
    return sorted((label for label in labels if label), key=str.casefold)


def _researcher_scholarship_type_options(
    rows: Sequence[Mapping[str, object]],
) -> list[str]:
    labels = {_researcher_scholarship_type_label(row) for row in rows}
    return sorted((label for label in labels if label), key=str.casefold)


def _filter_researcher_scholarship_rows(
    rows: Sequence[Mapping[str, object]],
    *,
    selected_institutions: Sequence[str] = (),
    selected_scholarship_types: Sequence[str] = (),
    min_value: float | None = None,
    max_value: float | None = None,
) -> list[ReportRow]:
    selected_institution_set = set(selected_institutions)
    selected_type_set = set(selected_scholarship_types)
    minimum = _decimal(min_value) if min_value is not None else None
    maximum = _decimal(max_value) if max_value is not None else None
    filtered_rows: list[ReportRow] = []
    for row in rows:
        if (
            selected_institution_set
            and _institution_label(row) not in selected_institution_set
        ):
            continue
        if (
            selected_type_set
            and _researcher_scholarship_type_label(row) not in selected_type_set
        ):
            continue
        value = _decimal(row.get("valor_total"))
        if minimum is not None and value < minimum:
            continue
        if maximum is not None and value > maximum:
            continue
        filtered_rows.append(dict(row))

    return filtered_rows


def _known_researcher_summary_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[ReportRow]:
    return [dict(row) for row in rows if not _is_unknown_researcher(row)]


def _unknown_researcher_summary_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[ReportRow]:
    return [dict(row) for row in rows if _is_unknown_researcher(row)]


def _top_researcher_scholarship_summary_rows(
    rows: Sequence[Mapping[str, object]],
    limit: int,
) -> list[ReportRow]:
    return sorted(
        (dict(row) for row in rows),
        key=lambda row: (
            -_decimal(row.get(_RESEARCHER_SCHOLARSHIP_TOTAL_COLUMN)),
            str(row.get("pesquisador_nome", "")).casefold(),
        ),
    )[:limit]


def _researcher_scholarship_max_value(
    rows: Sequence[Mapping[str, object]],
) -> float:
    return float(
        max(
            (_decimal(row.get("valor_total")) for row in rows),
            default=Decimal("0"),
        )
    )


def _researcher_scholarship_type_label(row: Mapping[str, object]) -> str:
    acronym = str(row.get("bolsa_sigla", "")).strip()
    name = str(row.get("bolsa_nome", "")).strip()
    if acronym and name and acronym != name:
        return f"{acronym} | {name}"
    return acronym or name


def _default_scholarship_allocations_path(input_dir: str | Path) -> Path:
    return Path(input_dir).parent / _DEFAULT_SCHOLARSHIP_ALLOCATIONS_JSON_NAME


def _should_skip_scholarship_allocation_row(
    row: Mapping[str, object],
    *,
    include_excluded_projects: bool,
    selected_statuses: Sequence[str],
) -> bool:
    if not include_excluded_projects and _is_not_contracted_project_status(
        row.get("situacao_descricao")
    ):
        return True

    statuses = {status.strip() for status in selected_statuses if status.strip()}
    return bool(statuses) and str(row.get("situacao_descricao", "")).strip() not in (
        statuses
    )


def _scholarship_allocation_institution_options(
    rows: Sequence[Mapping[str, object]],
) -> list[str]:
    labels = {_institution_label(row) for row in rows}
    return sorted((label for label in labels if label), key=str.casefold)


def _scholarship_allocation_type_options(
    rows: Sequence[Mapping[str, object]],
) -> list[str]:
    labels = {_scholarship_allocation_type_label(row) for row in rows}
    return sorted((label for label in labels if label), key=str.casefold)


def _filter_scholarship_allocation_rows(
    rows: Sequence[Mapping[str, object]],
    *,
    selected_institutions: Sequence[str] = (),
    selected_scholarship_types: Sequence[str] = (),
    query: str = "",
    institution_query: str = "",
) -> list[ReportRow]:
    selected_institution_set = set(selected_institutions)
    selected_type_set = set(selected_scholarship_types)
    filtered_rows: list[ReportRow] = []
    for row in rows:
        if (
            selected_institution_set
            and _institution_label(row) not in selected_institution_set
        ):
            continue
        if institution_query and not _scholarship_allocation_matches_institution_query(
            row,
            institution_query,
        ):
            continue
        if (
            selected_type_set
            and _scholarship_allocation_type_label(row) not in selected_type_set
        ):
            continue
        if query and not _scholarship_allocation_matches_query(row, query):
            continue
        filtered_rows.append(dict(row))

    return filtered_rows


def _scholarship_allocation_totals(
    rows: Sequence[Mapping[str, object]],
) -> ScholarshipAllocationTotals:
    holder_keys = {_scholarship_allocation_holder_key(row) for row in rows}
    project_keys = {
        str(row.get("projeto_id") or "").strip()
        for row in rows
        if str(row.get("projeto_id") or "").strip()
    }
    institution_labels = {_institution_label(row) for row in rows}
    allocated_amount = sum(
        (
            _decimal(row.get(_SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN))
            for row in rows
        ),
        Decimal("0"),
    )
    paid_amount = sum(
        (_decimal(row.get(_SCHOLARSHIP_ALLOCATION_PAID_AMOUNT_COLUMN)) for row in rows),
        Decimal("0"),
    )

    return ScholarshipAllocationTotals(
        total_holders=len({key for key in holder_keys if key}),
        total_projects=len(project_keys),
        total_institutions=len({label for label in institution_labels if label}),
        total_paid_scholarships=sum(
            _int_value(row.get("qtd_bolsas_paga")) for row in rows
        ),
        total_allocated_amount=_money(allocated_amount),
        total_paid_amount=_money(paid_amount),
    )


def _scholarship_allocation_table_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[ReportRow]:
    return [
        {
            "Bolsista": row.get("bolsista_pesquisador_nome", ""),
            "Projeto ID": row.get("projeto_id", ""),
            "Projeto": row.get("projeto_titulo", ""),
            "Responsavel": row.get("coordenador_nome", ""),
            "Instituicao": row.get("instituicao_nome", ""),
            "Sigla": row.get("instituicao_sigla", ""),
            "Tipo bolsa": _scholarship_allocation_type_label(row),
            "Nivel": row.get("bolsa_nivel_nome", ""),
            "Inicio": row.get("formulario_bolsa_inicio", ""),
            "Termino": row.get("formulario_bolsa_termino", ""),
            "Situacao": row.get("situacao_descricao", ""),
            "Bolsas pagas": _int_value(row.get("qtd_bolsas_paga")),
            "Valor alocado": _currency_label(
                row.get(_SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN)
            ),
            "Pagamentos": _int_value(row.get("pagamentos")),
            "Valor pago": _currency_label(
                row.get(_SCHOLARSHIP_ALLOCATION_PAID_AMOUNT_COLUMN)
            ),
        }
        for row in rows
    ]


def _scholarship_allocation_holder_summary_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[ReportRow]:
    totals: dict[str, dict[str, object]] = {}
    for row in rows:
        holder_key = _scholarship_allocation_holder_key(row)
        holder_name = str(
            row.get("bolsista_pesquisador_nome") or _UNKNOWN_INSTITUTION
        ).strip()
        if not holder_name:
            holder_name = _UNKNOWN_INSTITUTION
        if holder_key not in totals:
            totals[holder_key] = {
                "bolsista": holder_name,
                "projetos": set(),
                "projetos_nomes": set(),
                "instituicoes": set(),
                "bolsas_pagas": 0,
                _SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN: Decimal("0"),
                _SCHOLARSHIP_ALLOCATION_PAID_AMOUNT_COLUMN: Decimal("0"),
            }

        total = totals[holder_key]
        project_id = str(row.get("projeto_id") or "").strip()
        if project_id:
            cast(set[str], total["projetos"]).add(project_id)
        project_label = _scholarship_allocation_project_label(row)
        if project_label:
            cast(set[str], total["projetos_nomes"]).add(project_label)
        institution = _institution_label(row)
        if institution:
            cast(set[str], total["instituicoes"]).add(institution)
        total["bolsas_pagas"] = _int_value(total["bolsas_pagas"]) + _int_value(
            row.get("qtd_bolsas_paga")
        )
        total[_SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN] = _decimal(
            total[_SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN]
        ) + _decimal(row.get(_SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN))
        total[_SCHOLARSHIP_ALLOCATION_PAID_AMOUNT_COLUMN] = _decimal(
            total[_SCHOLARSHIP_ALLOCATION_PAID_AMOUNT_COLUMN]
        ) + _decimal(row.get(_SCHOLARSHIP_ALLOCATION_PAID_AMOUNT_COLUMN))

    ordered_totals = sorted(
        totals.values(),
        key=lambda total: (
            -_decimal(total[_SCHOLARSHIP_ALLOCATION_PAID_AMOUNT_COLUMN]),
            str(total["bolsista"]).casefold(),
        ),
    )
    return [
        {
            "bolsista": total["bolsista"],
            "projetos": len(cast(set[str], total["projetos"])),
            "projetos_nomes": _join_labels(cast(set[str], total["projetos_nomes"])),
            "instituicoes": len(cast(set[str], total["instituicoes"])),
            "instituicoes_nomes": _join_labels(cast(set[str], total["instituicoes"])),
            "bolsas_pagas": _int_value(total["bolsas_pagas"]),
            _SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN: _money(
                _decimal(total[_SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN])
            ),
            _SCHOLARSHIP_ALLOCATION_PAID_AMOUNT_COLUMN: _money(
                _decimal(total[_SCHOLARSHIP_ALLOCATION_PAID_AMOUNT_COLUMN])
            ),
        }
        for total in ordered_totals
    ]


def _scholarship_allocation_summary_table_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[ReportRow]:
    return [
        {
            "Bolsista": row.get("bolsista", ""),
            "Projetos": _int_value(row.get("projetos")),
            "Nomes dos projetos": row.get("projetos_nomes", ""),
            "Instituicoes": _int_value(row.get("instituicoes")),
            "Instituicoes vinculadas": row.get("instituicoes_nomes", ""),
            "Bolsas pagas": _int_value(row.get("bolsas_pagas")),
            "Valor alocado": _currency_label(
                row.get(_SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN)
            ),
            "Valor pago": _currency_label(
                row.get(_SCHOLARSHIP_ALLOCATION_PAID_AMOUNT_COLUMN)
            ),
        }
        for row in rows
    ]


def _top_scholarship_allocation_holder_rows(
    rows: Sequence[Mapping[str, object]],
    limit: int,
) -> list[ReportRow]:
    return top_rows(rows, _SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN, limit)


def _scholarship_allocation_matches_query(
    row: Mapping[str, object],
    query: str,
) -> bool:
    normalized_query = query.casefold().strip()
    if not normalized_query:
        return True

    searchable_values = (
        row.get("bolsista_pesquisador_nome"),
        row.get("projeto_id"),
        row.get("projeto_titulo"),
        row.get("coordenador_nome"),
        row.get("instituicao_nome"),
        row.get("instituicao_sigla"),
        row.get("situacao_descricao"),
    )
    return any(
        normalized_query in str(value or "").casefold() for value in searchable_values
    )


def _scholarship_allocation_matches_institution_query(
    row: Mapping[str, object],
    query: str,
) -> bool:
    normalized_query = _normalized_search_text(query)
    if not normalized_query:
        return True

    searchable_values = (
        row.get("instituicao_nome"),
        row.get("instituicao_sigla"),
        _institution_label(row),
    )
    return any(
        normalized_query in _normalized_search_text(value)
        for value in searchable_values
    )


def _scholarship_allocation_type_label(row: Mapping[str, object]) -> str:
    acronym = str(row.get("bolsa_sigla", "")).strip()
    name = str(row.get("bolsa_nome", "")).strip()
    if acronym and name and acronym != name:
        return f"{acronym} | {name}"
    return acronym or name


def _scholarship_allocation_holder_key(row: Mapping[str, object]) -> str:
    holder_id = str(row.get("bolsista_pesquisador_id") or "").strip()
    holder_name = str(row.get("bolsista_pesquisador_nome") or "").strip()
    return holder_id or holder_name


def _scholarship_allocation_project_label(row: Mapping[str, object]) -> str:
    title = str(row.get("projeto_titulo") or "").strip()
    project_id = str(row.get("projeto_id") or "").strip()
    return title or project_id


def _join_labels(labels: set[str]) -> str:
    return "; ".join(sorted((label for label in labels if label), key=str.casefold))


def _normalized_search_text(value: object) -> str:
    decomposed = normalize("NFKD", str(value or ""))
    without_accents = "".join(
        character for character in decomposed if not combining(character)
    )
    searchable = "".join(
        character if character.isalnum() else " " for character in without_accents
    )
    return " ".join(searchable.casefold().split())


def _json_payload(rows: Sequence[Mapping[str, object]]) -> bytes:
    return f"{json.dumps(list(rows), ensure_ascii=False, indent=2)}\n".encode()


def _is_unknown_researcher(row: Mapping[str, object]) -> bool:
    researcher_name = str(row.get("pesquisador_nome", "")).strip()
    if not researcher_name:
        return True

    return researcher_name == _UNKNOWN_INSTITUTION


def _filter_researcher_project_rows(
    rows: Sequence[Mapping[str, object]],
    *,
    selected_statuses: Sequence[str] = (),
) -> list[ReportRow]:
    if not selected_statuses:
        return [dict(row) for row in rows]

    statuses = set(selected_statuses)
    return [
        dict(row) for row in rows if str(row.get("situacao_descricao", "")) in statuses
    ]


def _responsible_financial_volume_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[ReportRow]:
    totals: dict[str, dict[str, object]] = {}
    for row in rows:
        if _is_not_contracted_project_status(row.get("situacao_descricao")):
            continue
        responsible = str(row.get("coordenador_nome") or _UNKNOWN_INSTITUTION).strip()
        if not responsible:
            responsible = _UNKNOWN_INSTITUTION
        if responsible not in totals:
            totals[responsible] = {
                "responsavel": responsible,
                "projetos": 0,
                "bolsas": 0,
                "valor_bolsas": Decimal("0"),
                "volume_financeiro": Decimal("0"),
            }

        total = totals[responsible]
        total["projetos"] = _int_value(total["projetos"]) + 1
        total["bolsas"] = _int_value(total["bolsas"]) + _int_value(
            row.get(_SCHOLARSHIPS_COLUMN)
        )
        total["valor_bolsas"] = _decimal(total["valor_bolsas"]) + _decimal(
            row.get(_SCHOLARSHIP_AMOUNT_COLUMN)
        )
        total["volume_financeiro"] = _decimal(total["volume_financeiro"]) + _decimal(
            row.get(_BUDGET_COLUMN)
        )

    ordered_totals = sorted(
        totals.values(),
        key=lambda total: (
            -_decimal(total["volume_financeiro"]),
            str(total["responsavel"]).casefold(),
        ),
    )
    return [
        {
            "Responsavel": total["responsavel"],
            "Projetos": _int_value(total["projetos"]),
            "Bolsas": _int_value(total["bolsas"]),
            "Valor bolsas": _currency_label(total["valor_bolsas"]),
            "Volume financeiro": _currency_label(total["volume_financeiro"]),
        }
        for total in ordered_totals
    ]


def _is_not_contracted_project_status(value: object) -> bool:
    return _report_is_not_contracted_status(value)


def _excluded_project_status_note() -> str:
    labels = "; ".join(excluded_project_status_labels())
    return (
        "Projetos com situacao "
        f"{labels} foram excluidos das contas, graficos e do volume financeiro."
    )


def _scholarship_detail_table_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[ReportRow]:
    return [
        {
            "Tipo de bolsa": row.get(_SCHOLARSHIP_TYPE_COLUMN, ""),
            "Nome da bolsa": row.get("nome_bolsa", ""),
            "Quantidade": _int_value(row.get(_SCHOLARSHIPS_COLUMN)),
            "Valor contratado": _currency_label(row.get(_SCHOLARSHIP_AMOUNT_COLUMN)),
            "Lancamentos": _int_value(row.get("total_lancamentos")),
        }
        for row in rows
    ]


def _active_project_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[ReportRow]:
    return [
        dict(row)
        for row in rows
        if _is_active_project_status(row.get("situacao_descricao"))
    ]


def _is_active_project_status(value: object) -> bool:
    return "em andamento" in str(value or "").casefold()


def _filter_project_rows(
    rows: Sequence[Mapping[str, object]],
    *,
    query: str,
    selected_statuses: Sequence[str],
    selected_years: Sequence[int],
    only_active: bool,
) -> list[ReportRow]:
    statuses = set(selected_statuses)
    years = set(selected_years)
    filtered_rows: list[ReportRow] = []
    for row in rows:
        if only_active and not _is_active_project_status(row.get("situacao_descricao")):
            continue
        if statuses and str(row.get("situacao_descricao", "")) not in statuses:
            continue
        if years and row.get("ano") not in years:
            continue
        if query and not _project_matches_query(row, query):
            continue
        filtered_rows.append(dict(row))

    return filtered_rows


def _project_matches_query(row: Mapping[str, object], query: str) -> bool:
    normalized_query = query.casefold().strip()
    if not normalized_query:
        return True

    searchable_values = (
        row.get("projeto_id"),
        row.get("projeto_titulo"),
        row.get("coordenador_nome"),
        row.get("situacao_descricao"),
    )
    return any(
        normalized_query in str(value or "").casefold() for value in searchable_values
    )


def _project_year_options(rows: Sequence[Mapping[str, object]]) -> list[int]:
    years = set()
    for row in rows:
        year = row.get("ano")
        if isinstance(year, int):
            years.add(year)

    return sorted(years)


def _project_status_options(rows: Sequence[Mapping[str, object]]) -> list[str]:
    statuses = {str(row.get("situacao_descricao", "")).strip() for row in rows}
    return sorted((status for status in statuses if status), key=str.casefold)


def _bar_chart_with_total_labels(
    st: Any,
    alt: Any,
    dataframe: Any,
    *,
    x: str,
    y: str,
    color: str,
    show_values: bool = True,
) -> None:
    if dataframe.empty:
        st.info("Sem dados para o grafico.")
        return

    x_type = "O" if x == "ano" else "N"
    label_angle = 0 if x == "ano" else -35
    base = alt.Chart(dataframe).encode(
        x=alt.X(
            f"{x}:{x_type}",
            sort=None,
            axis=alt.Axis(labelAngle=label_angle, labelLimit=160),
        ),
        y=alt.Y(
            f"{y}:Q",
            scale=_chart_y_scale(alt, dataframe, y),
            title=None,
        ),
        tooltip=[
            alt.Tooltip(f"{column}:N", title=title)
            for column, title in _chart_tooltip_fields(dataframe.columns, x)
        ],
    )
    bars = base.mark_bar(color=color)
    labels = base.mark_text(
        align="center",
        baseline="bottom",
        dy=-5,
        fontSize=12,
    ).encode(text=alt.Text(f"{_CHART_LABEL_COLUMN}:N"))

    chart = bars + labels if show_values else bars

    st.altair_chart(chart.properties(height=360), use_container_width=True)


def _grouped_bar_chart_with_total_labels(
    st: Any,
    alt: Any,
    dataframe: Any,
    *,
    x: str,
    y: str,
    color: str,
    color_domain: Sequence[str],
    color_range: Sequence[str],
    stack: str | None = None,
    show_values: bool = True,
) -> None:
    if dataframe.empty:
        st.info("Sem dados para o grafico.")
        return

    y_encoding = alt.Y(
        f"{y}:Q",
        scale=_chart_y_scale(alt, dataframe, y),
        stack=stack,
        title=None,
    )
    encodings = {
        "x": alt.X(
            f"{x}:O",
            sort=None,
            axis=alt.Axis(labelAngle=0, labelLimit=160),
        ),
        "y": y_encoding,
        "color": alt.Color(
            f"{color}:N",
            scale=alt.Scale(domain=list(color_domain), range=list(color_range)),
            title=None,
        ),
        "tooltip": [
            alt.Tooltip(f"{column}:N", title=title)
            for column, title in _financial_chart_tooltip_fields(
                dataframe.columns,
                x,
                color,
            )
        ],
    }
    if stack is None:
        encodings["xOffset"] = alt.XOffset(f"{color}:N", title=None)

    base = alt.Chart(dataframe).encode(
        **encodings,
    )
    bars = base.mark_bar()
    labels = base.mark_text(
        align="center",
        baseline="bottom",
        dy=-5,
        fontSize=12,
    ).encode(text=alt.Text(f"{_CHART_LABEL_COLUMN}:N"))

    chart = bars + labels if show_values else bars

    st.altair_chart(chart.properties(height=360), use_container_width=True)


def _chart_tooltip_fields(
    columns: Sequence[str],
    x_column: str,
) -> list[tuple[str, str]]:
    existing_columns = set(columns)
    tooltip_fields = [(x_column, x_column)]

    for column_options, title in _TOOLTIP_FIELD_GROUPS:
        for column in column_options:
            if column in existing_columns and column != x_column:
                tooltip_fields.append((column, title))
                break

    return tooltip_fields


def _financial_chart_tooltip_fields(
    columns: Sequence[str],
    x_column: str,
    color_column: str,
) -> list[tuple[str, str]]:
    existing_columns = set(columns)
    tooltip_fields = [(x_column, x_column), (color_column, "Tipo")]
    optional_fields = (
        (_CHART_LABEL_COLUMN, "Total"),
        (_PROJECTS_COLUMN, "Projetos"),
        (_SCHOLARSHIPS_COLUMN, "Bolsas"),
    )
    for column, title in optional_fields:
        if column in existing_columns:
            tooltip_fields.append((column, title))

    return tooltip_fields


def _financial_chart_stack_from_mode(mode_label: str) -> str | None:
    if mode_label == "Barras empilhadas":
        return "zero"

    return None


def _chart_y_scale(alt: Any, dataframe: Any, y: str) -> Any:
    max_value = _max_chart_value(dataframe, y)
    if max_value <= 0:
        return alt.Scale(zero=True)

    return alt.Scale(domain=[0, max_value * 1.15])


def _max_chart_value(dataframe: Any, y: str) -> float:
    try:
        values = [float(value) for value in dataframe[y].dropna()]
    except (AttributeError, KeyError, TypeError, ValueError):
        return 0.0

    return max(values, default=0.0)


def _chart_dataframe(
    pd_module: Any,
    rows: Sequence[Mapping[str, object]],
    y_column: str,
) -> Any:
    return pd_module.DataFrame(_chart_rows_with_labels(rows, y_column))


def _chart_rows_with_labels(
    rows: Sequence[Mapping[str, object]],
    y_column: str,
) -> list[ReportRow]:
    chart_rows: list[ReportRow] = []
    for row in rows:
        chart_row = dict(row)
        _add_money_tooltip_value(
            chart_row,
            row,
            _BUDGET_TOOLTIP_COLUMN,
            (_BUDGET_COLUMN, _BUDGET_VALUE_COLUMN),
        )
        _add_money_tooltip_value(
            chart_row,
            row,
            _SCHOLARSHIP_AMOUNT_TOOLTIP_COLUMN,
            (_SCHOLARSHIP_AMOUNT_COLUMN, _SCHOLARSHIP_AMOUNT_VALUE_COLUMN),
        )
        chart_row[y_column] = _chart_numeric_value(row, y_column)
        chart_row[_CHART_LABEL_COLUMN] = _chart_total_label(row, y_column)
        chart_rows.append(chart_row)

    return chart_rows


def _researcher_financial_timeline_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[ReportRow]:
    financial_rows: list[ReportRow] = []
    for row in rows:
        financial_rows.extend(
            [
                _researcher_financial_timeline_row(
                    row,
                    volume_type="Orcamento contratado",
                    value_column=_BUDGET_VALUE_COLUMN,
                    label_column=_BUDGET_COLUMN,
                ),
                _researcher_financial_timeline_row(
                    row,
                    volume_type="Valor bolsas",
                    value_column=_SCHOLARSHIP_AMOUNT_VALUE_COLUMN,
                    label_column=_SCHOLARSHIP_AMOUNT_COLUMN,
                ),
            ]
        )

    return financial_rows


def _researcher_financial_timeline_row(
    row: Mapping[str, object],
    *,
    volume_type: str,
    value_column: str,
    label_column: str,
) -> ReportRow:
    return {
        "ano": row.get("ano", ""),
        _FINANCIAL_VOLUME_TYPE_COLUMN: volume_type,
        _FINANCIAL_VOLUME_VALUE_COLUMN: _chart_numeric_value(row, value_column),
        _CHART_LABEL_COLUMN: _short_currency_label(
            row.get(label_column, row.get(value_column))
        ),
        _PROJECTS_COLUMN: _int_value(row.get(_PROJECTS_COLUMN)),
        _SCHOLARSHIPS_COLUMN: _int_value(row.get(_SCHOLARSHIPS_COLUMN)),
    }


def _researcher_financial_timeline_table_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[ReportRow]:
    table_rows: list[ReportRow] = []
    for row in rows:
        budget = _decimal(row.get(_BUDGET_COLUMN, row.get(_BUDGET_VALUE_COLUMN)))
        scholarships = _decimal(
            row.get(
                _SCHOLARSHIP_AMOUNT_COLUMN, row.get(_SCHOLARSHIP_AMOUNT_VALUE_COLUMN)
            )
        )
        table_rows.append(
            {
                "Ano": row.get("ano", ""),
                "Projetos": _int_value(row.get(_PROJECTS_COLUMN)),
                "Bolsas": _int_value(row.get(_SCHOLARSHIPS_COLUMN)),
                "Orcamento contratado": _currency_label(budget),
                "Valor bolsas": _currency_label(scholarships),
                "Total financeiro": _currency_label(budget + scholarships),
            }
        )

    return table_rows


def _add_money_tooltip_value(
    target_row: ReportRow,
    source_row: Mapping[str, object],
    tooltip_column: str,
    source_columns: Sequence[str],
) -> None:
    for column in source_columns:
        if column in source_row:
            target_row[tooltip_column] = _currency_label(source_row.get(column))
            return


def _chart_numeric_value(row: Mapping[str, object], y_column: str) -> int | float:
    if y_column in _FINANCIAL_CHART_COLUMNS:
        return float(_decimal(row.get(y_column)))

    return _int_value(row.get(y_column))


def _chart_total_label(row: Mapping[str, object], y_column: str) -> str:
    if y_column == _BUDGET_VALUE_COLUMN:
        return _short_currency_label(row.get(_BUDGET_COLUMN, row.get(y_column)))
    if y_column == _SCHOLARSHIP_AMOUNT_VALUE_COLUMN:
        return _short_currency_label(
            row.get(_SCHOLARSHIP_AMOUNT_COLUMN, row.get(y_column))
        )
    if y_column in {
        _BUDGET_COLUMN,
        _SCHOLARSHIP_AMOUNT_COLUMN,
        _RESEARCHER_SCHOLARSHIP_TOTAL_COLUMN,
        _SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN,
        _SCHOLARSHIP_ALLOCATION_PAID_AMOUNT_COLUMN,
    }:
        return _short_currency_label(row.get(y_column))

    return _number_label(_int_value(row.get(y_column)))


_FINANCIAL_CHART_COLUMNS: Final = frozenset(
    {
        _BUDGET_COLUMN,
        _BUDGET_VALUE_COLUMN,
        _SCHOLARSHIP_AMOUNT_COLUMN,
        _SCHOLARSHIP_AMOUNT_VALUE_COLUMN,
        _RESEARCHER_SCHOLARSHIP_TOTAL_COLUMN,
        _SCHOLARSHIP_ALLOCATION_ALLOCATED_AMOUNT_COLUMN,
        _SCHOLARSHIP_ALLOCATION_PAID_AMOUNT_COLUMN,
    }
)


def _display_dataframe(pd_module: Any, rows: Sequence[Mapping[str, object]]) -> Any:
    return pd_module.DataFrame(_display_rows(rows))


def _render_sortable_dataframe(st: Any, dataframe: Any) -> None:
    sortable_frame = _sortable_table_dataframe(dataframe)
    st.dataframe(
        sortable_frame,
        use_container_width=True,
        hide_index=True,
        column_config=_sortable_table_column_config(st, sortable_frame),
    )


def _sortable_table_dataframe(dataframe: Any) -> Any:
    sortable_frame = dataframe.copy()
    for column in _sortable_table_money_columns(sortable_frame):
        sortable_frame[column] = sortable_frame[column].map(
            lambda value: float(_decimal(value))
        )

    return sortable_frame


def _sortable_table_column_config(st: Any, dataframe: Any) -> dict[str, Any]:
    return {
        column: st.column_config.NumberColumn(column, format="R$ %.2f")
        for column in _sortable_table_money_columns(dataframe)
    }


def _sortable_table_money_columns(dataframe: Any) -> list[str]:
    try:
        columns = list(dataframe.columns)
    except AttributeError:
        return []

    return [column for column in columns if column in _TABLE_MONEY_COLUMNS]


def _summary_totals(rows: Sequence[Mapping[str, object]]) -> DashboardTotals:
    total_scholarship_amount = sum(
        (_decimal(row.get(_SCHOLARSHIP_AMOUNT_COLUMN)) for row in rows),
        Decimal("0"),
    )
    total_budget = sum(
        (_decimal(row.get(_BUDGET_COLUMN)) for row in rows),
        Decimal("0"),
    )

    return DashboardTotals(
        total_institutions=len(rows),
        total_projects=sum(_int_value(row.get(_PROJECTS_COLUMN)) for row in rows),
        total_scholarships=sum(
            _int_value(row.get(_SCHOLARSHIPS_COLUMN)) for row in rows
        ),
        total_scholarship_amount=_money(total_scholarship_amount),
        total_budget=_money(total_budget),
    )


def _display_rows(rows: Sequence[Mapping[str, object]]) -> list[ReportRow]:
    display_rows: list[ReportRow] = []
    for row in rows:
        display_row = dict(row)
        display_row[_SCHOLARSHIP_AMOUNT_COLUMN] = _money(
            _decimal(row.get(_SCHOLARSHIP_AMOUNT_COLUMN))
        )
        display_row[_BUDGET_COLUMN] = _money(_decimal(row.get(_BUDGET_COLUMN)))
        display_rows.append(display_row)

    return display_rows


def _institution_label(row: Mapping[str, object]) -> str:
    name = str(row.get("instituicao_nome", "")).strip()
    acronym = str(row.get("instituicao_sigla", "")).strip()
    if name and acronym:
        return f"{name} | {acronym}"
    if name:
        return name
    return acronym


def _metric_from_label(label: str) -> str:
    if label == "Quantidade de bolsas":
        return _SCHOLARSHIPS_COLUMN
    if label == "Bolsas concedidas financeiro":
        return _SCHOLARSHIP_AMOUNT_COLUMN
    if label == "Total de projetos":
        return _PROJECTS_COLUMN
    return _BUDGET_COLUMN


def _currency_label(value: object) -> str:
    return f"R$ {_money(_decimal(value))}"


def _short_currency_label(value: object) -> str:
    amount = _decimal(value)
    absolute_amount = abs(amount)
    units = (
        (Decimal("1000000000"), "bi"),
        (Decimal("1000000"), "mi"),
        (Decimal("1000"), "mil"),
    )

    for divisor, suffix in units:
        if absolute_amount >= divisor:
            return f"R$ {_short_decimal(amount / divisor)} {suffix}"

    return _currency_label(amount)


def _short_decimal(value: Decimal) -> str:
    formatted = f"{value.quantize(Decimal('0.1'))}"
    return formatted.replace(".", ",").removesuffix(",0")


def _number_label(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0")

    raw_value = str(value).strip()
    if not raw_value:
        return Decimal("0")

    normalized = raw_value.replace("R$", "").replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    elif "," in normalized:
        normalized = normalized.replace(",", ".")

    try:
        return Decimal(normalized)
    except InvalidOperation:
        return Decimal("0")


def _int_value(value: object) -> int:
    return int(_decimal(value))


def _money(value: Decimal) -> str:
    formatted = f"{value.quantize(Decimal('0.01')):,.2f}"
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".")


if __name__ == "__main__":
    run_app()
