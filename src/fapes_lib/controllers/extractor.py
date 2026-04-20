"""Composed extraction flows for FAPES API data."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, TypeVar

from fapes_lib.controllers.query_controller import QueryParameterValue
from fapes_lib.exceptions import FapesError, FapesExtractionError
from fapes_lib.models import FapesResponseEnvelope, JsonObject
from fapes_lib.views.exporters import FapesJsonExporter

__all__ = [
    "FapesExtractionApi",
    "FapesExtractionMetadata",
    "FapesExtractionResult",
    "FapesExtractor",
]

T = TypeVar("T")
_LOGGER = logging.getLogger(__name__)


class FapesExtractionApi(Protocol):
    """Direct API operations required by the extractor."""

    def listar_setores(self) -> FapesResponseEnvelope: ...

    def listar_modalidade_bolsas(self) -> FapesResponseEnvelope: ...

    def listar_situacao_projeto(self) -> FapesResponseEnvelope: ...

    def listar_editais(self) -> FapesResponseEnvelope: ...

    def listar_edital_chamadas(
        self,
        codedt: QueryParameterValue,
    ) -> FapesResponseEnvelope: ...

    def listar_projetos(
        self,
        codedt: QueryParameterValue,
    ) -> FapesResponseEnvelope: ...

    def listar_projeto_bolsas(
        self,
        codprj: QueryParameterValue,
    ) -> FapesResponseEnvelope: ...

    def listar_bolsistas(
        self,
        codprj: QueryParameterValue,
    ) -> FapesResponseEnvelope: ...


@dataclass(frozen=True, slots=True)
class FapesExtractionMetadata:
    """Execution metadata returned by a composed extraction flow."""

    steps: tuple[str, ...]
    counts: dict[str, int] = field(default_factory=dict)
    success: bool = True


@dataclass(frozen=True, slots=True)
class FapesExtractionResult:
    """Data and metadata produced by a FAPES extraction flow."""

    data: dict[str, Any]
    metadata: FapesExtractionMetadata


@dataclass(frozen=True, slots=True)
class _EditalProjectsFile:
    index: int
    edital: JsonObject
    project_count: int
    file_count: int
    skipped_count: int
    steps: tuple[str, ...]


class FapesExtractor:
    """Orchestrate predictable extraction flows using a direct API client."""

    def __init__(
        self,
        *,
        api_client: FapesExtractionApi,
        logger: logging.Logger | None = None,
    ) -> None:
        self._api_client = api_client
        self._logger = logger if logger is not None else _LOGGER

    def extrair_cadastros_auxiliares(self) -> FapesExtractionResult:
        """Extract sectors, grant modalities and project statuses."""

        setores = self._records(
            self._run_step("listar_setores", self._api_client.listar_setores)
        )
        modalidade_bolsas = self._records(
            self._run_step(
                "listar_modalidade_bolsas",
                self._api_client.listar_modalidade_bolsas,
            )
        )
        situacao_projeto = self._records(
            self._run_step(
                "listar_situacao_projeto",
                self._api_client.listar_situacao_projeto,
            )
        )

        return self._result(
            data={
                "setores": setores,
                "modalidade_bolsas": modalidade_bolsas,
                "situacao_projeto": situacao_projeto,
            },
            steps=(
                "listar_setores",
                "listar_modalidade_bolsas",
                "listar_situacao_projeto",
            ),
            counts={
                "setores": len(setores),
                "modalidade_bolsas": len(modalidade_bolsas),
                "situacao_projeto": len(situacao_projeto),
            },
        )

    def extrair_editais_com_chamadas(self) -> FapesExtractionResult:
        """Extract editais and attach their chamadas when an id is present."""

        editais = self._list_editais()
        enriched, related_steps, total_chamadas = self._attach_chamadas(editais)

        return self._result(
            data={"editais": enriched},
            steps=("listar_editais", *related_steps),
            counts={"editais": len(enriched), "chamadas": total_chamadas},
        )

    def extrair_editais_com_projetos(self) -> FapesExtractionResult:
        """Extract editais and attach their projects when an id is present."""

        editais = self._list_editais()
        enriched, related_steps, total_projetos = self._attach_projetos(editais)

        return self._result(
            data={"editais": enriched},
            steps=("listar_editais", *related_steps),
            counts={"editais": len(enriched), "projetos": total_projetos},
        )

    def extrair_projetos_dos_editais_em_threads(
        self,
        *,
        destination_dir: str | Path,
        editais: Iterable[JsonObject] | None = None,
        max_workers: int | None = None,
        retry_attempts: int = 0,
        skip_existing: bool = False,
    ) -> FapesExtractionResult:
        """Extract edital projects concurrently and save one JSON file per edital."""

        destination = _ensure_output_directory(Path(destination_dir))
        retry_count = _retry_attempts(retry_attempts)
        initial_steps: tuple[str, ...]
        if editais is None:
            editais_list = self._list_editais()
            initial_steps = ("listar_editais",)
        else:
            editais_list = [dict(edital) for edital in editais]
            initial_steps = ()

        if not editais_list:
            return self._result(
                data={"editais": []},
                steps=initial_steps,
                counts={"editais": 0, "projetos": 0, "arquivos": 0},
            )

        worker_count = _worker_count(max_workers, len(editais_list))
        files_by_index: dict[int, _EditalProjectsFile] = {}

        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="fapes-edital",
        ) as executor:
            futures = {
                executor.submit(
                    self._extract_projects_for_edital_file,
                    index=index,
                    edital=edital,
                    destination_dir=destination,
                    retry_attempts=retry_count,
                    skip_existing=skip_existing,
                ): index
                for index, edital in enumerate(editais_list)
            }

            for future in as_completed(futures):
                try:
                    file_result = future.result()
                except FapesExtractionError:
                    raise
                except FapesError as exc:
                    raise FapesExtractionError(
                        "FAPES threaded project extraction failed",
                        context={"cause": str(exc)},
                    ) from exc

                files_by_index[file_result.index] = file_result

        ordered_files = [files_by_index[index] for index in range(len(editais_list))]
        enriched = [file_result.edital for file_result in ordered_files]
        skipped_files = sum(file_result.skipped_count for file_result in ordered_files)
        counts = {
            "editais": len(enriched),
            "projetos": sum(file_result.project_count for file_result in ordered_files),
            "arquivos": sum(file_result.file_count for file_result in ordered_files),
        }
        if skipped_files:
            counts["arquivos_existentes"] = skipped_files

        return self._result(
            data={"editais": enriched},
            steps=initial_steps
            + tuple(
                step for file_result in ordered_files for step in file_result.steps
            ),
            counts=counts,
        )

    def extrair_projetos_com_bolsas_bolsistas(
        self,
        projetos: Iterable[JsonObject],
    ) -> FapesExtractionResult:
        """Extract grants and holders for each project with an identifier."""

        enriched: list[JsonObject] = []
        total_bolsas = 0
        total_bolsistas = 0
        steps: list[str] = []

        for projeto in projetos:
            item = dict(projeto)
            codprj = _identifier(item, "projeto_id", "codprj")
            bolsas: list[JsonObject] = []
            bolsistas: list[JsonObject] = []

            if codprj is not None:
                bolsas_step = f"listar_projeto_bolsas:{codprj}"
                bolsas = self._records(
                    self._run_step(
                        bolsas_step,
                        self._endpoint_call(
                            self._api_client.listar_projeto_bolsas,
                            codprj,
                        ),
                    )
                )
                steps.append(bolsas_step)

                bolsistas_step = f"listar_bolsistas:{codprj}"
                bolsistas = self._records(
                    self._run_step(
                        bolsistas_step,
                        self._endpoint_call(
                            self._api_client.listar_bolsistas,
                            codprj,
                        ),
                    )
                )
                steps.append(bolsistas_step)

            item["bolsas"] = bolsas
            item["bolsistas"] = bolsistas
            total_bolsas += len(bolsas)
            total_bolsistas += len(bolsistas)
            enriched.append(item)

        return self._result(
            data={"projetos": enriched},
            steps=tuple(steps),
            counts={
                "projetos": len(enriched),
                "bolsas": total_bolsas,
                "bolsistas": total_bolsistas,
            },
        )

    def extrair_completa(self) -> FapesExtractionResult:
        """Run the complete extraction flow in a predictable order."""

        cadastros = self.extrair_cadastros_auxiliares()
        editais = self._list_editais()
        (
            editais_com_chamadas,
            chamadas_steps,
            _total_chamadas,
        ) = self._attach_chamadas(editais)
        (
            editais_com_projetos,
            projetos_steps,
            _total_projetos,
        ) = self._attach_projetos(editais)
        projetos = _flatten_projects(editais_com_projetos)
        projetos_com_bolsas = self.extrair_projetos_com_bolsas_bolsistas(projetos)

        return self._result(
            data={
                "cadastros_auxiliares": cadastros.data,
                "editais_com_chamadas": {"editais": editais_com_chamadas},
                "editais_com_projetos": {"editais": editais_com_projetos},
                "projetos_com_bolsas_bolsistas": projetos_com_bolsas.data,
            },
            steps=(
                cadastros.metadata.steps
                + ("listar_editais",)
                + chamadas_steps
                + projetos_steps
                + projetos_com_bolsas.metadata.steps
            ),
            counts={
                "cadastros_auxiliares": len(cadastros.data),
                "editais_com_chamadas": len(editais_com_chamadas),
                "editais_com_projetos": len(editais_com_projetos),
                "projetos_com_bolsas_bolsistas": len(
                    projetos_com_bolsas.data["projetos"]
                ),
            },
        )

    def _list_editais(self) -> list[JsonObject]:
        return self._records(
            self._run_step("listar_editais", self._api_client.listar_editais)
        )

    def _attach_chamadas(
        self,
        editais: Iterable[JsonObject],
    ) -> tuple[list[JsonObject], tuple[str, ...], int]:
        enriched: list[JsonObject] = []
        steps: list[str] = []
        total_chamadas = 0

        for edital in editais:
            item = dict(edital)
            codedt = _identifier(item, "edital_id", "codedt")
            chamadas: list[JsonObject] = []

            if codedt is not None:
                step = f"listar_edital_chamadas:{codedt}"
                chamadas = self._records(
                    self._run_step(
                        step,
                        self._endpoint_call(
                            self._api_client.listar_edital_chamadas,
                            codedt,
                        ),
                    )
                )
                steps.append(step)

            item["chamadas"] = chamadas
            total_chamadas += len(chamadas)
            enriched.append(item)

        return enriched, tuple(steps), total_chamadas

    def _attach_projetos(
        self,
        editais: Iterable[JsonObject],
    ) -> tuple[list[JsonObject], tuple[str, ...], int]:
        enriched: list[JsonObject] = []
        steps: list[str] = []
        total_projetos = 0

        for edital in editais:
            item = dict(edital)
            codedt = _identifier(item, "edital_id", "codedt")
            projetos: list[JsonObject] = []

            if codedt is not None:
                step = f"listar_projetos:{codedt}"
                projetos = self._records(
                    self._run_step(
                        step,
                        self._endpoint_call(self._api_client.listar_projetos, codedt),
                    )
                )
                steps.append(step)

            item["projetos"] = projetos
            total_projetos += len(projetos)
            enriched.append(item)

        return enriched, tuple(steps), total_projetos

    def _extract_projects_for_edital_file(
        self,
        *,
        index: int,
        edital: JsonObject,
        destination_dir: Path,
        retry_attempts: int,
        skip_existing: bool,
    ) -> _EditalProjectsFile:
        item = dict(edital)
        codedt = _identifier(item, "edital_id", "codedt")
        file_path = destination_dir / _edital_projects_filename(index, codedt)
        if skip_existing and file_path.exists():
            item["projetos"] = []
            item["arquivo_projetos"] = str(file_path)
            item["arquivo_projetos_existente"] = True
            return _EditalProjectsFile(
                index=index,
                edital=item,
                project_count=0,
                file_count=0,
                skipped_count=1,
                steps=(),
            )

        projetos: list[JsonObject] = []
        steps: tuple[str, ...] = ()

        if codedt is not None:
            step = f"listar_projetos:{codedt}"
            projetos = self._records(
                self._run_step_with_retries(
                    step,
                    self._endpoint_call(self._api_client.listar_projetos, codedt),
                    retry_attempts=retry_attempts,
                )
            )
            steps = (step,)

        FapesJsonExporter().export(
            data={"edital": dict(item), "projetos": projetos},
            destination=file_path,
            metadata={
                "codedt": codedt,
                "steps": steps,
                "counts": {"projetos": len(projetos)},
            },
        )

        item["projetos"] = projetos
        item["arquivo_projetos"] = str(file_path)

        return _EditalProjectsFile(
            index=index,
            edital=item,
            project_count=len(projetos),
            file_count=1,
            skipped_count=0,
            steps=steps,
        )

    def _run_step_with_retries(
        self,
        step: str,
        operation: Callable[[], T],
        *,
        retry_attempts: int,
    ) -> T:
        for attempt in range(retry_attempts + 1):
            try:
                return self._run_step(step, operation)
            except FapesExtractionError:
                if attempt >= retry_attempts:
                    raise
                self._logger.warning(
                    "FAPES extraction step retrying",
                    extra={
                        "fapes_event": "step_retrying",
                        "fapes_step": step,
                        "fapes_attempt": attempt + 1,
                        "fapes_retry_attempts": retry_attempts,
                    },
                )

        raise AssertionError("unreachable retry loop")

    def _run_step(self, step: str, operation: Callable[[], T]) -> T:
        self._log_step_started(step)
        try:
            result = operation()
        except FapesError as exc:
            self._log_step_failed(step, exc)
            raise FapesExtractionError(
                "FAPES extraction step failed",
                context={
                    "step": step,
                    "cause": str(exc),
                },
            ) from exc

        self._log_step_finished(step)
        return result

    def _log_step_started(self, step: str) -> None:
        self._logger.info(
            "FAPES extraction step started",
            extra={"fapes_event": "step_started", "fapes_step": step},
        )

    def _log_step_finished(self, step: str) -> None:
        self._logger.info(
            "FAPES extraction step finished",
            extra={"fapes_event": "step_finished", "fapes_step": step},
        )

    def _log_step_failed(self, step: str, exc: FapesError) -> None:
        self._logger.error(
            "FAPES extraction step failed",
            extra={
                "fapes_event": "step_failed",
                "fapes_step": step,
                "fapes_error": exc.message,
                "fapes_error_type": type(exc).__name__,
            },
        )

    @staticmethod
    def _endpoint_call(
        operation: Callable[[QueryParameterValue], FapesResponseEnvelope],
        parameter: QueryParameterValue,
    ) -> Callable[[], FapesResponseEnvelope]:
        def call() -> FapesResponseEnvelope:
            return operation(parameter)

        return call

    @staticmethod
    def _records(envelope: FapesResponseEnvelope) -> list[JsonObject]:
        return [dict(item) for item in envelope.data]

    @staticmethod
    def _result(
        *,
        data: dict[str, Any],
        steps: tuple[str, ...],
        counts: dict[str, int],
    ) -> FapesExtractionResult:
        return FapesExtractionResult(
            data=data,
            metadata=FapesExtractionMetadata(steps=steps, counts=counts),
        )


def _identifier(
    record: JsonObject,
    *field_names: str,
) -> QueryParameterValue | None:
    for field_name in field_names:
        value = record.get(field_name)
        if value in (None, ""):
            continue
        if isinstance(value, str | int):
            return value
        return str(value)

    return None


def _flatten_projects(editais: object) -> list[JsonObject]:
    if not isinstance(editais, list):
        return []

    projetos: list[JsonObject] = []
    for edital in editais:
        if not isinstance(edital, dict):
            continue
        edital_projetos = edital.get("projetos", [])
        if not isinstance(edital_projetos, list):
            continue
        projetos.extend(
            dict(projeto) for projeto in edital_projetos if isinstance(projeto, dict)
        )
    return projetos


def _ensure_output_directory(destination: Path) -> Path:
    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FapesExtractionError(
            "FAPES extraction output directory could not be created",
            context={"destination": str(destination), "error": str(exc)},
        ) from exc

    return destination


def _worker_count(max_workers: int | None, total_editais: int) -> int:
    if max_workers is None:
        return total_editais

    if max_workers < 1:
        raise FapesExtractionError(
            "FAPES threaded extraction requires at least one worker",
            context={"max_workers": max_workers},
        )

    return min(max_workers, total_editais)


def _retry_attempts(retry_attempts: int) -> int:
    if retry_attempts < 0:
        raise FapesExtractionError(
            "FAPES threaded extraction retries cannot be negative",
            context={"retry_attempts": retry_attempts},
        )

    return retry_attempts


def _edital_projects_filename(
    index: int,
    codedt: QueryParameterValue | None,
) -> str:
    if codedt is None:
        return f"edital_sem_identificador_{index + 1}_projetos.json"

    return f"edital_{_safe_filename_part(codedt)}_projetos.json"


def _safe_filename_part(value: QueryParameterValue) -> str:
    safe = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in str(value).strip()
    )
    return safe or "sem_identificador"
