from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from backend.application.moderation.use_cases.reports import ModerationReportUseCases
from backend.infrastructure.persistence.repositories.moderation import SqlAlchemyModerationRepository
from tests.async_tools import AsyncSessionAdapter, run_async


def _ensure_role(db_session, code: str, name: str) -> int:
    db_session.execute(
        text(
            """
            INSERT INTO roles (code, name)
            VALUES (:code, :name)
            ON CONFLICT (code) DO NOTHING
            """
        ),
        {"code": code, "name": name},
    )
    role_id = db_session.execute(text("SELECT id FROM roles WHERE code = :code"), {"code": code}).scalar_one()
    db_session.commit()
    return int(role_id)


def _insert_user(db_session) -> UUID:
    user_id = uuid4()
    db_session.execute(
        text(
            """
            INSERT INTO users (id, email, username, password_hash, status)
            VALUES (:id, :email, :username, :password_hash, 'active')
            """
        ),
        {
            "id": user_id,
            "email": f"{uuid4().hex}@example.com",
            "username": f"user_{uuid4().hex[:10]}",
            "password_hash": "hash",
        },
    )
    db_session.commit()
    return user_id


def _grant_role(db_session, user_id: UUID, role_id: int) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO user_roles (user_id, role_id)
            VALUES (:user_id, :role_id)
            ON CONFLICT (user_id, role_id) DO NOTHING
            """
        ),
        {"user_id": user_id, "role_id": role_id},
    )
    db_session.commit()


@pytest.mark.integration
def test_report_full_lifecycle_creates_audit_records(db_session) -> None:
    user_role_id = _ensure_role(db_session, "user", "User")
    moderator_role_id = _ensure_role(db_session, "moderator", "Moderator")
    reporter_id = _insert_user(db_session)
    moderator_id = _insert_user(db_session)
    _grant_role(db_session, reporter_id, user_role_id)
    _grant_role(db_session, moderator_id, moderator_role_id)

    repository = SqlAlchemyModerationRepository(AsyncSessionAdapter(db_session))
    use_cases = ModerationReportUseCases(repository=repository)

    report = run_async(
        use_cases.create_report(
            reporter_id,
            target_type="track",
            target_id=uuid4(),
            reason="Inappropriate content in track description",
        )
    )
    first_update = run_async(use_cases.set_report_status(moderator_id, report_id=report.id, target_status="in_review"))
    second_update = run_async(use_cases.set_report_status(moderator_id, report_id=report.id, target_status="resolved"))
    db_session.commit()

    assert first_update.report.status == "in_review"
    assert second_update.report.status == "resolved"

    audit_rows = db_session.execute(
        text(
            """
            SELECT action, metadata
            FROM moderation_actions
            WHERE target_type = 'report' AND target_id = :target_id
            ORDER BY created_at ASC
            """
        ),
        {"target_id": report.id},
    ).all()

    assert len(audit_rows) == 2
    assert audit_rows[0].action == "report_status_updated"
    assert audit_rows[0].metadata["new_status"] == "in_review"
    assert audit_rows[1].metadata["new_status"] == "resolved"
