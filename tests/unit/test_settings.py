from pathlib import Path

import pytest

from fapes_lib.exceptions import FapesConfigError


def test_settings_load_required_environment_values() -> None:
    from fapes_lib.settings import FapesSettings

    settings = FapesSettings.from_env(
        environ={
            "FAPES_AUTH_URL": "https://example.test/auth.php",
            "FAPES_USUARIO": "service-user",
            "FAPES_SENHA": "secret-password",
        },
    )

    assert settings.auth_url == "https://example.test/auth.php"
    assert settings.usuario == "service-user"
    assert settings.senha == "secret-password"
    assert settings.base_url == "https://servicos.fapes.es.gov.br/webServicesSig/"
    assert settings.timeout_seconds == 30.0
    assert "secret-password" not in repr(settings)


def test_settings_load_values_from_dotenv_file(tmp_path: Path) -> None:
    from fapes_lib.settings import FapesSettings

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "FAPES_AUTH_URL=https://example.test/auth.php",
                "FAPES_USUARIO=dotenv-user",
                "FAPES_SENHA=dotenv-password",
            ],
        ),
        encoding="utf-8",
    )

    settings = FapesSettings.from_env(dotenv_path=dotenv_path, environ={})

    assert settings.usuario == "dotenv-user"
    assert settings.senha == "dotenv-password"
    assert "dotenv-password" not in repr(settings)


def test_settings_environment_overrides_dotenv_file(tmp_path: Path) -> None:
    from fapes_lib.settings import FapesSettings

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "FAPES_AUTH_URL=https://dotenv.test/auth.php",
                "FAPES_USUARIO=dotenv-user",
                "FAPES_SENHA=dotenv-password",
            ],
        ),
        encoding="utf-8",
    )

    settings = FapesSettings.from_env(
        dotenv_path=dotenv_path,
        environ={
            "FAPES_AUTH_URL": "https://env.test/auth.php",
            "FAPES_USUARIO": "env-user",
            "FAPES_SENHA": "env-password",
        },
    )

    assert settings.auth_url == "https://env.test/auth.php"
    assert settings.usuario == "env-user"
    assert settings.senha == "env-password"


def test_settings_missing_required_value_raises_config_error_without_secret() -> None:
    from fapes_lib.settings import FapesSettings

    with pytest.raises(FapesConfigError) as exc_info:
        FapesSettings.from_env(
            environ={
                "FAPES_AUTH_URL": "https://example.test/auth.php",
                "FAPES_SENHA": "secret-password",
            },
        )

    message = str(exc_info.value)

    assert "FAPES_USUARIO" in message
    assert "secret-password" not in message


def test_settings_invalid_timeout_raises_config_error_without_secret() -> None:
    from fapes_lib.settings import FapesSettings

    with pytest.raises(FapesConfigError) as exc_info:
        FapesSettings.from_env(
            environ={
                "FAPES_AUTH_URL": "https://example.test/auth.php",
                "FAPES_USUARIO": "service-user",
                "FAPES_SENHA": "secret-password",
                "FAPES_TIMEOUT_SECONDS": "0",
            },
        )

    message = str(exc_info.value)

    assert "FAPES_TIMEOUT_SECONDS" in message
    assert "secret-password" not in message
