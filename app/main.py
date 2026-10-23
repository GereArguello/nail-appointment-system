from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.appointments import routes as appointment_router
from app.auth import routes as auth_router
from app.business_settings import routes as business_settings_router
from app.calendar_blocks import routes as calendar_blocks_router
from app.core.bootstrap import create_initial_admin
from app.core.config import settings
from app.core.database import engine
from app.services import routes as services_router
from app.users import routes as users_router
from app.working_hours import routes as working_hours_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    if settings.ENVIRONMENT == "development":
        with Session(engine) as session:
            create_initial_admin(session)

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(business_settings_router.router)
app.include_router(users_router.router)
app.include_router(auth_router.router)
app.include_router(services_router.router)
app.include_router(working_hours_router.router)
app.include_router(calendar_blocks_router.router)
app.include_router(appointment_router.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"Hello": "World"}
