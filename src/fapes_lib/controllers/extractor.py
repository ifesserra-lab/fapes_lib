"""Composed extraction flows for FAPES API data."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from fapes_lib.controllers.query_controller import QueryParameterValue
from fapes_lib.exceptions import FapesError, FapesExtractionError
from fapes_lib.models import FapesResponseEnvelope, JsonObject

__all__ = [
    "FapesExtractionApi",
    "FapesExtractionMetadata",
    "FapesExtractionResult",
    "FapesExtractor",
]

T = TypeVar("T")


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


class FapesExtractor:
    """Orchestrate predictable extraction flows using a direct API client."""

    def __init__(self, *, api_client: FapesExtractionApi) -> None:
        self._api_client = api_client

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

        editais = self._records(
            self._run_step("listar_editais", self._api_client.listar_editais)
        )
        enriched: list[JsonObject] = []
        total_chamadas = 0

        for edital in editais:
            item = dict(edital)
            codedt = _identifier(item, "edital_id", "codedt")
            chamadas: list[JsonObject] = []

            if codedt is not None:
                chamadas = self._records(
                    self._run_step(
                        f"listar_edital_chamadas:{codedt}",
                        self._endpoint_call(
                            self._api_client.listar_edital_chamadas,
                            codedt,
                        ),
                    )
                )

            item["chamadas"] = chamadas
            total_chamadas += len(chamadas)
            enriched.append(item)

        return self._result(
            data={"editais": enriched},
            steps=("listar_editais", "listar_edital_chamadas"),
            counts={"editais": len(enriched), "chamadas": total_chamadas},
        )

    def extrair_editais_com_projetos(self) -> FapesExtractionResult:
        """Extract editais and attach their projects when an id is present."""

        editais = self._records(
            self._run_step("listar_editais", self._api_client.listar_editais)
        )
        enriched: list[JsonObject] = []
        total_projetos = 0

        for edital in editais:
            item = dict(edital)
            codedt = _identifier(item, "edital_id", "codedt")
            projetos: list[JsonObject] = []

            if codedt is not None:
                projetos = self._records(
                    self._run_step(
                        f"listar_projetos:{codedt}",
                        self._endpoint_call(self._api_client.listar_projetos, codedt),
                    )
                )

            item["projetos"] = projetos
            total_projetos += len(projetos)
            enriched.append(item)

        return self._result(
            data={"editais": enriched},
            steps=("listar_editais", "listar_projetos"),
            counts={"editais": len(enriched), "projetos": total_projetos},
        )

    def extrair_projetos_com_bolsas_bolsistas(
        self,
        projetos: Iterable[JsonObject],
    ) -> FapesExtractionResult:
        """Extract grants and holders for each project with an identifier."""

        enriched: list[JsonObject] = []
        total_bolsas = 0
        total_bolsistas = 0

        for projeto in projetos:
            item = dict(projeto)
            codprj = _identifier(item, "projeto_id", "codprj")
            bolsas: list[JsonObject] = []
            bolsistas: list[JsonObject] = []

            if codprj is not None:
                bolsas = self._records(
                    self._run_step(
                        f"listar_projeto_bolsas:{codprj}",
                        self._endpoint_call(
                            self._api_client.listar_projeto_bolsas,
                            codprj,
                        ),
                    )
                )
                bolsistas = self._records(
                    self._run_step(
                        f"listar_bolsistas:{codprj}",
                        self._endpoint_call(
                            self._api_client.listar_bolsistas,
                            codprj,
                        ),
                    )
                )

            item["bolsas"] = bolsas
            item["bolsistas"] = bolsistas
            total_bolsas += len(bolsas)
            total_bolsistas += len(bolsistas)
            enriched.append(item)

        return self._result(
            data={"projetos": enriched},
            steps=("listar_projeto_bolsas", "listar_bolsistas"),
            counts={
                "projetos": len(enriched),
                "bolsas": total_bolsas,
                "bolsistas": total_bolsistas,
            },
        )

    def extrair_completa(self) -> FapesExtractionResult:
        """Run the complete extraction flow in a predictable order."""

        cadastros = self.extrair_cadastros_auxiliares()
        editais_com_chamadas = self.extrair_editais_com_chamadas()
        editais_com_projetos = self.extrair_editais_com_projetos()
        projetos = _flatten_projects(editais_com_projetos.data["editais"])
        projetos_com_bolsas = self.extrair_projetos_com_bolsas_bolsistas(projetos)

        return self._result(
            data={
                "cadastros_auxiliares": cadastros.data,
                "editais_com_chamadas": editais_com_chamadas.data,
                "editais_com_projetos": editais_com_projetos.data,
                "projetos_com_bolsas_bolsistas": projetos_com_bolsas.data,
            },
            steps=(
                cadastros.metadata.steps
                + editais_com_chamadas.metadata.steps
                + editais_com_projetos.metadata.steps
                + projetos_com_bolsas.metadata.steps
            ),
            counts={
                "cadastros_auxiliares": len(cadastros.data),
                "editais_com_chamadas": len(editais_com_chamadas.data["editais"]),
                "editais_com_projetos": len(editais_com_projetos.data["editais"]),
                "projetos_com_bolsas_bolsistas": len(
                    projetos_com_bolsas.data["projetos"]
                ),
            },
        )

    def _run_step(self, step: str, operation: Callable[[], T]) -> T:
        try:
            return operation()
        except FapesError as exc:
            raise FapesExtractionError(
                "FAPES extraction step failed",
                context={
                    "step": step,
                    "cause": str(exc),
                },
            ) from exc

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
