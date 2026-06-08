from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.application.identity.security import hash_password


@pytest.mark.unit
def test_admin_auth_login_succeeds_for_superuser(db_session, admin_enabled_app) -> None:
    email = f"super_{uuid4().hex}@example.com"
    password = "SuperSecure1!"
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
            "username": f"super_{uuid4().hex[:10]}",
            "password_hash": hash_password(password),
        },
    )
    db_session.commit()

    with TestClient(admin_enabled_app) as client:
        response = client.post(
            "/admin/login", data={"username": email, "password": password}, follow_redirects=False
        )
        assert response.status_code in {302, 303, 307}
        client.cookies.update(response.cookies)
        assert client.get("/admin/").status_code == 200


@pytest.mark.unit
def test_admin_auth_login_rejects_non_superuser(db_session, admin_enabled_app) -> None:
    email = f"user_{uuid4().hex}@example.com"
    password = "RegularPass1!"
    db_session.execute(
        text(
            """
            INSERT INTO users (id, email, username, password_hash, is_superuser, status)
            VALUES (:id, :email, :username, :password_hash, false, 'active')
            """
        ),
        {
            "id": uuid4(),
            "email": email,
            "username": f"user_{uuid4().hex[:10]}",
            "password_hash": hash_password(password),
        },
    )
    db_session.commit()

    with TestClient(admin_enabled_app) as client:
        response = client.post(
            "/admin/login", data={"username": email, "password": password}, follow_redirects=False
        )
        assert response.status_code == 400


@pytest.mark.unit
def test_admin_auth_login_rejects_wrong_password(db_session, admin_enabled_app) -> None:
    email = f"super2_{uuid4().hex}@example.com"
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
            "username": f"super2_{uuid4().hex[:10]}",
            "password_hash": hash_password("CorrectPass1!"),
        },
    )
    db_session.commit()

    with TestClient(admin_enabled_app) as client:
        response = client.post(
            "/admin/login",
            data={"username": email, "password": "WrongPass1!"},
            follow_redirects=False,
        )
        assert response.status_code == 400
