from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest


def test_json_exporter_writes_valid_json_with_safe_metadata(
    tmp_path: Path,
) -> None:
    from fapes_lib.views.exporters import FapesJsonExporter

    destination = tmp_path / "dados.json"

    FapesJsonExporter().export(
        data={"editais": [{"edital_id": 756, "projetos": [{"projeto_id": 1}]}]},
        destination=destination,
        metadata={
            "fonte": "FAPES",
            "executed_at": "2026-04-19T18:00:00-03:00",
            "token": "jwt-secret",
            "senha": "secret-password",
        },
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert payload["data"] == {
        "editais": [{"edital_id": 756, "projetos": [{"projeto_id": 1}]}]
    }
    assert payload["metadata"] == {
        "fonte": "FAPES",
        "executed_at": "2026-04-19T18:00:00-03:00",
    }
    assert "jwt-secret" not in destination.read_text(encoding="utf-8")
    assert "secret-password" not in destination.read_text(encoding="utf-8")


def test_jsonl_exporter_writes_one_json_record_per_line(tmp_path: Path) -> None:
    from fapes_lib.views.exporters import FapesJsonlExporter

    destination = tmp_path / "dados.jsonl"

    FapesJsonlExporter().export(
        records=[{"id": 1, "nome": "A"}, {"id": 2, "nome": "B"}],
        destination=destination,
    )

    lines = destination.read_text(encoding="utf-8").splitlines()

    assert [json.loads(line) for line in lines] == [
        {"id": 1, "nome": "A"},
        {"id": 2, "nome": "B"},
    ]


def test_csv_exporter_writes_header_and_rows(tmp_path: Path) -> None:
    from fapes_lib.views.exporters import FapesCsvExporter

    destination = tmp_path / "dados.csv"

    FapesCsvExporter().export(
        records=[
            {"edital_id": 756, "nome": "Edital A"},
            {"edital_id": 757, "nome": "Edital B"},
        ],
        destination=destination,
    )

    with destination.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows == [
        {"edital_id": "756", "nome": "Edital A"},
        {"edital_id": "757", "nome": "Edital B"},
    ]


def test_csv_exporter_rejects_nested_records_without_partial_file(
    tmp_path: Path,
) -> None:
    from fapes_lib.exceptions import FapesExportError
    from fapes_lib.views.exporters import FapesCsvExporter

    destination = tmp_path / "dados.csv"

    with pytest.raises(FapesExportError) as exc_info:
        FapesCsvExporter().export(
            records=[{"edital_id": 756, "projetos": [{"projeto_id": 1}]}],
            destination=destination,
        )

    assert "CSV" in str(exc_info.value)
    assert "projetos" in str(exc_info.value)
    assert not destination.exists()


def test_exporter_wraps_write_errors_without_leaking_secrets(
    tmp_path: Path,
) -> None:
    from fapes_lib.exceptions import FapesExportError
    from fapes_lib.views.exporters import FapesJsonExporter

    destination = tmp_path / "token=jwt-secret"
    destination.mkdir()

    with pytest.raises(FapesExportError) as exc_info:
        FapesJsonExporter().export(
            data={"ok": True},
            destination=destination,
            metadata={"senha": "secret-password"},
        )

    message = str(exc_info.value)

    assert "jwt-secret" not in message
    assert "secret-password" not in message
