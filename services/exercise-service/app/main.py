from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlmodel import Session

from app.auth_routes import router as auth_router
from app.db import engine, init_db
from app.routes import router
from app.seed import seed_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as session:
        seed_all(session)
    yield


app = FastAPI(title="Workout Exercise Catalog API", lifespan=lifespan)
app.include_router(router)
app.include_router(auth_router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Workout Exercise Catalog API"}
