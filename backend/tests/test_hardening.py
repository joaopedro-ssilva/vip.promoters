"""Endurecimento para producao: prontidao, rotacao de chaves, segredo do webhook."""

import uuid

from cryptography.fernet import Fernet

from app.core import crypto
from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, sign_state, verify_state
from app.services.webhooks import sign_body, verify_signature

API = "/api/v1"


async def test_readiness_checks_database_and_redis(client):
    r = await client.get(f"{API}/health/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok", "redis": "ok"}


async def test_readiness_fails_when_redis_is_down(client, monkeypatch):
    class Broken:
        async def ping(self):
            raise ConnectionError("fora")

    monkeypatch.setattr("app.api.v1.misc.get_redis", lambda: Broken())
    r = await client.get(f"{API}/health/ready")
    assert r.status_code == 503
    assert r.json()["redis"] == "error"


def test_access_token_survives_secret_key_rotation(monkeypatch):
    old, new = "a" * 40, "b" * 40
    monkeypatch.setattr(settings, "secret_key", old)
    monkeypatch.setattr(settings, "secret_key_previous", "")
    uid, sid = uuid.uuid4(), uuid.uuid4()
    token = create_access_token(uid, "manager", sid)
    state = sign_state(uid)

    monkeypatch.setattr(settings, "secret_key", new)
    assert decode_access_token(token) is None  # sem a chave anterior: recusado
    assert verify_state(state) is None

    monkeypatch.setattr(settings, "secret_key_previous", old)
    assert decode_access_token(token) == (uid, sid)
    assert verify_state(state) == uid
    # tokens novos saem com a chave nova
    assert decode_access_token(create_access_token(uid, "manager", sid)) == (uid, sid)


def test_token_encryption_key_rotation(monkeypatch):
    key_a, key_b = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "token_encryption_key", key_a)
    monkeypatch.setattr(settings, "token_encryption_key_previous", "")
    crypto.reset_cipher()
    try:
        cipher = crypto.encrypt("ig-token")

        monkeypatch.setattr(settings, "token_encryption_key", key_b)
        monkeypatch.setattr(settings, "token_encryption_key_previous", key_a)
        crypto.reset_cipher()
        assert crypto.decrypt(cipher) == "ig-token"
        rotated = crypto.rotate(cipher)

        # depois da recifra, a chave antiga pode sair
        monkeypatch.setattr(settings, "token_encryption_key_previous", "")
        crypto.reset_cipher()
        assert crypto.decrypt(rotated) == "ig-token"
    finally:
        monkeypatch.undo()
        crypto.reset_cipher()


def test_webhook_secret_overrides_app_secret(monkeypatch):
    monkeypatch.setattr(settings, "meta_app_secret", "app-secret")
    monkeypatch.setattr(settings, "meta_webhook_secret", "instagram-secret")
    body = b'{"object":"instagram","entry":[]}'
    assert verify_signature(body, sign_body(body, "instagram-secret"))
    assert not verify_signature(body, sign_body(body, "app-secret"))


# ---------------------------------------------------------------- retencao


async def test_retention_anonymizes_old_interactions_and_keeps_points(client):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select, update

    from app.core.db import SessionLocal
    from app.models import Campaign, Interaction, Membership, Notification, RefreshToken
    from app.services import retention
    from tests.helpers import new_manager, new_promoter

    m = await new_manager()
    p = await new_promoter(m)
    old = await m.campaign(index=0)
    fresh = await m.campaign(index=1)
    await m.simulate_comment(old["id"], p.username, "texto antigo")
    await m.simulate_comment(fresh["id"], p.username, "texto novo")
    assert (await m.client.post(f"{API}/campaigns/{old['id']}/end")).status_code == 200

    now = datetime.now(UTC)
    async with SessionLocal() as db:
        # a campanha antiga encerrou ha 400 dias
        await db.execute(
            update(Campaign)
            .where(Campaign.id == old["id"])
            .values(ended_at=now - timedelta(days=400))
        )
        await db.commit()
        balance_before = (
            await db.execute(select(Membership.points_balance).where(Membership.id == p.membership_id))
        ).scalar_one()
        res = await retention.purge(db, now)
        assert res.interactions_anonymized == 1

        rows = {
            str(i.campaign_id): i
            for i in (await db.execute(select(Interaction))).scalars()
        }
        gone, kept = rows[old["id"]], rows[fresh["id"]]
        assert gone.text is None and gone.ig_username is None and gone.ig_scoped_id is None
        assert gone.points_awarded == 50 and gone.status == "awarded"
        assert kept.text == "texto novo" and kept.ig_username == p.username
        balance_after = (
            await db.execute(select(Membership.points_balance).where(Membership.id == p.membership_id))
        ).scalar_one()
        assert balance_after == balance_before  # extrato e saldo intactos

        # idempotente
        assert (await retention.purge(db, now)).interactions_anonymized == 0

        # sessoes expiradas e notificacoes lidas antigas
        n_tokens = len((await db.execute(select(RefreshToken))).scalars().all())
        await db.execute(update(RefreshToken).values(expires_at=now - timedelta(days=1)))
        await db.execute(
            update(Notification).values(read_at=now, created_at=now - timedelta(days=200))
        )
        await db.commit()
        res = await retention.purge(db, now)
        assert res.refresh_tokens_deleted == n_tokens
        assert res.notifications_deleted > 0
