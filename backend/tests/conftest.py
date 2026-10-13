"""Fixtures. Os testes rodam contra um banco proprio (vip_test) e o Redis db 15."""

import asyncio
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

# ---- ambiente de teste: definido ANTES de importar a aplicacao ----------------------
# DATABASE_URL_ADMIN (ou, na falta, DATABASE_URL) e um papel que cria bancos e papeis. O app
# roda nos testes com o PAPEL DE APLICACAO, como em producao: o RLS vale de verdade aqui.
_admin_url = os.environ.get("DATABASE_URL_ADMIN") or os.environ.get("DATABASE_URL")
if not _admin_url:
    raise RuntimeError(
        "Defina DATABASE_URL_ADMIN (um usuario do Postgres que cria bancos e papeis) "
        "para rodar os testes."
    )
TEST_DB = "vip_test"
# Papel PROPRIO dos testes: papeis valem para o servidor inteiro, e reaproveitar o vip_app
# trocaria a senha do papel que o app de desenvolvimento usa no mesmo Postgres.
APP_DB_USER = os.environ.get("TEST_APP_DB_USER", "vip_test_app")
# senha nova a cada execucao: o papel e recriado pelo preparar-banco logo abaixo
APP_DB_PASSWORD = os.environ.get("TEST_APP_DB_PASSWORD") or secrets.token_hex(16)
_server = _admin_url.split("@", 1)[1].rsplit("/", 1)[0]
TEST_ADMIN_URL = _admin_url.rsplit("/", 1)[0] + "/" + TEST_DB
TEST_URL = f"postgresql+asyncpg://{APP_DB_USER}:{APP_DB_PASSWORD}@{_server}/{TEST_DB}"
os.environ.update(
    {
        "DATABASE_URL": TEST_URL,
        "DATABASE_URL_ADMIN": TEST_ADMIN_URL,
        "APP_DB_USER": APP_DB_USER,
        "APP_DB_PASSWORD": APP_DB_PASSWORD,
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
        _admin_url.replace("postgresql+asyncpg://", "postgresql://").rsplit("/", 1)[0] + "/postgres"
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
    # o mesmo comando do deploy: migracoes + papel de aplicacao
    subprocess.run(
        [sys.executable, "-m", "app.cli", "preparar-banco"],
        cwd=root,
        env=os.environ.copy(),
        check=True,
        stdout=subprocess.DEVNULL,
    )


_prepare_database()

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.redis import get_redis  # noqa: E402
from app.main import app  # noqa: E402

TABLES = (
    "username_claims, data_deletion_requests, notifications, point_transactions, redemptions, rewards, interactions, campaigns, "
    "memberships, promoter_profiles, instagram_accounts, organizations, refresh_tokens, users"
)


class FakeArq:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict]] = []

    async def enqueue_job(self, name: str, payload: dict):
        self.jobs.append((name, payload))


# TRUNCATE e privilegio do dono das tabelas, nunca do papel de aplicacao
admin_engine = create_async_engine(TEST_ADMIN_URL)


@pytest_asyncio.fixture(autouse=True)
async def clean_state():
    async with admin_engine.begin() as conn:
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
