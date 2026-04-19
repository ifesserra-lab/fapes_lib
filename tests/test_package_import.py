def test_package_exposes_version() -> None:
    import fapes_lib

    assert fapes_lib.__version__ == "0.0.0"
