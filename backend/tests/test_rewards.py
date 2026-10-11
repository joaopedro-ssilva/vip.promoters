import asyncio
import uuid

from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models import Membership, PointTransaction
from tests.helpers import error_code, new_manager, new_promoter

API = "/api/v1"


async def make_reward(m, **over):
    body = {"name": "Entrada VIP", "cost_points": 100, "stock": 5} | over
    r = await m.client.post(f"{API}/rewards", json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def fund(m, p, amount):
    mem = await p.membership()
    r = await m.client.post(
        f"{API}/team/members/{mem['id']}/adjust-points",
        json={"amount": amount, "reason": "Bônus de teste"},
    )
    assert r.status_code == 200, r.text
    return r.json()


async def redeem(p, reward_id, request_id=None):
    return await p.client.post(
        f"{API}/promoter/rewards/{reward_id}/redeem",
        json={"request_id": request_id or str(uuid.uuid4())},
    )


async def test_redeem_happy_path_and_fulfill():
    m = await new_manager(connect=False)
    p = await new_promoter(m)
    reward = await make_reward(m)
    await fund(m, p, 250)
    r = await redeem(p, reward["id"])
    assert r.status_code == 201
    red = r.json()
    assert (
        red["status"] == "pending" and red["code"].startswith("VIP-") and red["cost_points"] == 100
    )
    assert red["reward"]["name"] == "Entrada VIP" and red["organization_name"] == m.org_name
    assert await p.balance() == 150
    rw = (await m.client.get(f"{API}/rewards")).json()["items"][0]
    assert rw["stock"] == 4 and rw["redeemed_count"] == 1

    mq = (await m.client.get(f"{API}/redemptions", params={"status": "pending"})).json()
    assert mq["total"] == 1 and mq["items"][0]["promoter"]["name"] == p.user["name"]
    notes = (await m.client.get(f"{API}/notifications")).json()["items"]
    assert any(n["type"] == "redemption_requested" for n in notes)

    f = await m.client.post(f"{API}/redemptions/{red['id']}/fulfill", json={"note": "Entregue"})
    assert (
        f.status_code == 200
        and f.json()["status"] == "fulfilled"
        and f.json()["note"] == "Entregue"
    )
    again = await m.client.post(f"{API}/redemptions/{red['id']}/fulfill", json={})
    assert again.status_code == 400 and error_code(again) == "redemption_not_pending"
    pn = (await p.client.get(f"{API}/notifications")).json()["items"]
    assert any(n["type"] == "redemption_fulfilled" for n in pn)
    mine = (await p.client.get(f"{API}/promoter/redemptions")).json()
    assert mine["total"] == 1 and mine["items"][0]["status"] == "fulfilled"


async def test_insufficient_points_and_balance_never_negative():
    m = await new_manager(connect=False)
    p = await new_promoter(m)
    reward = await make_reward(m)
    await fund(m, p, 99)
    r = await redeem(p, reward["id"])
    assert r.status_code == 400 and error_code(r) == "insufficient_points"
    assert await p.balance() == 99
    rw = (await m.client.get(f"{API}/rewards")).json()["items"][0]
    assert rw["stock"] == 5  # nada foi consumido


async def test_out_of_stock_and_unavailable_reward():
    m = await new_manager(connect=False)
    p = await new_promoter(m)
    await fund(m, p, 500)
    empty = await make_reward(m, stock=0)
    r = await redeem(p, empty["id"])
    assert r.status_code == 400 and error_code(r) == "out_of_stock"
    hidden = await make_reward(m, is_active=False)
    r = await redeem(p, hidden["id"])
    assert r.status_code == 400 and error_code(r) == "reward_unavailable"
    listed = (await p.client.get(f"{API}/promoter/rewards")).json()["items"]
    assert [x["name"] for x in listed] == ["Entrada VIP"]  # so ativos
    assert listed[0]["available"] is False  # estoque 0


async def test_per_promoter_limit():
    m = await new_manager(connect=False)
    p = await new_promoter(m)
    await fund(m, p, 500)
    reward = await make_reward(m, max_per_promoter=1)
    assert (await redeem(p, reward["id"])).status_code == 201
    r = await redeem(p, reward["id"])
    assert r.status_code == 400 and error_code(r) == "redeem_limit_reached"
    item = (await p.client.get(f"{API}/promoter/rewards")).json()["items"][0]
    assert (
        item["my_redemptions_count"] == 1
        and item["available"] is False
        and item["can_afford"] is True
    )


async def test_redeem_is_idempotent_by_request_id():
    m = await new_manager(connect=False)
    p = await new_promoter(m)
    await fund(m, p, 300)
    reward = await make_reward(m)
    rid = str(uuid.uuid4())
    first = await redeem(p, reward["id"], rid)
    second = await redeem(p, reward["id"], rid)
    assert first.status_code == second.status_code == 201
    assert (
        first.json()["id"] == second.json()["id"] and first.json()["code"] == second.json()["code"]
    )
    assert await p.balance() == 200
    assert (await m.client.get(f"{API}/rewards")).json()["items"][0]["stock"] == 4
    # concorrente com o mesmo request_id
    rid2 = str(uuid.uuid4())
    res = await asyncio.gather(*[redeem(p, reward["id"], rid2) for _ in range(5)])
    assert {r.status_code for r in res} == {201}
    assert len({r.json()["id"] for r in res}) == 1
    assert await p.balance() == 100


async def test_concurrent_redeems_of_last_unit_give_exactly_one_success():
    m = await new_manager(connect=False)
    promoters = [await new_promoter(m, username=f"conc.user{i}") for i in range(4)]
    for p in promoters:
        await fund(m, p, 200)
    reward = await make_reward(m, stock=1)
    results = await asyncio.gather(*[redeem(p, reward["id"]) for p in promoters])
    codes = sorted(r.status_code for r in results)
    assert codes == [201, 400, 400, 400]
    assert all(error_code(r) == "out_of_stock" for r in results if r.status_code == 400)
    assert (await m.client.get(f"{API}/rewards")).json()["items"][0]["stock"] == 0
    async with SessionLocal() as db:
        bal = (await db.execute(select(func.sum(Membership.points_balance)))).scalar()
        spent = await db.scalar(
            select(func.sum(PointTransaction.amount)).where(PointTransaction.type == "redeem")
        )
    assert bal == 4 * 200 - 100 and spent == -100


async def test_concurrent_redeems_never_overspend_balance():
    m = await new_manager(connect=False)
    p = await new_promoter(m)
    await fund(m, p, 150)
    reward = await make_reward(m, stock=None)
    results = await asyncio.gather(*[redeem(p, reward["id"]) for _ in range(5)])
    assert sorted(r.status_code for r in results) == [201, 400, 400, 400, 400]
    assert await p.balance() == 50


async def test_cancel_refunds_points_and_restocks():
    m = await new_manager(connect=False)
    p = await new_promoter(m)
    await fund(m, p, 200)
    reward = await make_reward(m, stock=3, max_per_promoter=1)
    red = (await redeem(p, reward["id"])).json()
    assert await p.balance() == 100
    c = await m.client.post(
        f"{API}/redemptions/{red['id']}/cancel", json={"note": "Sem estoque físico"}
    )
    assert c.status_code == 200 and c.json()["status"] == "cancelled"
    assert await p.balance() == 200
    rw = (await m.client.get(f"{API}/rewards")).json()["items"][0]
    assert rw["stock"] == 3 and rw["redeemed_count"] == 0
    tx = (await p.client.get(f"{API}/promoter/transactions")).json()["items"]
    assert [t["type"] for t in tx][:2] == ["refund", "redeem"] or "refund" in {
        t["type"] for t in tx
    }
    again = await m.client.post(f"{API}/redemptions/{red['id']}/cancel")
    assert again.status_code == 400 and error_code(again) == "redemption_not_pending"
    # cancelado nao conta para o limite por promoter
    assert (await redeem(p, reward["id"])).status_code == 201
    pn = (await p.client.get(f"{API}/notifications")).json()["items"]
    assert any(n["type"] == "redemption_cancelled" for n in pn)


async def test_adjust_points_negative_beyond_balance_is_400_not_500():
    m = await new_manager(connect=False)
    p = await new_promoter(m)
    mem = await p.membership()
    await fund(m, p, 30)
    r = await m.client.post(
        f"{API}/team/members/{mem['id']}/adjust-points", json={"amount": -31, "reason": "Correção"}
    )
    assert r.status_code == 400 and error_code(r) == "insufficient_points"
    ok = await m.client.post(
        f"{API}/team/members/{mem['id']}/adjust-points", json={"amount": -30, "reason": "Correção"}
    )
    assert ok.status_code == 200 and ok.json()["points_balance"] == 0
    zero = await m.client.post(
        f"{API}/team/members/{mem['id']}/adjust-points", json={"amount": 0, "reason": "Nada"}
    )
    assert zero.status_code == 422 and "amount" in zero.json()["error"]["fields"]
    async with SessionLocal() as db:
        assert (await db.scalar(select(func.min(PointTransaction.balance_after)))) >= 0


async def test_pending_member_cannot_redeem_or_adjust():
    m = await new_manager(connect=False)
    p = await new_promoter(m, approve=False)
    reward = await make_reward(m)
    r = await redeem(p, reward["id"])
    assert r.status_code == 403 and error_code(r) == "membership_not_approved"
    mem = await p.membership()
    r = await m.client.post(
        f"{API}/team/members/{mem['id']}/adjust-points",
        json={"amount": 10, "reason": "Teste ajuste"},
    )
    assert r.status_code == 400


async def test_reward_delete_archives_when_it_has_redemptions():
    m = await new_manager(connect=False)
    p = await new_promoter(m)
    await fund(m, p, 200)
    used = await make_reward(m, name="Usada")
    unused = await make_reward(m, name="Nunca usada")
    assert (await redeem(p, used["id"])).status_code == 201
    assert (await m.client.delete(f"{API}/rewards/{used['id']}")).status_code == 204
    assert (await m.client.delete(f"{API}/rewards/{unused['id']}")).status_code == 204
    names = [
        r["name"]
        for r in (await m.client.get(f"{API}/rewards", params={"include_inactive": True})).json()[
            "items"
        ]
    ]
    assert names == []
    # o resgate antigo continua visivel
    assert (await m.client.get(f"{API}/redemptions")).json()["total"] == 1
    r = await redeem(p, used["id"])
    assert r.status_code in (400, 404)


async def test_reward_validation_rules():
    m = await new_manager(connect=False)
    r = await m.client.post(f"{API}/rewards", json={"name": "x", "cost_points": 0})
    assert r.status_code == 422
    assert set(r.json()["error"]["fields"]) == {"name", "cost_points"}
    r = await m.client.post(
        f"{API}/rewards",
        json={"name": "Camiseta", "cost_points": 10, "image_url": "javascript:alert(1)"},
    )
    assert r.status_code == 422 and "image_url" in r.json()["error"]["fields"]
    r = await m.client.patch(f"{API}/rewards/{uuid.uuid4()}", json={"name": "ok nome"})
    assert r.status_code == 404
