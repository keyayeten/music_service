from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

ROLE_SEED_DATA: tuple[tuple[str, str], ...] = (
    ("admin", "Administrator"),
    ("moderator", "Moderator"),
    ("composer", "Composer"),
    ("user", "User"),
)


def seed_identity_roles(session: Session) -> None:
    for code, name in ROLE_SEED_DATA:
        session.execute(
            text(
                """
                INSERT INTO roles (code, name)
                VALUES (:code, :name)
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {"code": code, "name": name},
        )
