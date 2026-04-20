from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, cast

import pytest

from fapes_lib.controllers.extractor import (
    FapesExtractionMetadata,
    FapesExtractionResult,
)


class FakeExtractor:
    def __init__(self) -> None:
        self.destination_dir: Path | None = None
        self.max_workers: int | None = None
        self.retry_attempts: int | None = None
        self.skip_existing: bool | None = None

    def extrair_projetos_dos_editais_em_threads(
        self,
        *,
        destination_dir: str | Path,
        max_workers: int | None = None,
        retry_attempts: int = 0,
        skip_existing: bool = False,
    ) -> FapesExtractionResult:
        self.destination_dir = Path(destination_dir)
        self.max_workers = max_workers
        self.retry_attempts = retry_attempts
        self.skip_existing = skip_existing
        return FapesExtractionResult(
            data={
                "editais": [
                    {
                        "edital_id": 756,
                        "arquivo_projetos": str(
                            Path(destination_dir) / "edital_756_projetos.json"
                        ),
                    }
                ]
            },
            metadata=FapesExtractionMetadata(
                steps=("listar_editais", "listar_projetos:756"),
                counts={"editais": 1, "projetos": 2, "arquivos": 1},
            ),
        )


def test_main_downloads_projects_for_all_editais(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    main_module = cast(Any, importlib.import_module("scripts.main"))

    fake_extractor = FakeExtractor()

    def extractor_factory() -> FakeExtractor:
        return fake_extractor

    exit_code = main_module.run(
        [
            "--output-dir",
            str(tmp_path),
            "--max-workers",
            "4",
            "--retries",
            "3",
            "--skip-existing",
        ],
        extractor_factory=extractor_factory,
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert fake_extractor.destination_dir == tmp_path
    assert fake_extractor.max_workers == 4
    assert fake_extractor.retry_attempts == 3
    assert fake_extractor.skip_existing is True
    assert "Editais: 1" in output
    assert "Projetos: 2" in output
    assert "Arquivos: 1" in output
    assert str(tmp_path) in output
