"""LGPD: exclusao de conta, exclusao de dados pedida pela Meta e esquecimento de terceiros."""

import base64
import hashlib
import hmac
import json

from sqlalchemy import func, select

from app.core.config import settings
from app.core.db import SessionLocal
from app.models import (
    DataDeletionRequest,
    InstagramAccount,
    Interaction,
    Membership,
    Organization,
    Reward,
    User,
)
from app.services import privacy
from tests.helpers import PASSWORD, error_code, new_manager, new_promoter
from tests.test_rewards import fund, make_reward, redeem

API = "/api/v1"


def signed_request(payload: dict) -> str:
    raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = hmac.new(settings.webhook_secret.encode(), raw.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip("=") + "." + raw


async def count(model, *where) -> int:
    async with SessionLocal() as db:
        return await db.scalar(select(func.count()).select_from(model).where(*where))


async def test_delete_account_requires_password_and_confirmation():
    p = await new_promoter()
    r = await p.client.post(
        f"{API}/auth/delete-account", json={"password": PASSWORD, "confirmation": "sim"}
    )
    assert r.status_code == 422 and "confirmation" in r.json()["error"]["fields"]
    r = await p.client.post(
        f"{API}/auth/delete-account", json={"password": PASSWORD[::-1], "confirmation": "EXCLUIR"}
    )
    assert r.status_code == 422 and "password" in r.json()["error"]["fields"]
    assert await count(User, User.id == p.user["id"]) == 1


async def test_promoter_deletes_account():
    m = await new_manager()
    p = await new_promoter(m)
    other = await new_promoter(m)
    c = await m.campaign()
    await m.simulate_comment(c["id"], p.username, "meu comentario")
    await m.simulate_comment(c["id"], other.username, "outro")
    reward = await make_reward(m, stock=3)
    await fund(m, p, 200)
    assert (await redeem(p, reward["id"])).status_code == 201

    r = await p.client.post(
        f"{API}/auth/delete-account", json={"password": PASSWORD, "confirmation": "excluir"}
    )
    assert r.status_code == 204
    assert 'vip_access=""' in r.headers.get("set-cookie", "") or "Max-Age=0" in r.headers.get(
        "set-cookie", ""
    )
    # sessao derrubada na hora
    assert (await p.client.get(f"{API}/auth/me")).status_code == 401
    assert await count(User, User.id == p.user["id"]) == 0
    assert await count(Membership, Membership.id == p.membership_id) == 0

    async with SessionLocal() as db:
        rows = (await db.execute(select(Interaction))).scalars().all()
        mine = [i for i in rows if i.points_awarded == 50 and i.ig_username is None]
        theirs = [i for i in rows if i.ig_username == other.username]
        assert len(mine) == 1 and mine[0].text is None and mine[0].membership_id is None
        assert len(theirs) == 1 and theirs[0].text == "outro"  # terceiros intactos
        # o resgate pendente devolveu o estoque
        assert (await db.get(Reward, reward["id"])).stock == 3

    # gestor continua vendo o total de pontos distribuidos
    dash = (await m.client.get(f"{API}/dashboard/manager")).json()
    assert dash["kpis"]["promoters_approved"] == 1
    # o mesmo e-mail e @ podem ser usados de novo
    again = await new_promoter(username=p.username)
    assert again.username == p.username


async def test_manager_deletes_account_and_organization():
    m = await new_manager()
    keep = await new_manager()
    p = await new_promoter(m)
    c = await m.campaign()
    await m.simulate_comment(c["id"], p.username)
    reward = await make_reward(m)
    await fund(m, p, 200)
    assert (await redeem(p, reward["id"])).status_code == 201  # resgate (FK RESTRICT)

    r = await m.client.post(
        f"{API}/auth/delete-account", json={"password": PASSWORD, "confirmation": "EXCLUIR"}
    )
    assert r.status_code == 204
    assert await count(Organization, Organization.id == m.org["id"]) == 0
    assert await count(Interaction, Interaction.organization_id == m.org["id"]) == 0
    assert await count(InstagramAccount, InstagramAccount.user_id == m.user["id"]) == 0
    # o promoter continua existindo, so sem a equipe; a outra organizacao nao foi tocada
    assert (await p.client.get(f"{API}/promoter/memberships")).json()["items"] == []
    assert await count(Organization, Organization.id == keep.org["id"]) == 1


async def test_meta_data_deletion_callback(anon):
    m = await new_manager()
    p = await new_promoter(m)
    c = await m.campaign()
    await m.simulate_comment(c["id"], p.username, "comentario")
    acc = (await m.client.get(f"{API}/instagram/account")).json()["account"]

    r = await anon.post(
        f"{API}/meta/data-deletion",
        data={"signed_request": signed_request({"user_id": acc["ig_user_id"]})},
    )
    assert r.status_code == 200, r.text
    code = r.json()["confirmation_code"]
    assert r.json()["url"].endswith(f"/meta/data-deletion/{code}")

    assert await count(InstagramAccount, InstagramAccount.ig_user_id == acc["ig_user_id"]) == 0
    async with SessionLocal() as db:
        it = (await db.execute(select(Interaction))).scalars().one()
        assert it.text is None and it.ig_username is None and it.points_awarded == 50
        req = (await db.execute(select(DataDeletionRequest))).scalars().one()
        assert req.subject_hash == privacy.subject_hash(acc["ig_user_id"])
        assert acc["ig_user_id"] not in req.subject_hash

    status = await anon.get(f"{API}/meta/data-deletion/{code}")
    assert status.status_code == 200 and status.json()["status"] == "completed"
    assert (await anon.get(f"{API}/meta/data-deletion/naoexiste")).status_code == 404

    bad = await anon.post(f"{API}/meta/data-deletion", data={"signed_request": "x.y"})
    assert bad.status_code == 403 and error_code(bad) == "forbidden"


async def test_forget_third_party_username():
    m = await new_manager()
    c = await m.campaign()
    await m.simulate_comment(c["id"], "fulano.qualquer", "quero ir")
    async with SessionLocal() as db:
        assert await privacy.forget_instagram_username(db, "@Fulano.Qualquer") == 1
        it = (await db.execute(select(Interaction))).scalars().one()
        assert it.ig_username is None and it.text is None
