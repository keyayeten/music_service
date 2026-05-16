from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from backend.domain.common.exceptions import AuthenticationError

_JWT_HEADER = {"alg": "HS256", "typ": "JWT"}
_PBKDF2_ITERATIONS = 120_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt_hex, digest_hex = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
    except (TypeError, ValueError):
        return False

    current_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(current_digest, expected_digest)


def issue_token_pair(
    user_id: UUID,
    secret: str,
    access_ttl_minutes: int,
    refresh_ttl_minutes: int,
) -> dict[str, str | int]:
    access_exp = datetime.now(tz=UTC) + timedelta(minutes=access_ttl_minutes)
    refresh_exp = datetime.now(tz=UTC) + timedelta(minutes=refresh_ttl_minutes)

    access_token = encode_jwt(
        {
            "sub": str(user_id),
            "type": "access",
            "iat": _unix_now(),
            "exp": int(access_exp.timestamp()),
            "jti": str(uuid4()),
        },
        secret,
    )
    refresh_token = encode_jwt(
        {
            "sub": str(user_id),
            "type": "refresh",
            "iat": _unix_now(),
            "exp": int(refresh_exp.timestamp()),
            "jti": str(uuid4()),
        },
        secret,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "access_expires_in": access_ttl_minutes * 60,
        "refresh_expires_in": refresh_ttl_minutes * 60,
    }


def decode_jwt(token: str, secret: str) -> dict[str, object]:
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthenticationError("Invalid token.")

    header_segment, payload_segment, signature_segment = parts
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    expected_signature = _sign(signing_input, secret)
    if not hmac.compare_digest(signature_segment, expected_signature):
        raise AuthenticationError("Invalid token signature.")

    try:
        payload_raw = _base64_url_decode(payload_segment)
        payload = json.loads(payload_raw)
    except (ValueError, json.JSONDecodeError) as exc:
        raise AuthenticationError("Invalid token payload.") from exc

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp <= _unix_now():
        raise AuthenticationError("Token is expired.")
    return payload


def encode_jwt(payload: dict[str, object], secret: str) -> str:
    header_segment = _base64_url_encode(json.dumps(_JWT_HEADER, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    payload_segment = _base64_url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature_segment = _sign(signing_input, secret)
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def _sign(signing_input: bytes, secret: str) -> str:
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return _base64_url_encode(signature)


def _base64_url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _base64_url_decode(raw: str) -> bytes:
    padding = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("ascii"))


def _unix_now() -> int:
    return int(datetime.now(tz=UTC).timestamp())
