from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.schemas import Token
from app.auth.service import authenticate_user, generate_auth_token
from app.core.database import SessionDep

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token, status_code=status.HTTP_200_OK, summary="")
def login(
    session: SessionDep, form_data: OAuth2PasswordRequestForm = Depends()
) -> Token:

    email = form_data.username.strip().lower()

    user = authenticate_user(session=session, email=email, password=form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="El usuario no tiene un ID válido",
        )

    access_token = generate_auth_token(user.id)

    return Token(
        access_token=access_token,
        token_type="bearer",  # noqa: S106
    )
