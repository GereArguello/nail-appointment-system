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


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciales inválidas",
    headers={"WWW-Authenticate": "Bearer"},
)


def authenticate_user(token: str, session: Session) -> User:
    """Autentica un usuario a partir de un token de acceso.

    Valida que el token sea de acceso, que contenga un identificador
    de usuario válido y que el usuario exista y permanezca activo.

    Lanza 401 si las credenciales no son válidas.
    """
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise credentials_exception

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise credentials_exception from None

    user = cast(User | None, session.get(User, user_id))

    if user is None or user.status == StatusEnum.INACTIVE:
        raise credentials_exception

    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    """Obtiene el usuario autenticado a partir de un token de acceso válido."""
    return authenticate_user(token, session)


def get_current_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Obtiene el usuario autenticado si posee el rol de administrador."""
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
    """Obtiene el usuario autenticado cuando hay credenciales disponibles.

    Retorna None si no se proporciona un token.
    Lanza 401 si se proporcionan credenciales inválidas.
    """
    if token is None:
        return None

    return authenticate_user(token, session)
