from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

from fastapi import HTTPException, status
from jose import jwt
from jose.exceptions import JWTError
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    issued_at = datetime.now(UTC)
    expire = issued_at + expires_delta
    to_encode.update(
        {"exp": expire, "iat": issued_at, "jti": str(uuid4()), "type": "access"}
    )

    return cast(
        str, jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = cast(
            dict[str, Any],
            jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]),
        )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado"
        ) from exc
