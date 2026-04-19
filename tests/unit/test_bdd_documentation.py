from pathlib import Path


def test_bdd_tooling_decision_is_documented() -> None:
    documentation = Path("docs/bdd.md")

    assert documentation.exists()

    content = documentation.read_text(encoding="utf-8").lower()

    assert "pytest-bdd" in content
    assert "sem rede" in content
