from fastapi import FastAPI

from app.auth import routes as auth_router
from app.users import routes as users_router

app = FastAPI()

app.include_router(users_router.router)
app.include_router(auth_router.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"Hello": "World"}
