from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.application.identity.use_cases.profiles import (
    COMPOSER_PROFILE_TYPE,
    IdentityProfilesUseCases,
)
from backend.infrastructure.persistence.repositories.identity_auth import (
    SqlAlchemyIdentityAuthRepository,
)
from tests.async_tools import AsyncSessionAdapter, run_async


@pytest.mark.integration
def test_composer_profiles_unique_user_id_constraint(db_session) -> None:
    user_id = uuid4()
    db_session.execute(
        text(
            """
            INSERT INTO users (id, email, username, password_hash, status)
            VALUES (:id, :email, :username, :password_hash, :status)
            """
        ),
        {
            "id": user_id,
            "email": f"{uuid4().hex}@example.com",
            "username": f"user_{uuid4().hex[:10]}",
            "password_hash": "hash",
            "status": "active",
        },
    )
    db_session.commit()

    db_session.execute(
        text(
            """
            INSERT INTO composer_profiles (id, user_id, display_name, bio, country_code, verified)
            VALUES (:id, :user_id, :display_name, :bio, :country_code, :verified)
            """
        ),
        {
            "id": uuid4(),
            "user_id": user_id,
            "display_name": "Composer One",
            "bio": "Bio",
            "country_code": "US",
            "verified": False,
        },
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO composer_profiles (id, user_id, display_name, bio, country_code, verified)
                VALUES (:id, :user_id, :display_name, :bio, :country_code, :verified)
                """
            ),
            {
                "id": uuid4(),
                "user_id": user_id,
                "display_name": "Composer Two",
                "bio": "Another bio",
                "country_code": "DE",
                "verified": False,
            },
        )
        db_session.commit()
    db_session.rollback()


@pytest.mark.integration
def test_user_role_profiles_profile_type_check_constraint(db_session) -> None:
    user_id = uuid4()
    role_id = db_session.execute(text("SELECT id FROM roles WHERE code = 'composer'")).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO users (id, email, username, password_hash, status)
            VALUES (:id, :email, :username, :password_hash, :status)
            """
        ),
        {
            "id": user_id,
            "email": f"{uuid4().hex}@example.com",
            "username": f"user_{uuid4().hex[:10]}",
            "password_hash": "hash",
            "status": "active",
        },
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO user_role_profiles (id, user_id, role_id, profile_type, profile_id)
                VALUES (:id, :user_id, :role_id, :profile_type, :profile_id)
                """
            ),
            {
                "id": uuid4(),
                "user_id": user_id,
                "role_id": role_id,
                "profile_type": "invalid_profile",
                "profile_id": uuid4(),
            },
        )
        db_session.commit()
    db_session.rollback()


@pytest.mark.integration
def test_update_profile_syncs_user_role_profiles_link(db_session) -> None:
    repository = SqlAlchemyIdentityAuthRepository(AsyncSessionAdapter(db_session))
    user = run_async(
        repository.create_user(
            email=f"{uuid4().hex}@example.com",
            username=f"user_{uuid4().hex[:10]}",
            password_hash="hash",
        )
    )
    run_async(repository.ensure_roles_seeded())
    composer_role_id = run_async(repository.get_role_id_by_code("composer"))
    assert composer_role_id is not None
    run_async(repository.assign_role(user.id, composer_role_id))
    db_session.commit()

    use_cases = IdentityProfilesUseCases(repository=repository)
    profile_result = run_async(
        use_cases.update_my_profile(
            user.id,
            display_name="Composer Profile",
            bio="Bio",
            country_code="UA",
        )
    )
    db_session.commit()

    row = (
        db_session.execute(
            text(
                """
            SELECT role_id, profile_type, profile_id
            FROM user_role_profiles
            WHERE user_id = :user_id
            """
            ),
            {"user_id": user.id},
        )
        .mappings()
        .one()
    )

    assert int(row["role_id"]) == composer_role_id
    assert row["profile_type"] == COMPOSER_PROFILE_TYPE
    assert str(row["profile_id"]) == str(profile_result.composer_profile.id)
