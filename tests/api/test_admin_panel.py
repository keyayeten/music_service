from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.application.identity.security import hash_password


@pytest.mark.api
def test_admin_panel_requires_login_when_enabled(db_session, admin_enabled_app) -> None:
    email = f"admin_panel_{uuid4().hex}@example.com"
    password = "AdminPanel1!"
    db_session.execute(
        text(
            """
            INSERT INTO users (id, email, username, password_hash, is_superuser, status)
            VALUES (:id, :email, :username, :password_hash, true, 'active')
            """
        ),
        {
            "id": uuid4(),
            "email": email,
            "username": f"admin_panel_{uuid4().hex[:10]}",
            "password_hash": hash_password(password),
        },
    )
    db_session.commit()

    with TestClient(admin_enabled_app) as client:
        response = client.get("/admin/", follow_redirects=False)
        assert response.status_code in {302, 307}
        assert "login" in response.headers.get("location", "").lower()

        login_response = client.post(
            "/admin/login",
            data={"username": email, "password": password},
            follow_redirects=False,
        )
        assert login_response.status_code in {302, 303, 307}
        client.cookies.update(login_response.cookies)
        assert client.get("/admin/").status_code == 200
