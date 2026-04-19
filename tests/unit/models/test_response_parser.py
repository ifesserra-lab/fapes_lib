from __future__ import annotations

import pytest

from fapes_lib.exceptions import FapesEnvelopeError


def test_parse_standard_response_envelope_preserves_metadata_and_extras() -> None:
    from fapes_lib.models.responses import FapesResponseEnvelope

    response = FapesResponseEnvelope.parse(
        [
            {
                "data": [{"edital_id": 1, "campo_extra": "preservado"}],
                "encontrado": "1",
                "msg": "ok",
                "erro": "",
                "qtd": "1",
                "tempo_execucao": "10ms",
            },
        ],
    )

    assert response.data == [{"edital_id": 1, "campo_extra": "preservado"}]
    assert response.encontrado == 1
    assert response.msg == "ok"
    assert response.erro == ""
    assert response.qtd == 1
    assert response.extra == {"tempo_execucao": "10ms"}


def test_parse_direct_setores_response_without_envelope() -> None:
    from fapes_lib.models.responses import FapesResponseEnvelope

    response = FapesResponseEnvelope.parse_direct_list(
        [
            {"sigla": "DITEC", "descricao": "Diretoria Tecnica"},
            {"sigla": "GER", "descricao": "Gerencia"},
        ],
    )

    assert response.data == [
        {"sigla": "DITEC", "descricao": "Diretoria Tecnica"},
        {"sigla": "GER", "descricao": "Gerencia"},
    ]
    assert response.encontrado == 1
    assert response.qtd == 2


def test_parse_empty_direct_setores_response() -> None:
    from fapes_lib.models.responses import FapesResponseEnvelope

    response = FapesResponseEnvelope.parse_direct_list([])

    assert response.data == []
    assert response.encontrado == 0
    assert response.qtd == 0


def test_parse_invalid_envelope_raises_domain_error() -> None:
    from fapes_lib.models.responses import FapesResponseEnvelope

    with pytest.raises(FapesEnvelopeError) as exc_info:
        FapesResponseEnvelope.parse({"data": []})

    assert "envelope" in str(exc_info.value).lower()


def test_parse_envelope_with_non_list_data_raises_domain_error() -> None:
    from fapes_lib.models.responses import FapesResponseEnvelope

    with pytest.raises(FapesEnvelopeError):
        FapesResponseEnvelope.parse(
            [
                {
                    "data": {"unexpected": "dict"},
                    "encontrado": 1,
                    "msg": "",
                    "erro": "",
                    "qtd": 1,
                },
            ],
        )
