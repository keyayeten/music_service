import pytest
from sqlalchemy import text


@pytest.mark.integration
def test_users_is_superuser_column_exists_with_default_false(db_session) -> None:
    row = db_session.execute(
        text(
            """
            SELECT column_name, column_default, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'is_superuser'
            """
        )
    ).one()
    assert row.column_name == "is_superuser"
    assert row.is_nullable == "NO"
    assert row.column_default is not None
    assert "false" in str(row.column_default).lower()
