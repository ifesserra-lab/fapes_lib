def test_domain_exceptions_inherit_from_fapes_error() -> None:
    from fapes_lib.exceptions import (
        FapesAuthenticationError,
        FapesConfigError,
        FapesEnvelopeError,
        FapesError,
        FapesRequestError,
        FapesResponseError,
    )

    assert issubclass(FapesConfigError, FapesError)
    assert issubclass(FapesAuthenticationError, FapesError)
    assert issubclass(FapesRequestError, FapesError)
    assert issubclass(FapesResponseError, FapesError)
    assert issubclass(FapesEnvelopeError, FapesError)


def test_fapes_error_masks_sensitive_context_values() -> None:
    from fapes_lib.exceptions import FapesRequestError

    error = FapesRequestError(
        "Request failed",
        context={
            "endpoint": "setores",
            "status_code": 401,
            "senha": "password-to-mask",
            "headers": {
                "Authorization": "Bearer token-to-mask",
                "X-Request-ID": "req-123",
            },
            "detail": "token=inline-token",
        },
    )

    assert error.context == {
        "endpoint": "setores",
        "status_code": 401,
        "senha": "***",
        "headers": {
            "Authorization": "***",
            "X-Request-ID": "req-123",
        },
        "detail": "token=***",
    }
    assert "setores" in str(error)
    assert "401" in str(error)
    assert "req-123" in str(error)
    assert "password-to-mask" not in str(error)
    assert "token-to-mask" not in str(error)
    assert "inline-token" not in str(error)


def test_fapes_error_masks_sensitive_values_in_public_message() -> None:
    from fapes_lib.exceptions import FapesAuthenticationError

    error = FapesAuthenticationError(
        "Authentication failed for password-to-mask using token-to-mask",
        context={
            "usuario": "service-user",
            "senha": "password-to-mask",
            "token": "token-to-mask",
        },
    )

    public_message = str(error)

    assert "service-user" in public_message
    assert "password-to-mask" not in public_message
    assert "token-to-mask" not in public_message


def test_fapes_error_ignores_empty_sensitive_context_values() -> None:
    from fapes_lib.exceptions import FapesAuthenticationError

    error = FapesAuthenticationError(
        "Authentication failed",
        context={
            "token": "",
            "senha": None,
        },
    )

    assert str(error).startswith("Authentication failed")
