"""Correcoes da auditoria externa (itens numerados conforme o relatorio)."""

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from arq import Retry
from arq.connections import RedisSettings
from arq.worker import Worker, func
from httpx import AsyncClient
from sqlalchemy import func as sa_func
from sqlalchemy import select, update
from starlette.requests import Request

from app import worker as worker_mod
from app.core import rate_limit, sessions
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.logging import setup_logging
from app.core.redis import get_redis
from app.models import (
    Campaign,
    InstagramAccount,
    Interaction,
    Membership,
    PromoterProfile,
    RefreshToken,
)
from app.services import interactions as pipeline
from app.services.instagram.base import InstagramError
from app.services.instagram.mock import MockInstagramClient
from app.services.interactions import InboundEvent, TransientPipelineError, process_event
from app.services.webhooks import sanitize_payload
from tests.conftest import make_client
from tests.helpers import (
    PASSWORD,
    comment_payload,
    cookie_from,
    error_code,
    new_manager,
    new_promoter,
    story_payload,
)

API = "/api/v1"


def event(account_ig_id, media_id, event_id, username, **kw) -> InboundEvent:
    return InboundEvent(
        type="comment",
        ig_event_id=event_id,
        account_ig_id=account_ig_id,
        occurred_at=kw.pop("occurred_at", datetime.now(UTC)),
        from_id=f"mock_{username}",
        from_username=username,
        media_id=media_id,
        text="oi",
        **kw,
    )


def story_event(account_ig_id, mid, username, **kw) -> InboundEvent:
    return InboundEvent(
        type="story_mention",
        ig_event_id=mid,
        account_ig_id=account_ig_id,
        occurred_at=kw.pop("occurred_at", datetime.now(UTC)),
        from_id=f"mock_{username}",
        **kw,
    )


async def ig_id(m) -> str:
    return (await m.client.get(f"{API}/instagram/account")).json()["account"]["ig_user_id"]


async def run_event(ev):
    async with SessionLocal() as db:
        return await process_event(db, ev)


async def statuses(m, campaign_id, **params):
    r = await m.client.get(f"{API}/campaigns/{campaign_id}/interactions", params=params)
    return [i["status"] for i in r.json()["items"]]


# ---------------------------------------------------------------- 1. troca de @ (roubo de pontos)


async def test_1a_username_change_demotes_to_pending_and_does_not_rematch():
    m = await new_manager()
    thief = await new_promoter(m, username="ladrao.user")
    c = await m.campaign()
    victim = await m.simulate_comment(c["id"], "vitima.real")  # nao casa com ninguem
    assert victim["status"] == "unmatched"

    r = await thief.client.patch(
        f"{API}/promoter/profile", json={"instagram_username": "@Vitima.Real"}
    )
    assert r.status_code == 200
    assert r.json()["user"]["promoter_profile"]["verified"] is False
    mem = await thief.membership()
    assert mem["status"] == "pending" and mem["points_balance"] == 0
    assert await statuses(m, c["id"]) == ["unmatched"]  # nada foi creditado ao ladrao

    notes = (await m.client.get(f"{API}/notifications")).json()["items"]
    changed = [n for n in notes if n["type"] == "username_changed"]
    assert len(changed) == 1
    assert "ladrao.user" in changed[0]["body"] and "vitima.real" in changed[0]["body"]
    assert "precisa de nova aprovação" in changed[0]["body"]
    # promoter pendente nao acessa nada da equipe
    h = await thief.client.get(f"{API}/promoter/home")
    assert h.status_code == 403 and error_code(h) == "membership_not_approved"
    # so a aprovacao MANUAL do gestor religa (e e ela que dispara o re-match)
    ok = await m.client.post(f"{API}/team/members/{mem['id']}/approve")
    assert ok.status_code == 200 and ok.json()["points_balance"] == 50


async def test_1c_auto_approve_never_rematches_retroactively():
    m = await new_manager()
    c = await m.campaign()
    old = await m.simulate_comment(c["id"], "chegou.depois")
    assert old["status"] == "unmatched"
    r = await m.client.patch(f"{API}/organization", json={"auto_approve_promoters": True})
    assert r.status_code == 200
    p = await new_promoter(m, approve=False, username="chegou.depois")
    mem = await p.membership()
    assert mem["status"] == "approved"  # auto-aprovado
    assert await p.balance() == 0
    assert await statuses(m, c["id"]) == ["unmatched"]  # evento anterior nao e creditado
    # eventos POSTERIORES a entrada premiam normalmente
    new = await m.simulate_comment(c["id"], "chegou.depois", "agora sim")
    assert new["status"] == "awarded" and await p.balance() == 50


async def test_1d_pipeline_never_awards_events_before_joined_at_unless_manual():
    m = await new_manager()
    await m.client.patch(f"{API}/organization", json={"auto_approve_promoters": True})
    auto = await new_promoter(m, approve=False, username="auto.user")
    c = await m.campaign()
    acc = await ig_id(m)
    past = datetime.now(UTC) - timedelta(days=1)
    # janela da campanha cobre o passado para isolar a regra de joined_at
    async with SessionLocal() as db:
        await db.execute(
            update(Campaign)
            .where(Campaign.id == c["id"])
            .values(starts_at=past - timedelta(days=1))
        )
        await db.commit()
    res = await run_event(event(acc, c["ig_media_id"], "old_1", "auto.user", occurred_at=past))
    assert res.interaction.status == "unmatched" and await auto.balance() == 0
    # mesmo evento antigo, para quem foi aprovado manualmente: premia
    await m.client.patch(f"{API}/organization", json={"auto_approve_promoters": False})
    manual = await new_promoter(m, username="manual.user")
    res = await run_event(event(acc, c["ig_media_id"], "old_2", "manual.user", occurred_at=past))
    assert res.interaction.status == "awarded" and await manual.balance() == 50


async def test_1e_rematch_runs_in_batches_until_exhausted(monkeypatch):
    monkeypatch.setattr(pipeline, "REMATCH_BATCH", 2)
    m = await new_manager()
    c = await m.campaign()
    for i in range(5):
        await m.simulate_comment(c["id"], "em.lote", f"c{i}")
    p = await new_promoter(m, approve=False, username="em.lote")
    r = await m.client.post(f"{API}/team/members/{(await p.membership())['id']}/approve")
    assert r.status_code == 200
    got = await statuses(m, c["id"])
    assert sorted(got) == ["awarded", "duplicate", "duplicate", "duplicate", "duplicate"]
    assert await p.balance() == 50


# ---------------------------------------------------------------- 2. JWT revogavel (sid)


async def _register_manager_client() -> tuple[AsyncClient, str, str]:
    c = make_client()
    r = await c.post(
        f"{API}/auth/register",
        json={
            "name": "Ana",
            "email": f"sid{uuid.uuid4().hex[:10]}@test.com",
            "password": PASSWORD,
            "role": "manager",
            "organization_name": "Clube Sid",
        },
    )
    return c, cookie_from(r, "vip_access"), cookie_from(r, "vip_refresh")


async def test_2_access_token_dies_on_logout():
    c, access, _ = await _register_manager_client()
    assert (await c.get(f"{API}/auth/me")).status_code == 200
    assert (await c.post(f"{API}/auth/logout")).status_code == 204
    stolen = make_client()
    r = await stolen.get(f"{API}/auth/me", headers={"Cookie": f"vip_access={access}"})
    assert r.status_code == 401 and error_code(r) == "unauthenticated"


async def test_2_access_token_dies_on_change_password_for_other_sessions_only():
    c1, access1, _ = await _register_manager_client()
    email = (await c1.get(f"{API}/auth/me")).json()["user"]["email"]
    c2 = make_client()
    r = await c2.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD})
    access2 = cookie_from(r, "vip_access")
    ok = await c1.post(
        f"{API}/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "Nova12345"},
    )
    assert ok.status_code == 204
    other = await make_client().get(f"{API}/auth/me", headers={"Cookie": f"vip_access={access2}"})
    assert other.status_code == 401
    same = await make_client().get(f"{API}/auth/me", headers={"Cookie": f"vip_access={access1}"})
    assert same.status_code == 200  # a sessao que trocou a senha segue valida


async def test_2_access_token_dies_on_refresh_reuse_detection():
    c, access, refresh = await _register_manager_client()
    other = make_client()
    ok = await other.post(f"{API}/auth/refresh", headers={"Cookie": f"vip_refresh={refresh}"})
    new_access = cookie_from(ok, "vip_access")
    assert (
        await make_client().get(f"{API}/auth/me", headers={"Cookie": f"vip_access={new_access}"})
    ).status_code == 200
    reuse = await other.post(f"{API}/auth/refresh", headers={"Cookie": f"vip_refresh={refresh}"})
    assert reuse.status_code == 401
    for tok in (access, new_access):  # mesma familia: todos os acessos morrem
        r = await make_client().get(f"{API}/auth/me", headers={"Cookie": f"vip_access={tok}"})
        assert r.status_code == 401


async def test_2_redis_down_falls_back_to_postgres_fail_closed(monkeypatch):
    c, access, _ = await _register_manager_client()
    c_dead, access_dead, _ = await _register_manager_client()
    await c_dead.post(f"{API}/auth/logout")
    await get_redis().flushdb()  # a marca de revogacao no Redis se perdeu

    def boom():
        raise ConnectionError("redis fora")

    monkeypatch.setattr(sessions, "get_redis", boom)
    live = await make_client().get(f"{API}/auth/me", headers={"Cookie": f"vip_access={access}"})
    assert live.status_code == 200  # familia viva no Postgres
    dead = await make_client().get(
        f"{API}/auth/me", headers={"Cookie": f"vip_access={access_dead}"}
    )
    assert dead.status_code == 401  # revogada no Postgres: fecha, nunca abre


# ---------------------------------------------------------------- 3. corrida no refresh


async def test_3_refresh_and_logout_race_leaves_no_live_token():
    for _ in range(3):
        c, _, refresh = await _register_manager_client()
        results = await asyncio.gather(
            c.post(f"{API}/auth/refresh"),
            c.post(f"{API}/auth/refresh"),
            c.post(f"{API}/auth/logout"),
            return_exceptions=True,
        )
        assert not any(isinstance(r, Exception) for r in results)
        assert sum(1 for r in results[:2] if r.status_code == 200) <= 1
        async with SessionLocal() as db:
            live = await db.scalar(
                select(sa_func.count())
                .select_from(RefreshToken)
                .where(RefreshToken.revoked_at.is_(None))
            )
        assert live == 0, "sucessor nasceu numa familia revogada"
        assert refresh


async def test_3_concurrent_refresh_same_token_issues_single_successor():
    c, _, refresh = await _register_manager_client()
    results = await asyncio.gather(
        *[
            make_client().post(f"{API}/auth/refresh", headers={"Cookie": f"vip_refresh={refresh}"})
            for _ in range(5)
        ]
    )
    assert sum(1 for r in results if r.status_code == 200) == 1
    async with SessionLocal() as db:
        live = await db.scalar(
            select(sa_func.count())
            .select_from(RefreshToken)
            .where(RefreshToken.revoked_at.is_(None))
        )
    assert live == 0  # os demais detectaram reutilizacao e revogaram a familia


# ---------------------------------------------------------------- 4. limite de corpo


async def test_4_webhook_body_limit_content_length_and_chunked(anon):
    big = b"x" * (1024 * 1024 + 1)
    r = await anon.post(f"{API}/webhooks/instagram", content=big)
    assert r.status_code == 413 and error_code(r) == "payload_too_large"

    async def chunks():
        for _ in range(5):
            yield b"y" * 300_000

    r = await anon.post(f"{API}/webhooks/instagram", content=chunks())  # chunked, sem length
    assert r.status_code == 413 and error_code(r) == "payload_too_large"


async def test_4_upload_unauthenticated_rejected_before_reading_and_size_cap(anon):
    r = await anon.post(f"{API}/uploads/image", files={"file": ("a.png", b"x" * 1000, "image/png")})
    assert r.status_code == 401 and error_code(r) == "unauthenticated"
    m = await new_manager(connect=False)
    huge = b"\x00" * (10 * 1024 * 1024)
    r = await m.client.post(f"{API}/uploads/image", files={"file": ("a.png", huge, "image/png")})
    assert r.status_code == 413 and error_code(r) == "payload_too_large"

    async def chunks():
        yield (
            b'--x\r\nContent-Disposition: form-data; name="file"; filename="a.png"\r\n'
            b"Content-Type: image/png\r\n\r\n"
        )
        for _ in range(12):
            yield b"z" * (1024 * 1024)

    r = await m.client.post(
        f"{API}/uploads/image",
        content=chunks(),
        headers={"Content-Type": "multipart/form-data; boundary=x"},
    )
    assert r.status_code == 413


async def test_4_regular_routes_are_capped_at_1mb():
    m = await new_manager(connect=False)
    r = await m.client.post(f"{API}/rewards", content=b"{" + b" " * (1024 * 1024 + 10) + b"}")
    assert r.status_code == 413 and error_code(r) == "payload_too_large"


# ---------------------------------------------------------------- 5. story sem deadlock


async def test_5_concurrent_story_mentions_award_once_without_deadlock():
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    await m.campaign()
    acc = await ig_id(m)
    results = await asyncio.gather(
        *[run_event(story_event(acc, f"mid_{i}", "bia.promo")) for i in range(8)],
        return_exceptions=True,
    )
    assert not [r for r in results if isinstance(r, Exception)], results
    got = sorted(r.interaction.status for r in results)
    assert got.count("awarded") == 1 and got.count("duplicate") == 7
    assert await p.balance() == 80


# ---------------------------------------------------------------- 6. retry de webhooks (arq)

_attempts: list[int] = []


async def test_6_transient_failure_raises_retry_with_backoff_and_logs_ids_when_exhausted(
    monkeypatch, caplog
):
    async def boom(payload):
        raise TransientPipelineError("temporario")

    monkeypatch.setattr(worker_mod, "handle_webhook_payload", boom)
    payload = comment_payload("1", "m1", "c_secret_id", "someone")
    with pytest.raises(Retry) as first:
        await worker_mod.process_webhook({"job_try": 1}, payload)
    with pytest.raises(Retry) as third:
        await worker_mod.process_webhook({"job_try": 3}, payload)
    assert third.value.defer_score > first.value.defer_score  # backoff crescente
    with caplog.at_level(logging.ERROR, logger="app.worker"):
        assert await worker_mod.process_webhook({"job_try": worker_mod.MAX_TRIES}, payload) == 0
    msg = " ".join(r.getMessage() for r in caplog.records)
    assert "comment:c_secret_id" in msg and "Quero participar" not in msg

    async def permanent(payload):
        raise ValueError("bug")

    monkeypatch.setattr(worker_mod, "handle_webhook_payload", permanent)
    with pytest.raises(ValueError):
        await worker_mod.process_webhook({"job_try": 1}, payload)


async def test_6_arq_really_retries_the_job(monkeypatch):
    _attempts.clear()

    async def flaky(payload):
        _attempts.append(1)
        if len(_attempts) < 3:
            raise TransientPipelineError("temporario")
        return 1

    monkeypatch.setattr(worker_mod, "handle_webhook_payload", flaky)
    monkeypatch.setattr(worker_mod, "BACKOFF_SECONDS", (0,))
    from arq import create_pool

    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    await pool.enqueue_job("process_webhook", {"object": "instagram", "entry": []})
    worker = Worker(
        functions=[func(worker_mod.process_webhook, name="process_webhook")],
        redis_pool=pool,
        burst=True,
        max_tries=worker_mod.MAX_TRIES,
        poll_delay=0.05,
        handle_signals=False,
    )
    await asyncio.wait_for(worker.main(), timeout=20)
    await worker.close()
    assert len(_attempts) == 3  # falhou duas vezes e foi repetido ate dar certo


# ---------------------------------------------------------------- 7. publicacao idempotente


async def test_7_lost_publish_response_is_recovered_without_second_publish(monkeypatch):
    m = await new_manager()
    original = MockInstagramClient.publish_container

    async def lost_response(self, token, ig_user_id, container_id):
        await original(self, token, ig_user_id, container_id)  # o Instagram PUBLICOU...
        raise InstagramError("timeout na resposta")  # ...mas a resposta se perdeu

    monkeypatch.setattr(MockInstagramClient, "publish_container", lost_response)
    r = await m.client.post(
        f"{API}/campaigns",
        json={
            "title": "Publicada",
            "source": "publish",
            "image_url": "https://x.test/a.jpg",
            "caption": "Legenda única 123",
        },
    )
    cid = r.json()["id"]
    first = await m.client.post(f"{API}/campaigns/{cid}/dispatch")
    assert first.status_code == 502 and error_code(first) == "instagram_error"
    async with SessionLocal() as db:
        c = await db.get(Campaign, cid)
        container = c.publish_container_id
        assert container and c.ig_media_id is None and c.status == "draft"

    monkeypatch.setattr(MockInstagramClient, "publish_container", original)
    second = await m.client.post(f"{API}/campaigns/{cid}/dispatch")
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["status"] == "active" and body["ig_media_id"]
    r = get_redis()
    assert len([k async for k in r.scan_iter("mock:container:*")]) == 1  # um unico container
    published = await r.lrange(f"mock:published:{await ig_id(m)}", 0, -1)
    assert len(published) == 1  # um unico post
    async with SessionLocal() as db:
        assert (await db.get(Campaign, cid)).publish_container_id == container


async def test_7_pending_container_is_reused_not_recreated(monkeypatch):
    m = await new_manager()

    async def fail(self, token, ig_user_id, container_id):
        raise InstagramError("fora do ar", status=500)

    monkeypatch.setattr(MockInstagramClient, "publish_container", fail)
    r = await m.client.post(
        f"{API}/campaigns",
        json={
            "title": "Pub 2",
            "source": "publish",
            "image_url": "https://x.test/a.jpg",
            "caption": "Leg 2",
        },
    )
    cid = r.json()["id"]
    for _ in range(3):
        assert (await m.client.post(f"{API}/campaigns/{cid}/dispatch")).status_code == 502
    keys = [k async for k in get_redis().scan_iter("mock:container:*")]
    assert len(keys) == 1  # nunca criou um segundo container


# ---------------------------------------------------------------- 8/9. rate limit


def _request(peer: str, xff: str | None) -> Request:
    headers = [(b"x-forwarded-for", xff.encode())] if xff else []
    return Request(
        {"type": "http", "headers": headers, "client": (peer, 1234), "method": "GET", "path": "/"}
    )


def test_8_xff_only_honoured_from_trusted_peers(monkeypatch):
    assert rate_limit.client_ip(_request("172.18.0.5", "9.9.9.9, 203.0.113.7")) == "203.0.113.7"
    assert rate_limit.client_ip(_request("8.8.8.8", "1.2.3.4")) == "8.8.8.8"  # peer nao confiavel
    assert rate_limit.client_ip(_request("172.18.0.5", None)) == "172.18.0.5"
    monkeypatch.setattr(settings, "trusted_proxy_cidrs", "10.1.0.0/16")
    assert rate_limit.client_ip(_request("172.18.0.5", "1.2.3.4")) == "172.18.0.5"
    assert rate_limit.client_ip(_request("10.1.2.3", "1.2.3.4")) == "1.2.3.4"


async def test_9_rate_limit_falls_back_to_memory_when_redis_is_down(monkeypatch, client):
    monkeypatch.setattr(settings, "rate_limit_multiplier", 1)
    monkeypatch.setattr(settings, "rl_login_ip", "3/60")

    def boom():
        raise ConnectionError("redis fora")

    monkeypatch.setattr(rate_limit, "get_redis", boom)
    codes = []
    for _ in range(5):
        r = await client.post(
            f"{API}/auth/login", json={"email": "x@test.com", "password": "abc12345"}
        )
        codes.append(r.status_code)
    assert codes == [401, 401, 401, 429, 429]


# ---------------------------------------------------------------- 10. username do story


async def test_10_transient_username_failure_retries_and_stores_nothing(monkeypatch):
    m = await new_manager()
    await new_promoter(m, username="bia.promo")
    await m.campaign()
    acc = await ig_id(m)

    async def transient(self, token, scoped_id):
        raise InstagramError("5xx", status=503)

    monkeypatch.setattr(MockInstagramClient, "get_user_username", transient)
    with pytest.raises(TransientPipelineError):
        await run_event(story_event(acc, "mid_t", "bia.promo"))
    async with SessionLocal() as db:
        assert await db.scalar(select(sa_func.count()).select_from(Interaction)) == 0


async def test_10_definitive_failure_stays_unmatched_and_rematchable_by_scoped_id(monkeypatch):
    m = await new_manager()
    c = await m.campaign()
    p = await new_promoter(m, approve=False, username="sem.nome")
    acc = await ig_id(m)
    async with SessionLocal() as db:
        await db.execute(
            update(PromoterProfile)
            .where(PromoterProfile.instagram_username == "sem.nome")
            .values(ig_scoped_id="mock_sem.nome")
        )
        await db.commit()

    async def definitive(self, token, scoped_id):
        raise InstagramError("usuario inexistente", status=400)

    monkeypatch.setattr(MockInstagramClient, "get_user_username", definitive)
    res = await run_event(story_event(acc, "mid_d", "sem.nome"))
    assert res.interaction.status == "unmatched" and res.interaction.ig_scoped_id == "mock_sem.nome"
    mem = await p.membership()
    ok = await m.client.post(f"{API}/team/members/{mem['id']}/approve")
    assert ok.json()["points_balance"] == 80  # re-casado por ig_scoped_id
    assert c


# ---------------------------------------------------------------- 11. assinatura de webhooks


async def test_11_cron_retries_failed_webhook_subscription():
    m = await new_manager()
    async with SessionLocal() as db:
        await db.execute(update(InstagramAccount).values(webhook_subscribed=False))
        await db.commit()
    assert (await m.client.get(f"{API}/instagram/account")).json()["account"][
        "webhook_subscribed"
    ] is False
    assert await worker_mod.retry_webhook_subscriptions({}) == 1
    assert (await m.client.get(f"{API}/instagram/account")).json()["account"][
        "webhook_subscribed"
    ] is True
    assert await worker_mod.retry_webhook_subscriptions({}) == 0


# ---------------------------------------------------------------- 12. revalidacao apos o lock


async def test_12_membership_removed_after_match_is_not_awarded(monkeypatch):
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    c = await m.campaign()
    acc = await ig_id(m)
    async with SessionLocal() as db:
        stale = (await db.execute(select(Membership))).scalar_one()
        db.expunge(stale)

    await m.client.post(f"{API}/team/members/{(await p.membership())['id']}/remove")

    async def stale_match(db, org_id, from_id, username):
        return stale

    monkeypatch.setattr(pipeline, "_match_membership", stale_match)
    res = await run_event(event(acc, c["ig_media_id"], "late_1", "bia.promo"))
    assert res.interaction.status == "unmatched" and res.interaction.membership_id is None
    async with SessionLocal() as db:
        assert (await db.scalar(select(Membership.points_balance))) == 0


async def test_12_campaign_ended_after_lookup_is_out_of_window(monkeypatch):
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    c = await m.campaign()
    acc = await ig_id(m)
    async with SessionLocal() as db:
        stale = await db.get(Campaign, c["id"])
        db.expunge(stale)
    await m.client.post(f"{API}/campaigns/{c['id']}/end")

    async def stale_campaign(db, org_id, media_id):
        return stale

    monkeypatch.setattr(pipeline, "_find_comment_campaign", stale_campaign)
    res = await run_event(event(acc, c["ig_media_id"], "late_2", "bia.promo"))
    assert res.interaction.status == "out_of_window"
    assert await p.balance() == 0


# ---------------------------------------------------------------- 13. polling paginado


async def test_13_polling_resumes_from_cursor_and_stops_early_after_full_pass(monkeypatch):
    monkeypatch.setattr(settings, "sync_page_size", 2)
    monkeypatch.setattr(settings, "sync_pages_per_run", 2)
    from app.services.instagram.mock import mock_store_comment

    m = await new_manager()
    c = await m.campaign(starts_at=(datetime.now(UTC) - timedelta(days=1)).isoformat())
    acc = await ig_id(m)
    now = datetime.now(UTC)
    for i in range(7):
        await mock_store_comment(
            acc,
            c["ig_media_id"],
            f"pc_{i}",
            f"u{i}",
            f"mock_u{i}",
            f"t{i}",
            now + timedelta(seconds=i),
        )

    async def cursor_state():
        async with SessionLocal() as db:
            camp = await db.get(Campaign, c["id"], populate_existing=True)
            return camp.sync_cursor, camp.sync_full_pass_at

    r1 = (await m.client.post(f"{API}/campaigns/{c['id']}/sync")).json()
    assert r1["fetched"] == 4 and r1["new_interactions"] == 4
    cur, full = await cursor_state()
    assert cur is not None and full is None  # cortada pelo orcamento: guarda a continuacao

    r2 = (await m.client.post(f"{API}/campaigns/{c['id']}/sync")).json()
    assert r2["fetched"] == 3 and r2["new_interactions"] == 3  # retomou do cursor
    cur, full = await cursor_state()
    assert cur is None and full is not None  # fim da listagem: cursor limpo, passada completa
    assert len(await statuses(m, c["id"], limit=100)) == 7

    await mock_store_comment(
        acc, c["ig_media_id"], "pc_new", "u9", "mock_u9", "novo", now + timedelta(seconds=30)
    )
    r3 = (await m.client.post(f"{API}/campaigns/{c['id']}/sync")).json()
    assert r3["new_interactions"] == 1
    assert r3["fetched"] == 4  # parou na pagina so com ids conhecidos (nao leu os 8)
    assert len(await statuses(m, c["id"], limit=100)) == 8


# ---------------------------------------------------------------- 14. um post, uma campanha


async def test_14_concurrent_creates_for_same_post_yield_one_campaign():
    m = await new_manager()
    media = (await m.media_ids())[0]
    body = {"title": "Mesma mídia", "source": "existing", "ig_media_id": media}
    results = await asyncio.gather(
        *[m.client.post(f"{API}/campaigns", json=body) for _ in range(4)]
    )
    codes = sorted(r.status_code for r in results)
    assert codes == [201, 409, 409, 409]
    loser = next(r for r in results if r.status_code == 409)
    assert error_code(loser) == "conflict"
    assert loser.json()["error"]["message"] == "Já existe uma campanha em andamento para este post."
    created = next(r for r in results if r.status_code == 201).json()
    # depois de encerrada, o mesmo post pode ter nova campanha
    await m.client.post(f"{API}/campaigns/{created['id']}/dispatch")
    await m.client.post(f"{API}/campaigns/{created['id']}/end")
    assert (await m.client.post(f"{API}/campaigns", json=body)).status_code == 201


# ---------------------------------------------------------------- 15. dispatch exatamente uma vez


async def test_15_concurrent_dispatch_activates_and_notifies_once():
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    c = await m.campaign(dispatch=False)
    results = await asyncio.gather(
        *[m.client.post(f"{API}/campaigns/{c['id']}/dispatch") for _ in range(4)]
    )
    assert sorted(r.status_code for r in results) == [200, 400, 400, 400]
    notes = (await p.client.get(f"{API}/notifications")).json()["items"]
    assert len([n for n in notes if n["type"] == "campaign_dispatched"]) == 1


# ---------------------------------------------------------------- 18. org_id omitido


async def test_18_removed_member_sees_no_history_without_org_id():
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    c = await m.campaign()
    await m.simulate_comment(c["id"], "bia.promo")
    assert (await p.client.get(f"{API}/promoter/transactions")).json()["total"] == 1
    await m.client.post(f"{API}/team/members/{(await p.membership())['id']}/remove")
    assert (await p.client.get(f"{API}/promoter/transactions")).json()["total"] == 0
    assert (await p.client.get(f"{API}/promoter/redemptions")).json()["total"] == 0


# ---------------------------------------------------------------- 19. janela no dispatch


async def test_19_dispatch_rejects_end_before_start_or_in_the_past():
    m = await new_manager()
    past_end = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    c = await m.campaign(dispatch=False, ends_at=past_end)
    r = await m.client.post(f"{API}/campaigns/{c['id']}/dispatch")
    assert r.status_code == 400 and error_code(r) == "validation_error"
    assert "término" in r.json()["error"]["message"]
    assert "ends_at" in r.json()["error"]["fields"]
    assert (await m.client.get(f"{API}/campaigns/{c['id']}")).json()["status"] == "draft"
    # ends_at antes do inicio efetivo (starts_at no futuro)
    c2 = await m.campaign(
        index=1,
        dispatch=False,
        starts_at=(datetime.now(UTC) + timedelta(days=5)).isoformat(),
    )
    await m.client.patch(
        f"{API}/campaigns/{c2['id']}",
        json={"ends_at": (datetime.now(UTC) + timedelta(days=6)).isoformat()},
    )
    assert (await m.client.post(f"{API}/campaigns/{c2['id']}/dispatch")).status_code == 200


# ---------------------------------------------------------------- 20. payload minimo


def test_20_sanitize_keeps_only_what_the_pipeline_needs():
    payload = {
        "object": "instagram",
        "extra": "x",
        "entry": [
            {
                "id": "111",
                "time": 1,
                "changes": [
                    {"field": "mentions", "value": {"secret": "s"}},
                    {
                        "field": "comments",
                        "value": {
                            "id": "c1",
                            "text": "oi",
                            "from": {"id": "9", "username": "u", "self_ig_scoped_id": "z"},
                            "media": {"id": "m1", "media_product_type": "FEED"},
                            "verb": "add",
                        },
                    },
                ],
                "messaging": [
                    {
                        "sender": {"id": "9", "name": "Fulano"},
                        "recipient": {"id": "111"},
                        "timestamp": 5,
                        "message": {
                            "mid": "mid1",
                            "text": "mensagem privada",
                            "attachments": [
                                {
                                    "type": "story_mention",
                                    "payload": {"url": "https://c/s", "x": 1},
                                },
                                {"type": "image", "payload": {"url": "https://c/i"}},
                            ],
                        },
                    },
                    {
                        "sender": {"id": "9"},
                        "recipient": {"id": "111"},
                        "message": {"mid": "mid2", "text": "so texto"},
                    },
                ],
            }
        ],
    }
    out = sanitize_payload(payload)
    flat = json.dumps(out)
    assert "mensagem privada" not in flat and "so texto" not in flat and "Fulano" not in flat
    assert "mentions" not in flat and "verb" not in flat and "image" not in flat
    entry = out["entry"][0]
    assert len(entry["changes"]) == 1 and len(entry["messaging"]) == 1
    assert entry["messaging"][0]["message"]["attachments"] == [
        {"type": "story_mention", "payload": {"url": "https://c/s"}}
    ]
    assert (
        sanitize_payload(
            {
                "object": "instagram",
                "entry": [{"id": "1", "messaging": [{"message": {"text": "x"}}]}],
            }
        )
        is None
    )
    assert sanitize_payload({"object": "page"}) is None


async def test_20_endpoint_enqueues_reduced_payload_and_arq_logger_is_quiet(anon, arq):
    from app.services.webhooks import sign_body

    payload = story_payload("111", "9", "mid1")
    payload["entry"][0]["messaging"][0]["message"]["text"] = "privado"
    body = json.dumps(payload).encode()
    r = await anon.post(
        f"{API}/webhooks/instagram",
        content=body,
        headers={"X-Hub-Signature-256": sign_body(body, settings.webhook_secret)},
    )
    assert r.status_code == 200
    assert len(arq.jobs) == 1 and "privado" not in json.dumps(arq.jobs[0][1])
    # sem nada processavel: aceita (200) e nao enfileira
    empty = json.dumps({"object": "instagram", "entry": []}).encode()
    r = await anon.post(
        f"{API}/webhooks/instagram",
        content=empty,
        headers={"X-Hub-Signature-256": sign_body(empty, settings.webhook_secret)},
    )
    assert r.status_code == 200 and len(arq.jobs) == 1
    setup_logging()
    assert logging.getLogger("arq.worker").level >= logging.WARNING


# ---------------------------------------------------------------- 21. tolerancia no story


async def test_21_story_mention_respects_start_tolerance():
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    await m.campaign(starts_at=(datetime.now(UTC) + timedelta(seconds=10)).isoformat())
    it = await m.simulate_story("bia.promo")
    assert it["status"] == "awarded" and await p.balance() == 80


# ---------------------------------------------------------------- 22. 500 com cabecalhos


async def test_22_unhandled_500_carries_security_headers_and_request_id(client, monkeypatch):
    from app.api.v1 import misc

    def boom(**_):
        raise RuntimeError("segredo")

    monkeypatch.setattr(misc, "ConfigOut", boom)
    r = await client.get(f"{API}/config")
    assert r.status_code == 500 and r.json()["error"]["code"] == "internal_error"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in r.headers["content-security-policy"]
    assert r.headers.get("x-request-id")
