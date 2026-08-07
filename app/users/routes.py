from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionDep
from app.core.security import password_hash
from app.users.models import User
from app.users.schemas import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/", response_model=UserRead, status_code=status.HTTP_201_CREATED, summary=""
)
def create_user(user: UserCreate, session: SessionDep) -> UserRead:
    data = user.model_dump(exclude={"password1", "password2"})

    db_user = User(
        **data,
        password_hash=password_hash.hash(user.password1),
    )

    try:
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con este email",
        ) from exc

    response: UserRead = UserRead.model_validate(db_user)
    return response
