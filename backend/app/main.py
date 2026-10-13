import logging
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.gzip import GZipMiddleware

from app.core.config import settings, validate_production
from app.core.db import engine
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.core.middleware import BodyLimitMiddleware, CSRFMiddleware, SecurityHeadersMiddleware
from app.core.redis import close_redis

log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.arq = None
    # RLS so vale se o app NAO conecta como superusuario/dono: em producao, recusa subir.
    from app.core.db import SessionLocal
    from app.core.rls import check_database_role

    async with SessionLocal() as db:
        await check_database_role(db, strict=settings.is_production)
    try:
        app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    except Exception:
        log.exception("fila arq indisponivel", extra={"event": "arq_pool"})
    if settings.seed_demo and not settings.is_production:
        from app.seed import run_seed

        try:
            await run_seed()
        except Exception:
            log.exception("seed falhou", extra={"event": "seed"})
    yield
    if app.state.arq is not None:
        await app.state.arq.aclose()
    from app.services.instagram import close_instagram_client

    await close_instagram_client()
    await close_redis()
    await engine.dispose()


def _operation_id(route: APIRoute) -> str:
    return route.name


def create_app() -> FastAPI:
    validate_production(settings)
    setup_logging()
    prod = settings.is_production
    app = FastAPI(
        title="VIP Promoters API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if prod else "/docs",
        redoc_url=None,
        openapi_url=None if prod else "/openapi.json",
        generate_unique_id_function=_operation_id,
    )
    register_error_handlers(app)

    from app.api.v1 import (
        auth,
        campaigns,
        dev,
        instagram,
        misc,
        promoter,
        shop,
        team,
        uploads,
        webhooks,
    )

    api = APIRouter(prefix="/api/v1")
    for module in (misc, auth, team, instagram, campaigns, uploads, shop, webhooks):
        api.include_router(module.router)
    api.include_router(promoter.router)
    api.include_router(promoter.public_router)
    if settings.meta_mock_mode:
        api.include_router(dev.router)  # rotas /dev/* so existem em modo mock
    app.include_router(api)

    # Ordem: o ultimo adicionado e o mais externo.
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    return app


app = create_app()
