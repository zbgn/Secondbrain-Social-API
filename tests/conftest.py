import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-bytes")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

from app.database import get_db
from app.models import Base
from main import create_app


@pytest.fixture
def db_session(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create_tables())
    yield TestingSessionLocal
    asyncio.run(engine.dispose())


@pytest.fixture
def client(db_session):
    app = create_app()

    async def override_get_db():
        async with db_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
