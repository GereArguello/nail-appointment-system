from sqlmodel import Session, select

from app.core.config import settings
from app.core.enums import RoleEnum, StatusEnum
from app.core.security import password_hash
from app.users.models import User


def create_initial_admin(session: Session) -> None:
    email = settings.initial_admin_email
    password = settings.initial_admin_password

    if not email or not password:
        return

    existing_user = session.exec(select(User).where(User.email == email)).first()

    if existing_user:
        return

    admin = User(
        first_name="Admin",
        last_name="Sistema",
        email=email,
        password_hash=password_hash.hash(password),
        role=RoleEnum.ADMIN,
        status=StatusEnum.ACTIVE,
        email_verified=True,
    )

    session.add(admin)
    session.commit()
