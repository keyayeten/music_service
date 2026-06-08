import pytest
import typer

from backend.cli import _resolve_superuser_credentials


@pytest.mark.unit
def test_resolve_superuser_credentials_no_input_requires_all_flags() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        _resolve_superuser_credentials(
            email="admin@example.com",
            username="admin",
            password=None,
            no_input=True,
        )
    assert exc_info.value.exit_code == 1


@pytest.mark.unit
def test_resolve_superuser_credentials_validates_password_length() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        _resolve_superuser_credentials(
            email="admin@example.com",
            username="admin",
            password="short",
            no_input=True,
        )
    assert exc_info.value.exit_code == 1


@pytest.mark.unit
def test_resolve_superuser_credentials_returns_normalized_email() -> None:
    email, username, password = _resolve_superuser_credentials(
        email="  Admin@Example.COM ",
        username="admin_user",
        password="SecurePass1!",
        no_input=True,
    )
    assert email == "admin@example.com"
    assert username == "admin_user"
    assert password == "SecurePass1!"
