"""Public client for direct FAPES API queries."""

from __future__ import annotations

from typing import Protocol

from fapes_lib.controllers.query_controller import (
    FapesQueryFunction,
    QueryParameterValue,
)
from fapes_lib.infrastructure.http_client import JsonValue
from fapes_lib.models import FapesResponseEnvelope

__all__ = [
    "FapesApiClient",
    "FapesQueryExecutor",
]


class FapesQueryExecutor(Protocol):
    """Query collaborator required by the public API client."""

    def execute(
        self,
        funcao: FapesQueryFunction | str,
        **parameters: QueryParameterValue,
    ) -> JsonValue:
        """Execute a FAPES query function and return its JSON payload."""


class FapesApiClient:
    """Facade with direct query methods for the FAPES WebServicesSig API."""

    def __init__(self, *, query_controller: FapesQueryExecutor) -> None:
        self._query_controller = query_controller

    def listar_setores(self) -> FapesResponseEnvelope:
        """List FAPES sectors.

        The `setores` endpoint returns a direct list instead of the standard
        `data/encontrado/msg/erro/qtd` envelope.
        """

        return self._direct_list_query(FapesQueryFunction.SETORES)

    def listar_editais(self) -> FapesResponseEnvelope:
        """List FAPES public calls."""

        return self._standard_query(FapesQueryFunction.EDITAIS)

    def listar_edital_chamadas(
        self,
        codedt: QueryParameterValue,
    ) -> FapesResponseEnvelope:
        """List calls for a FAPES edital."""

        return self._standard_query(
            FapesQueryFunction.EDITAL_CHAMADAS,
            codedt=codedt,
        )

    def listar_edital_objetos_filhos(
        self,
        codedt: QueryParameterValue,
    ) -> FapesResponseEnvelope:
        """List child objects for a FAPES edital."""

        return self._standard_query(
            FapesQueryFunction.EDITAL_OBJETOS_FILHOS,
            codedt=codedt,
        )

    def listar_projetos(
        self,
        codedt: QueryParameterValue,
    ) -> FapesResponseEnvelope:
        """List projects for a FAPES edital."""

        return self._standard_query(FapesQueryFunction.PROJETOS, codedt=codedt)

    def listar_projeto_bolsas(
        self,
        codprj: QueryParameterValue,
    ) -> FapesResponseEnvelope:
        """List grants budgeted for a FAPES project."""

        return self._standard_query(
            FapesQueryFunction.PROJETO_BOLSAS,
            codprj=codprj,
        )

    def listar_bolsistas(
        self,
        codprj: QueryParameterValue,
    ) -> FapesResponseEnvelope:
        """List scholarship holders for a FAPES project."""

        return self._standard_query(FapesQueryFunction.BOLSISTAS, codprj=codprj)

    def obter_pesquisador(
        self,
        codpes: QueryParameterValue,
    ) -> FapesResponseEnvelope:
        """Get researcher details by FAPES researcher code."""

        return self._standard_query(FapesQueryFunction.PESQUISADOR, codpes=codpes)

    def listar_modalidade_bolsas(self) -> FapesResponseEnvelope:
        """List grant modalities and levels."""

        return self._standard_query(FapesQueryFunction.MODALIDADE_BOLSAS)

    def listar_situacao_projeto(self) -> FapesResponseEnvelope:
        """List project statuses."""

        return self._standard_query(FapesQueryFunction.SITUACAO_PROJETO)

    def _standard_query(
        self,
        funcao: FapesQueryFunction,
        **parameters: QueryParameterValue,
    ) -> FapesResponseEnvelope:
        payload = self._execute(funcao, **parameters)
        return FapesResponseEnvelope.parse(payload)

    def _direct_list_query(
        self,
        funcao: FapesQueryFunction,
        **parameters: QueryParameterValue,
    ) -> FapesResponseEnvelope:
        payload = self._execute(funcao, **parameters)
        return FapesResponseEnvelope.parse_direct_list(payload)

    def _execute(
        self,
        funcao: FapesQueryFunction,
        **parameters: QueryParameterValue,
    ) -> JsonValue:
        return self._query_controller.execute(funcao, **parameters)
