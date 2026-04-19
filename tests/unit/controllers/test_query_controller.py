from __future__ import annotations

from typing import Any

import pytest

from fapes_lib.exceptions import FapesRequestError


class RecordingHttpClient:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def post(
        self,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.requests.append((endpoint, json or {}))
        return {"ok": True}


def test_query_controller_complements_base_path_for_simple_function() -> None:
    from fapes_lib.controllers.query_controller import FapesQueryController

    http_client = RecordingHttpClient()
    controller = FapesQueryController(http_client=http_client, token="jwt-token")

    result = controller.execute("setores")

    assert result == {"ok": True}
    assert http_client.requests == [
        (
            "consulta.php/setores",
            {
                "token": "jwt-token",
                "funcao": "setores",
            },
        ),
    ]


def test_query_controller_adds_required_parameter_to_payload() -> None:
    from fapes_lib.controllers.query_controller import FapesQueryController

    http_client = RecordingHttpClient()
    controller = FapesQueryController(http_client=http_client, token="jwt-token")

    controller.execute("projetos", codedt=756)

    assert http_client.requests == [
        (
            "consulta.php/projetos",
            {
                "token": "jwt-token",
                "funcao": "projetos",
                "codedt": 756,
            },
        ),
    ]


def test_query_controller_fails_before_http_when_parameter_is_missing() -> None:
    from fapes_lib.controllers.query_controller import FapesQueryController

    http_client = RecordingHttpClient()
    controller = FapesQueryController(http_client=http_client, token="jwt-secret")

    with pytest.raises(FapesRequestError) as exc_info:
        controller.execute("projetos")

    assert http_client.requests == []
    assert "projetos" in str(exc_info.value)
    assert "codedt" in str(exc_info.value)
    assert "jwt-secret" not in str(exc_info.value)


def test_query_controller_fails_before_http_for_unknown_function() -> None:
    from fapes_lib.controllers.query_controller import FapesQueryController

    http_client = RecordingHttpClient()
    controller = FapesQueryController(http_client=http_client, token="jwt-secret")

    with pytest.raises(FapesRequestError) as exc_info:
        controller.execute("funcao_inexistente")

    assert http_client.requests == []
    assert "funcao_inexistente" in str(exc_info.value)
    assert "jwt-secret" not in str(exc_info.value)
