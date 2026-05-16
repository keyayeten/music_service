from uuid import uuid4

import pytest

from backend.application.identity.security import decode_jwt, hash_password, issue_token_pair, verify_password
from backend.domain.common.exceptions import AuthenticationError


@pytest.mark.unit
def test_password_hash_roundtrip() -> None:
    password = "VeryStrongPassword123!"
    encoded = hash_password(password)
    assert verify_password(password, encoded) is True
    assert verify_password("wrong-password", encoded) is False


@pytest.mark.unit
def test_refresh_token_can_be_decoded() -> None:
    pair = issue_token_pair(
        user_id=uuid4(),
        secret="unit-test-secret",
        access_ttl_minutes=15,
        refresh_ttl_minutes=60,
    )
    payload = decode_jwt(pair["refresh_token"], "unit-test-secret")
    assert payload["type"] == "refresh"
    assert isinstance(payload["sub"], str)


@pytest.mark.unit
def test_decode_jwt_rejects_invalid_signature() -> None:
    pair = issue_token_pair(
        user_id=uuid4(),
        secret="unit-test-secret",
        access_ttl_minutes=15,
        refresh_ttl_minutes=60,
    )
    with pytest.raises(AuthenticationError):
        decode_jwt(pair["access_token"], "another-secret")
