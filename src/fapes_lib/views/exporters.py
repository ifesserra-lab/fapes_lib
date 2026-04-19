"""File exporters for extracted FAPES data."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping
from io import StringIO
from pathlib import Path
from typing import Any

from fapes_lib.exceptions import FapesExportError, mask_sensitive_text

__all__ = [
    "FapesCsvExporter",
    "FapesJsonExporter",
    "FapesJsonlExporter",
]

Destination = str | Path
Record = Mapping[str, Any]

_SENSITIVE_METADATA_MARKERS = (
    "senha",
    "password",
    "token",
    "authorization",
    "secret",
    "apikey",
    "jwt",
    "credential",
)


class FapesJsonExporter:
    """Export extracted FAPES data as JSON."""

    def export(
        self,
        *,
        data: object,
        destination: Destination,
        metadata: Mapping[str, object] | None = None,
    ) -> Path:
        payload: dict[str, object] = {"data": data}
        if metadata is not None:
            payload["metadata"] = _safe_metadata(metadata)

        content = f"{_json_dumps(payload, indent=2)}\n"
        return _write_text(destination, content)


class FapesJsonlExporter:
    """Export independent records as JSON Lines."""

    def export(
        self,
        *,
        records: Iterable[object],
        destination: Destination,
    ) -> Path:
        lines = [_json_dumps(record, indent=None) for record in records]
        content = "\n".join(lines)
        if content:
            content = f"{content}\n"

        return _write_text(destination, content)


class FapesCsvExporter:
    """Export flat dictionaries as CSV."""

    def export(
        self,
        *,
        records: Iterable[Record],
        destination: Destination,
    ) -> Path:
        records_list = [_copy_record(record) for record in records]
        _validate_flat_records(records_list)
        content = _csv_content(records_list)
        return _write_text(destination, content)


def _json_dumps(value: object, *, indent: int | None) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=indent)
    except TypeError as exc:
        raise FapesExportError(
            "FAPES export serialization failed",
            context={"error": str(exc)},
        ) from exc


def _write_text(destination: Destination, content: str) -> Path:
    path = Path(destination)
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise FapesExportError(
            "FAPES export write failed",
            context={"destination": str(path), "error": str(exc)},
        ) from exc
    return path


def _copy_record(record: Record) -> dict[str, Any]:
    return {str(key): value for key, value in record.items()}


def _validate_flat_records(records: Iterable[Record]) -> None:
    for index, record in enumerate(records):
        for field_name, value in record.items():
            if _is_nested(value):
                raise FapesExportError(
                    "CSV export requires flat records",
                    context={
                        "record_index": index,
                        "field": field_name,
                    },
                )


def _is_nested(value: object) -> bool:
    return isinstance(value, Mapping | list | tuple | set)


def _csv_content(records: list[dict[str, Any]]) -> str:
    fieldnames = _fieldnames(records)
    if not fieldnames:
        return ""

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def _fieldnames(records: Iterable[Record]) -> list[str]:
    names: list[str] = []
    for record in records:
        for field_name in record:
            if field_name not in names:
                names.append(field_name)
    return names


def _safe_metadata(metadata: Mapping[str, object]) -> dict[str, object]:
    safe: dict[str, object] = {}
    for key, value in metadata.items():
        normalized_key = str(key)
        if _is_sensitive_metadata_key(normalized_key):
            continue
        safe[normalized_key] = _safe_metadata_value(value)
    return safe


def _safe_metadata_value(value: object) -> object:
    if isinstance(value, Mapping):
        return _safe_metadata({str(key): item for key, item in value.items()})

    if isinstance(value, list):
        return [_safe_metadata_value(item) for item in value]

    if isinstance(value, tuple):
        return tuple(_safe_metadata_value(item) for item in value)

    if isinstance(value, str):
        return mask_sensitive_text(value)

    return value


def _is_sensitive_metadata_key(key: str) -> bool:
    normalized = "".join(character for character in key.lower() if character.isalnum())
    return any(marker in normalized for marker in _SENSITIVE_METADATA_MARKERS)
