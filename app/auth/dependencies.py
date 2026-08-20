from typing import cast

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.database import get_session
from app.core.enums import RoleEnum, StatusEnum
from app.core.security import decode_token
from app.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        ) from None

    user = cast(User | None, session.get(User, user_id))

    if user is None or user.status == StatusEnum.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    return user


def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    if user.role is not RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta acción",
        )

    return user


def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    session: Session = Depends(get_session),
) -> User | None:
    if not token:
        return None

    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        return None

    user = cast(User | None, session.get(User, int(user_id)))

    if not user or user.status == StatusEnum.INACTIVE:
        return None

    return user
