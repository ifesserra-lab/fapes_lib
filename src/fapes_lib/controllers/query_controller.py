"""Controller for FAPES query endpoint paths and payloads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from fapes_lib.exceptions import FapesRequestError
from fapes_lib.infrastructure.http_client import JsonValue

QueryParameterValue = str | int

__all__ = [
    "FapesQueryController",
    "FapesQueryFunction",
    "FapesQuerySpec",
]


class FapesJsonPoster(Protocol):
    """HTTP collaborator required by the query controller."""

    def post(
        self,
        endpoint: str,
        *,
        json: JsonValue = None,
        headers: Mapping[str, str] | None = None,
    ) -> JsonValue:
        """Send a JSON POST request to a relative endpoint."""


class FapesQueryFunction(StrEnum):
    """Supported FAPES query function names."""

    SETORES = "setores"
    EDITAIS = "editais"
    EDITAL_CHAMADAS = "edital_chamadas"
    EDITAL_OBJETOS_FILHOS = "edital_objetos_filhos"
    PROJETOS = "projetos"
    PROJETO_BOLSAS = "projeto_bolsas"
    BOLSISTAS = "bolsistas"
    PESQUISADOR = "pesquisador"
    MODALIDADE_BOLSAS = "modalidade_bolsas"
    SITUACAO_PROJETO = "situacao_projeto"


@dataclass(frozen=True, slots=True)
class FapesQuerySpec:
    """Endpoint contract for a single FAPES query function."""

    funcao: FapesQueryFunction
    required_parameters: tuple[str, ...] = ()

    @property
    def endpoint(self) -> str:
        """Return the endpoint relative to FAPES_BASE_URL."""

        return f"consulta.php/{self.funcao.value}"


_QUERY_SPECS = {
    FapesQueryFunction.SETORES: FapesQuerySpec(FapesQueryFunction.SETORES),
    FapesQueryFunction.EDITAIS: FapesQuerySpec(FapesQueryFunction.EDITAIS),
    FapesQueryFunction.EDITAL_CHAMADAS: FapesQuerySpec(
        FapesQueryFunction.EDITAL_CHAMADAS,
        required_parameters=("codedt",),
    ),
    FapesQueryFunction.EDITAL_OBJETOS_FILHOS: FapesQuerySpec(
        FapesQueryFunction.EDITAL_OBJETOS_FILHOS,
        required_parameters=("codedt",),
    ),
    FapesQueryFunction.PROJETOS: FapesQuerySpec(
        FapesQueryFunction.PROJETOS,
        required_parameters=("codedt",),
    ),
    FapesQueryFunction.PROJETO_BOLSAS: FapesQuerySpec(
        FapesQueryFunction.PROJETO_BOLSAS,
        required_parameters=("codprj",),
    ),
    FapesQueryFunction.BOLSISTAS: FapesQuerySpec(
        FapesQueryFunction.BOLSISTAS,
        required_parameters=("codprj",),
    ),
    FapesQueryFunction.PESQUISADOR: FapesQuerySpec(
        FapesQueryFunction.PESQUISADOR,
        required_parameters=("codpes",),
    ),
    FapesQueryFunction.MODALIDADE_BOLSAS: FapesQuerySpec(
        FapesQueryFunction.MODALIDADE_BOLSAS,
    ),
    FapesQueryFunction.SITUACAO_PROJETO: FapesQuerySpec(
        FapesQueryFunction.SITUACAO_PROJETO,
    ),
}


class FapesQueryController:
    """Complete FAPES query paths and payloads before transport execution."""

    def __init__(self, *, http_client: FapesJsonPoster, token: str) -> None:
        self._http_client = http_client
        self._token = token

    def execute(
        self,
        funcao: FapesQueryFunction | str,
        **parameters: QueryParameterValue,
    ) -> JsonValue:
        """POST to the relative query endpoint for the requested function.

        Raises:
            FapesRequestError: When the function is unknown or a required
                query parameter is missing.
        """

        spec = self._spec_for(funcao)
        payload = self.payload_for(spec.funcao, **parameters)
        return self._http_client.post(spec.endpoint, json=payload)

    def endpoint_for(self, funcao: FapesQueryFunction | str) -> str:
        """Return the relative endpoint path for a FAPES query function."""

        return self._spec_for(funcao).endpoint

    def payload_for(
        self,
        funcao: FapesQueryFunction | str,
        **parameters: QueryParameterValue,
    ) -> dict[str, Any]:
        """Return the JSON payload expected by a FAPES query endpoint.

        Raises:
            FapesRequestError: When a required query parameter is missing.
        """

        spec = self._spec_for(funcao)
        missing = [
            name
            for name in spec.required_parameters
            if parameters.get(name) in (None, "")
        ]
        if missing:
            raise FapesRequestError(
                "Missing required FAPES query parameter",
                context={
                    "funcao": spec.funcao.value,
                    "missing": missing,
                    "token": self._token,
                },
            )

        payload: dict[str, Any] = {
            "token": self._token,
            "funcao": spec.funcao.value,
        }
        payload.update(parameters)
        return payload

    def _spec_for(self, funcao: FapesQueryFunction | str) -> FapesQuerySpec:
        try:
            query_function = FapesQueryFunction(funcao)
        except ValueError as exc:
            raise FapesRequestError(
                "Unknown FAPES query function",
                context={"funcao": funcao, "token": self._token},
            ) from exc

        return _QUERY_SPECS[query_function]
