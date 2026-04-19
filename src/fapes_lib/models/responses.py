"""Response models and parsers for FAPES API payloads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from fapes_lib.exceptions import FapesEnvelopeError

JsonObject = dict[str, Any]

__all__ = [
    "FapesResponseEnvelope",
    "JsonObject",
]

_ENVELOPE_KEYS = {"data", "encontrado", "msg", "erro", "qtd"}


@dataclass(frozen=True, slots=True)
class FapesResponseEnvelope:
    """Parsed FAPES response envelope with preserved unknown metadata."""

    data: list[JsonObject]
    encontrado: int
    msg: str
    erro: str
    qtd: int
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def parse(cls, payload: object) -> FapesResponseEnvelope:
        """Parse the standard `data/encontrado/msg/erro/qtd` envelope.

        Raises:
            FapesEnvelopeError: When the envelope shape is invalid.
        """

        raw_envelope = _extract_single_envelope(payload)
        data = raw_envelope.get("data")
        if not isinstance(data, list):
            raise _invalid_envelope("FAPES envelope data must be a list", payload)

        return cls(
            data=[_copy_object(item, "FAPES envelope data item") for item in data],
            encontrado=_coerce_int(raw_envelope.get("encontrado"), "encontrado"),
            msg=str(raw_envelope.get("msg", "")),
            erro=str(raw_envelope.get("erro", "")),
            qtd=_coerce_int(raw_envelope.get("qtd"), "qtd"),
            extra={
                str(key): value
                for key, value in raw_envelope.items()
                if str(key) not in _ENVELOPE_KEYS
            },
        )

    @classmethod
    def parse_direct_list(cls, payload: object) -> FapesResponseEnvelope:
        """Parse endpoint responses that return a direct list, such as setores.

        Raises:
            FapesEnvelopeError: When the payload is not a list of objects.
        """

        if not isinstance(payload, list):
            raise _invalid_envelope("FAPES direct response must be a list", payload)

        data = [_copy_object(item, "FAPES direct response item") for item in payload]
        return cls(
            data=data,
            encontrado=1 if data else 0,
            msg="",
            erro="",
            qtd=len(data),
        )


def _extract_single_envelope(payload: object) -> Mapping[str, Any]:
    sequence = _as_sequence(payload)
    if len(sequence) != 1:
        raise _invalid_envelope(
            "FAPES response envelope must be a single-item list",
            payload,
        )

    envelope = sequence[0]
    if not isinstance(envelope, Mapping):
        raise _invalid_envelope(
            "FAPES response envelope item must be an object",
            payload,
        )

    missing = sorted(_ENVELOPE_KEYS.difference(str(key) for key in envelope))
    if missing:
        raise _invalid_envelope(
            "FAPES response envelope is missing required fields",
            payload,
            missing=missing,
        )

    return envelope


def _copy_object(value: object, label: str) -> JsonObject:
    if not isinstance(value, Mapping):
        raise _invalid_envelope(f"{label} must be an object", value)

    return {str(key): item for key, item in value.items()}


def _coerce_int(value: object, field_name: str) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:
        raise _invalid_envelope(
            f"FAPES envelope field {field_name} must be an integer",
            value,
        ) from exc


def _as_sequence(value: object) -> Sequence[object]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return value

    raise _invalid_envelope("FAPES response envelope must be a list", value)


def _invalid_envelope(
    message: str,
    payload: object,
    *,
    missing: list[str] | None = None,
) -> FapesEnvelopeError:
    context: dict[str, object] = {"payload": payload}
    if missing:
        context["missing"] = missing
    return FapesEnvelopeError(message, context=context)
