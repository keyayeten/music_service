from uuid import uuid4

import pytest
from sqlalchemy import text


def _signup(client) -> dict:
    marker = uuid4().hex[:10]
    payload = {
        "email": f"{marker}@example.com",
        "username": f"user_{marker}",
        "password": "StrongPassword123!",
    }
    response = client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201
    return response.json()


def _grant_role(db_session, user_id: str, role_code: str) -> None:
    role_id = db_session.execute(
        text("SELECT id FROM roles WHERE code = :code"), {"code": role_code}
    ).scalar_one()
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


@pytest.mark.api
def test_reports_full_api_flow_for_user_and_moderator(client, db_session, redis_client) -> None:
    regular_user = _signup(client)
    user_id = regular_user["user"]["id"]
    user_access = regular_user["tokens"]["access_token"]

    create_response = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {user_access}"},
        json={
            "target_type": "track",
            "target_id": str(uuid4()),
            "reason": "Spam links in track metadata",
        },
    )
    assert create_response.status_code == 201
    report_id = create_response.json()["id"]
    assert create_response.json()["status"] == "open"
    assert create_response.json()["reporter_user_id"] == user_id

    forbidden_list_response = client.get(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {user_access}"},
    )
    assert forbidden_list_response.status_code == 403
    assert forbidden_list_response.json()["detail"]["code"] == "authorization_error"

    moderator_user = _signup(client)
    moderator_id = moderator_user["user"]["id"]
    moderator_access = moderator_user["tokens"]["access_token"]
    _grant_role(db_session, moderator_id, "moderator")

    list_response = client.get(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {moderator_access}"},
        params={"status": "open"},
    )
    assert list_response.status_code == 200
    assert any(item["id"] == report_id for item in list_response.json()["items"])

    detail_response = client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {moderator_access}"},
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == report_id

    in_review_response = client.post(
        f"/api/v1/reports/{report_id}/status",
        headers={"Authorization": f"Bearer {moderator_access}"},
        json={"status": "in_review"},
    )
    assert in_review_response.status_code == 200
    assert in_review_response.json()["status"] == "in_review"

    resolved_response = client.post(
        f"/api/v1/reports/{report_id}/status",
        headers={"Authorization": f"Bearer {moderator_access}"},
        json={"status": "resolved"},
    )
    assert resolved_response.status_code == 200
    assert resolved_response.json()["status"] == "resolved"


@pytest.mark.api
def test_reports_create_requires_authentication(client, db_session, redis_client) -> None:
    response = client.post(
        "/api/v1/reports",
        json={
            "target_type": "comment",
            "target_id": str(uuid4()),
            "reason": "Offensive language",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "authentication_error"
