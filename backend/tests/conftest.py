"""Fixtures. Os testes rodam contra um banco proprio (vip_test) e o Redis db 15."""

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ---- ambiente de teste: definido ANTES de importar a aplicacao ----------------------
_dev_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://vip:vip@db:5432/vip")
TEST_DB = "vip_test"
TEST_URL = _dev_url.rsplit("/", 1)[0] + "/" + TEST_DB
os.environ.update(
    {
        "DATABASE_URL": TEST_URL,
        "REDIS_URL": os.environ.get("REDIS_URL", "redis://redis:6379/0").rsplit("/", 1)[0] + "/15",
        "ENVIRONMENT": "development",
        "META_MOCK_MODE": "true",
        "SEED_DEMO": "false",
        "LOG_LEVEL": "WARNING",
        "COOKIE_SECURE": "false",
        "RATE_LIMIT_MULTIPLIER": "1000",
        "UPLOAD_DIR": tempfile.mkdtemp(prefix="vip-uploads-"),
        "APP_URL": "http://localhost:3000",
        "ALLOWED_ORIGINS": "http://localhost:3000",
    }
)


def _prepare_database() -> None:
    import asyncpg

    admin = (
        _dev_url.replace("postgresql+asyncpg://", "postgresql://").rsplit("/", 1)[0] + "/postgres"
    )

    async def go() -> None:
        conn = await asyncpg.connect(admin)
        try:
            await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
            await conn.execute(f'CREATE DATABASE "{TEST_DB}"')
        finally:
            await conn.close()

    asyncio.run(go())
    root = Path(__file__).resolve().parent.parent
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=root,
        env=os.environ.copy(),
        check=True,
    )


_prepare_database()

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.db import engine  # noqa: E402
from app.core.redis import get_redis  # noqa: E402
from app.main import app  # noqa: E402

TABLES = (
    "notifications, point_transactions, redemptions, rewards, interactions, campaigns, "
    "memberships, promoter_profiles, instagram_accounts, organizations, refresh_tokens, users"
)


class FakeArq:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict]] = []

    async def enqueue_job(self, name: str, payload: dict):
        self.jobs.append((name, payload))


@pytest_asyncio.fixture(autouse=True)
async def clean_state():
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    await get_redis().flushdb()
    from app.core import rate_limit

    rate_limit._mem.clear()
    app.state.arq = FakeArq()
    yield


@pytest.fixture
def arq() -> FakeArq:
    return app.state.arq


def make_client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )


@pytest_asyncio.fixture
async def client():
    async with make_client() as c:
        yield c


@pytest_asyncio.fixture
async def anon():
    """Cliente sem cookies e sem cabecalho CSRF."""
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as c:
        yield c
