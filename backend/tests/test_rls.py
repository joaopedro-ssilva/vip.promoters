"""Row Level Security: a segunda camada do isolamento entre organizacoes.

Estes testes simulam o BUG que o RLS existe para conter: uma consulta que esquece o filtro
por organizacao. Rodam com o papel de aplicacao (conftest), como em producao."""

import uuid

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rls
from app.core.db import SessionLocal, engine
from app.models import Campaign, Interaction, Membership, Organization, Reward
from tests.conftest import admin_engine
from tests.helpers import new_manager, new_promoter
from tests.test_rewards import make_reward

API = "/api/v1"


async def two_orgs():
    a = await new_manager()
    b = await new_manager()
    pa = await new_promoter(a)
    pb = await new_promoter(b)
    ca = await a.campaign()
    cb = await b.campaign()
    await a.simulate_comment(ca["id"], pa.username)
    await b.simulate_comment(cb["id"], pb.username)
    await make_reward(a)
    await make_reward(b)
    return a, b, pa, pb


def uid(x: str) -> uuid.UUID:
    return uuid.UUID(x)


async def test_app_role_is_not_privileged():
    async with SessionLocal() as db:
        assert await rls.check_database_role(db, strict=True) == []
    # o dono das tabelas (admin) e recusado em producao
    async with AsyncSession(admin_engine) as db:
        with pytest.raises(RuntimeError):
            await rls.check_database_role(db, strict=True)


async def test_query_without_org_filter_only_sees_own_tenant():
    a, b, pa, _ = await two_orgs()
    async with SessionLocal() as db:
        await rls.set_tenant(db, uid(a.user["id"]), [uid(a.org["id"])])
        # consultas SEM where de organizacao (o bug que o RLS contem)
        for model in (Campaign, Interaction, Reward, Membership, Organization):
            orgs = {
                str(getattr(r, "organization_id", None) or r.id)
                for r in (await db.execute(select(model))).scalars()
            }
            assert orgs == {a.org["id"]}, model.__tablename__

        # modo sistema (worker, webhooks) enxerga tudo
        async with rls.system(db):
            total = await db.scalar(select(func.count()).select_from(Campaign))
            assert total == 2
        # e o contexto do tenant volta ao sair do bloco
        assert await db.scalar(select(func.count()).select_from(Campaign)) == 1


async def test_promoter_context_sees_only_own_teams_and_memberships():
    a, b, pa, pb = await two_orgs()
    async with SessionLocal() as db:
        await rls.set_tenant(db, uid(pa.user["id"]), [uid(a.org["id"])])
        mems = (await db.execute(select(Membership))).scalars().all()
        assert {str(m.organization_id) for m in mems} == {a.org["id"]}
        assert await db.scalar(select(func.count()).select_from(Interaction)) == 1


async def test_cannot_write_into_another_tenant():
    a, b, *_ = await two_orgs()
    async with SessionLocal() as db:
        await rls.set_tenant(db, uid(a.user["id"]), [uid(a.org["id"])])
        db.add(Reward(organization_id=uid(b.org["id"]), name="Invasao", cost_points=1, stock=None))
        with pytest.raises(DBAPIError) as exc:
            await db.flush()
        assert "row-level security" in str(exc.value).lower()
        await db.rollback()

    # UPDATE/DELETE sem filtro so alcancam o proprio tenant
    async with SessionLocal() as db:
        await rls.set_tenant(db, uid(a.user["id"]), [uid(a.org["id"])])
        res = await db.execute(text("UPDATE rewards SET name = 'mexido'"))
        assert res.rowcount == 1
        await db.commit()
    async with SessionLocal() as db:
        names = dict((await db.execute(select(Reward.organization_id, Reward.name))).all())
        assert names[uid(a.org["id"])] == "mexido"
        assert names[uid(b.org["id"])] != "mexido"


async def test_connection_without_context_sees_nothing():
    """Fora da sessao (conexao crua, sem set_config), as policies fecham tudo."""
    await two_orgs()
    async with engine.connect() as conn:
        assert (await conn.execute(text("SELECT count(*) FROM campaigns"))).scalar() == 0
        assert (await conn.execute(text("SELECT count(*) FROM organizations"))).scalar() == 0


async def test_context_never_leaks_between_transactions():
    """set_config local a transacao: o contexto de uma requisicao nao sobra no pool."""
    a, b, *_ = await two_orgs()
    async with SessionLocal() as db:
        await rls.set_tenant(db, uid(a.user["id"]), [uid(a.org["id"])])
        assert await db.scalar(select(func.count()).select_from(Campaign)) == 1
        await db.commit()
    async with engine.connect() as conn:
        mode = (await conn.execute(text("SELECT current_setting('app.rls_mode', true)"))).scalar()
        assert mode in (None, "")


async def _buggy_route_total(client) -> int:
    """Rota de teste escrita com o BUG: lista recompensas sem filtrar por organizacao."""
    from app.api.deps import DB, Manager
    from app.main import app

    async def buggy(ctx: Manager, db: DB):  # noqa: ARG001
        return {"total": await db.scalar(select(func.count()).select_from(Reward))}

    app.add_api_route("/api/v1/_teste/buggy", buggy, methods=["GET"])
    try:
        r = await client.get(f"{API}/_teste/buggy")
        assert r.status_code == 200, r.text
        return r.json()["total"]
    finally:
        app.router.routes = [
            rt for rt in app.router.routes if getattr(rt, "path", "") != "/api/v1/_teste/buggy"
        ]


async def test_http_route_without_org_filter_stays_isolated():
    """Ponta a ponta: uma rota nova que esquece o filtro de organizacao nao vaza dados."""
    a, *_ = await two_orgs()
    assert await _buggy_route_total(a.client) == 1


async def test_http_route_without_org_filter_leaks_if_rls_is_off(monkeypatch):
    """Controle do teste acima: sem o contexto de tenant, a mesma rota vaza as duas."""
    a, *_ = await two_orgs()

    async def no_tenant(*args, **kwargs):
        return None

    monkeypatch.setattr(rls, "set_tenant", no_tenant)
    assert await _buggy_route_total(a.client) == 2
