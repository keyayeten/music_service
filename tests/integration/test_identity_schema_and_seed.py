from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.infrastructure.persistence.seeds.identity_roles import seed_identity_roles


@pytest.mark.integration
def test_identity_roles_seed_is_idempotent(db_session) -> None:
    seed_identity_roles(db_session)
    seed_identity_roles(db_session)
    db_session.commit()

    roles_count = db_session.execute(text("SELECT COUNT(*) FROM roles WHERE code IN ('admin','moderator','composer','user')")).scalar_one()
    assert roles_count == 4


@pytest.mark.integration
def test_users_email_and_username_are_unique(db_session) -> None:
    uid1 = uuid4()
    uid2 = uuid4()
    email = f"{uuid4().hex}@example.com"
    username = f"user_{uuid4().hex[:12]}"

    db_session.execute(
        text(
            """
            INSERT INTO users (id, email, username, password_hash, status)
            VALUES (:id, :email, :username, :password_hash, :status)
            """
        ),
        {
            "id": uid1,
            "email": email,
            "username": username,
            "password_hash": "hash",
            "status": "active",
        },
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO users (id, email, username, password_hash, status)
                VALUES (:id, :email, :username, :password_hash, :status)
                """
            ),
            {
                "id": uid2,
                "email": email,
                "username": f"other_{uuid4().hex[:10]}",
                "password_hash": "hash",
                "status": "active",
            },
        )
        db_session.commit()
    db_session.rollback()
