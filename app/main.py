from fastapi import FastAPI

from app.auth import routes as auth_router
from app.calendar_blocks import routes as calendar_blocks_router
from app.services import routes as services_router
from app.users import routes as users_router
from app.working_hours import routes as working_hours_router

app = FastAPI()

app.include_router(users_router.router)
app.include_router(auth_router.router)
app.include_router(services_router.router)
app.include_router(working_hours_router.router)
app.include_router(calendar_blocks_router.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"Hello": "World"}
