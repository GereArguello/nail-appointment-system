from datetime import timedelta
from typing import cast

from sqlmodel import Session, select

from app.core.config import settings
from app.core.enums import StatusEnum
from app.core.security import create_access_token, password_hash
from app.users.models import User


def get_user_by_email(session: Session, email: str) -> User | None:
    """Busca un usuario por su correo electrónico."""
    return cast(
        User | None, session.exec(select(User).where(User.email == email)).first()
    )


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    """Autentica un usuario mediante correo electrónico y contraseña.

    Retorna None si el usuario no existe, está inactivo o la contraseña
    proporcionada es incorrecta.
    """
    user = get_user_by_email(session, email)

    if not user:
        return None

    if user.status == StatusEnum.INACTIVE:
        return None

    if not password_hash.verify(password, user.password_hash):
        return None

    return user


def generate_auth_token(user_id: int) -> str:
    """Genera un token de acceso para el usuario indicado."""
    return create_access_token(
        data={"sub": str(user_id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
