from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import get_current_user
from app.core.database import SessionDep
from app.core.security import password_hash
from app.users.models import User
from app.users.schemas import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
)
def create_user(user: UserCreate, session: SessionDep) -> UserRead:
    """Registra un nuevo usuario.

    El correo electrónico debe ser único.
    """
    data = user.model_dump(exclude={"password", "password2"})

    db_user = User(
        **data,
        password_hash=password_hash.hash(user.password),
    )

    try:
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya está registrado",
        ) from exc

    response: UserRead = UserRead.model_validate(db_user)
    return response


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener usuario actual",
)
def read_me(current_user: User = Depends(get_current_user)) -> UserRead:
    """Obtiene la información del usuario autenticado."""
    return current_user
