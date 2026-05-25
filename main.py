from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import engine
from app.models import Base
from app.routes import router
from app.security import get_secret_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_secret_key()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Secondbrain Social API", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
