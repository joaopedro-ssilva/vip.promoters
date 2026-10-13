"""Verificacao do @ por codigo em comentario e disputa de @."""

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Interaction, Membership, PromoterProfile
from tests.conftest import make_client
from tests.helpers import PASSWORD, comment_payload, error_code, new_manager, new_promoter

API = "/api/v1"


async def deliver_comment(manager, username: str, text: str, comment_id: str):
    """Comentario chegando pela MESMA porta do webhook real (pipeline)."""
    from app.services.interactions import process_event
    from app.services.webhooks import parse_payload

    acc = (await manager.client.get(f"{API}/instagram/account")).json()["account"]
    media = (await manager.media_ids())[3]  # post sem campanha: verificacao vale em qualquer post
    payload = comment_payload(acc["ig_user_id"], media, comment_id, username)
    payload["entry"][0]["changes"][0]["value"]["text"] = text
    async with SessionLocal() as db:
        for ev in parse_payload(payload):
            await process_event(db, ev)


async def test_promoter_verifies_own_username_by_comment():
    m = await new_manager()
    p = await new_promoter(m)
    r = await p.client.post(f"{API}/promoter/verification")
    assert r.status_code == 200, r.text
    code = r.json()["code"]
    assert code.startswith("VIP-") and r.json()["claim_username"] == p.username

    # outro @ comentando o codigo nao verifica
    await deliver_comment(m, "outra.pessoa", f"meu codigo {code}", "c_wrong")
    assert (await p.client.get(f"{API}/promoter/verification")).json()["verified"] is False

    await deliver_comment(m, p.username, f"verificando {code.lower()} obrigado", "c_ok")
    v = (await p.client.get(f"{API}/promoter/verification")).json()
    assert v["verified"] is True and v["code"] is None
    me = (await p.client.get(f"{API}/auth/me")).json()["user"]["promoter_profile"]
    assert me["verification_method"] == "comment"
    # comentario de verificacao nao vira interacao nem pontos
    async with SessionLocal() as db:
        assert (await db.execute(select(Interaction))).scalars().all() == []
        mem = await db.get(Membership, p.membership_id)
        assert mem.status == "approved"  # o proprio @: aprovacao continua

    r = await p.client.post(f"{API}/promoter/verification")
    assert r.status_code == 409 and error_code(r) == "already_verified"


async def test_username_dispute_moves_unverified_username_to_real_owner():
    m = await new_manager()
    squatter = await new_promoter(m, username="dono.real")

    c = make_client()
    body = {
        "name": "Dono Real",
        "email": "dono@test.com",
        "password": PASSWORD,
        "role": "promoter",
        "instagram_username": "dono.real",
        "invite_code": m.org["invite_code"],
    }
    r = await c.post(f"{API}/auth/register", json=body)
    assert r.status_code == 409 and error_code(r) == "instagram_username_claimable"
    r = await c.post(f"{API}/auth/register", json=body | {"claim_username": True})
    assert r.status_code == 201, r.text
    assert r.json()["user"]["promoter_profile"]["instagram_username"] is None
    v = (await c.get(f"{API}/promoter/verification")).json()
    assert v["claim_username"] == "dono.real"

    # sem @ o gestor nao consegue aprovar
    owner_mem = (await c.get(f"{API}/promoter/memberships")).json()["items"][0]
    r = await m.client.post(f"{API}/team/members/{owner_mem['id']}/approve")
    assert r.status_code == 400 and error_code(r) == "promoter_without_username"

    await deliver_comment(m, "dono.real", v["code"], "c_claim")

    me = (await c.get(f"{API}/auth/me")).json()["user"]["promoter_profile"]
    assert me == {
        "instagram_username": "dono.real",
        "verified": True,
        "verification_method": "comment",
    }
    async with SessionLocal() as db:
        lost = await db.get(PromoterProfile, squatter.user["id"])
        assert lost.instagram_username is None and lost.verified is False
        mem = await db.get(Membership, squatter.membership_id)
        assert mem.status == "pending"  # quem perdeu o @ volta para analise
    notes = (await squatter.client.get(f"{API}/notifications")).json()["items"]
    assert any(n["type"] == "username_lost" for n in notes)

    # agora o gestor aprova o dono real
    r = await m.client.post(f"{API}/team/members/{owner_mem['id']}/approve")
    assert r.status_code == 200


async def test_verified_username_cannot_be_claimed():
    m = await new_manager()
    owner = await new_promoter(m, username="ja.verificado")
    code = (await owner.client.post(f"{API}/promoter/verification")).json()["code"]
    await deliver_comment(m, "ja.verificado", code, "c_v")

    other = await new_promoter()
    r = await other.client.post(
        f"{API}/promoter/username-claims", json={"instagram_username": "ja.verificado"}
    )
    assert r.status_code == 409 and error_code(r) == "instagram_username_verified"
    r = await make_client().post(
        f"{API}/auth/register",
        json={
            "name": "Outro",
            "email": "outro@test.com",
            "password": PASSWORD,
            "role": "promoter",
            "instagram_username": "ja.verificado",
            "claim_username": True,
        },
    )
    assert r.status_code == 409 and error_code(r) == "instagram_username_taken"


async def test_changing_username_cancels_pending_claim():
    p = await new_promoter()
    await p.client.post(f"{API}/promoter/verification")
    r = await p.client.patch(f"{API}/promoter/profile", json={"instagram_username": "novo.arroba"})
    assert r.status_code == 200
    assert (await p.client.get(f"{API}/promoter/verification")).json()["code"] is None


async def test_promoter_instagram_login_is_disabled():
    p = await new_promoter()
    r = await p.client.post(f"{API}/instagram/connect")
    assert r.status_code == 400 and error_code(r) == "use_comment_verification"
