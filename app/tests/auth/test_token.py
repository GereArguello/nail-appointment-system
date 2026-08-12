from datetime import timedelta

import pytest
from fastapi import HTTPException, status

from app.core.security import create_access_token, decode_token


def test_access_token_contains_expected_claims() -> None:
    token = create_access_token(
        data={"sub": "123"},
        expires_delta=timedelta(minutes=30),
    )

    payload = decode_token(token)

    assert payload["sub"] == "123"
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload


def test_access_token_jti_is_unique() -> None:
    token1 = create_access_token(
        data={"sub": "123"},
        expires_delta=timedelta(minutes=30),
    )

    token2 = create_access_token(
        data={"sub": "123"},
        expires_delta=timedelta(minutes=30),
    )

    payload1 = decode_token(token1)
    payload2 = decode_token(token2)

    assert payload1["jti"] != payload2["jti"]


def test_decode_invalid_token() -> None:
    with pytest.raises(HTTPException) as exc_info:
        decode_token("invalid-token")

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Token inválido o expirado"


def test_decode_expired_token() -> None:
    token = create_access_token(
        data={"sub": "123"},
        expires_delta=timedelta(seconds=-1),
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "Token inválido o expirado"


def test_access_token_preserves_subject() -> None:
    token = create_access_token(
        data={"sub": "999"},
        expires_delta=timedelta(minutes=30),
    )

    payload = decode_token(token)

    assert payload["sub"] == "999"
