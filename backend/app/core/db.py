from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.rls import RlsSession

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_timeout=30,
    connect_args={"server_settings": {"statement_timeout": "30000", "application_name": "vip"}},
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, sync_session_class=RlsSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
