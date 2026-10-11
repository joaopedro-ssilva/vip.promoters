import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models import Interaction, Membership, PointTransaction
from app.services.instagram.mock import mock_store_comment
from app.services.interactions import InboundEvent, process_event
from app.services.webhooks import handle_webhook_payload
from tests.helpers import comment_payload, new_manager, new_promoter, story_payload

API = "/api/v1"


async def interactions(m, campaign_id, **params):
    r = await m.client.get(f"{API}/campaigns/{campaign_id}/interactions", params=params)
    assert r.status_code == 200
    return r.json()["items"]


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


async def test_comment_awards_points_and_writes_ledger():
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    c = await m.campaign()
    assert c["status"] == "active" and c["starts_at"]

    it = await m.simulate_comment(c["id"], "@Bia.Promo")
    assert it["status"] == "awarded" and it["points_awarded"] == 50
    assert it["promoter"]["name"] == p.user["name"]
    assert await p.balance() == 50

    tx = (await p.client.get(f"{API}/promoter/transactions")).json()["items"]
    assert (
        [t["type"] for t in tx] == ["earn"]
        and tx[0]["amount"] == 50
        and tx[0]["balance_after"] == 50
    )
    notes = (await p.client.get(f"{API}/notifications")).json()
    assert notes["unread_count"] >= 1 and any(n["type"] == "points_earned" for n in notes["items"])

    stats = (await m.client.get(f"{API}/campaigns/{c['id']}")).json()["stats"]
    assert stats == {
        "comments_awarded": 1,
        "story_mentions_awarded": 0,
        "participants": 1,
        "points_issued": 50,
        "unmatched": 0,
    }


async def test_second_comment_is_duplicate():
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    c = await m.campaign()
    assert (await m.simulate_comment(c["id"], "bia.promo"))["status"] == "awarded"
    second = await m.simulate_comment(c["id"], "bia.promo", "de novo")
    assert second["status"] == "duplicate" and second["points_awarded"] == 0
    assert await p.balance() == 50


async def test_unknown_username_is_unmatched_then_rematched_after_approval():
    m = await new_manager()
    c = await m.campaign()
    it = await m.simulate_comment(c["id"], "nova.pessoa")
    assert it["status"] == "unmatched" and it["promoter"] is None

    p = await new_promoter(m, approve=False, username="nova.pessoa")
    # pendente ainda nao conta
    assert (await interactions(m, c["id"], status="unmatched"))[0]["id"] == it["id"]
    mem = await p.membership()
    r = await m.client.post(f"{API}/team/members/{mem['id']}/approve")
    assert r.status_code == 200 and r.json()["points_balance"] == 50
    awarded = await interactions(m, c["id"], status="awarded")
    assert [i["id"] for i in awarded] == [it["id"]]
    assert await p.balance() == 50


async def test_comment_on_ended_campaign_is_out_of_window():
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    c = await m.campaign()
    assert (await m.client.post(f"{API}/campaigns/{c['id']}/end")).status_code == 200
    it = await m.simulate_comment(c["id"], "bia.promo")
    assert it["status"] == "out_of_window" and it["points_awarded"] == 0
    assert await p.balance() == 0


async def test_comment_outside_time_window_is_out_of_window():
    m = await new_manager()
    await new_promoter(m, username="bia.promo")
    c = await m.campaign(starts_at=(datetime.now(UTC) + timedelta(days=1)).isoformat())
    it = await m.simulate_comment(c["id"], "bia.promo")
    assert it["status"] == "out_of_window"


async def test_replies_and_own_comments_are_ignored():
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    c = await m.campaign()
    acc = (await m.client.get(f"{API}/instagram/account")).json()["account"]
    await handle_webhook_payload(
        comment_payload(
            acc["ig_user_id"], c["ig_media_id"], "reply_1", "bia.promo", parent_id="c_0"
        )
    )
    await handle_webhook_payload(
        comment_payload(acc["ig_user_id"], c["ig_media_id"], "own_1", acc["username"])
    )
    await handle_webhook_payload(  # post sem campanha
        comment_payload(acc["ig_user_id"], "999999", "other_1", "bia.promo")
    )
    await handle_webhook_payload(  # conta desconhecida
        comment_payload("00000", c["ig_media_id"], "unk_1", "bia.promo")
    )
    assert await interactions(m, c["id"]) == []
    assert await p.balance() == 0


async def test_campaign_with_zero_comment_points_ignores_comments():
    m = await new_manager()
    await new_promoter(m, username="bia.promo")
    c = await m.campaign(points_comment=0, points_story_mention=30)
    r = await m.client.post(
        f"{API}/dev/simulate/comment",
        json={"campaign_id": c["id"], "username": "bia.promo", "text": "x"},
    )
    assert r.status_code == 400  # descartado pelo pipeline (nao armazenado)
    assert await interactions(m, c["id"]) == []


async def test_story_mention_awards_and_respects_limit():
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    c = await m.campaign()
    first = await m.simulate_story("bia.promo")
    assert first["status"] == "awarded" and first["points_awarded"] == 80
    assert first["campaign_id"] == c["id"] and first["type"] == "story_mention"
    second = await m.simulate_story("bia.promo")
    assert second["status"] == "duplicate" and second["points_awarded"] == 0
    assert await p.balance() == 80

    unknown = await m.simulate_story("ninguem.aqui")
    assert unknown["status"] == "unmatched"


async def test_story_mention_goes_to_next_campaign_when_first_is_at_limit():
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    older = await m.campaign(index=0)
    newer = await m.campaign(index=1, points_story_mention=100)
    first = await m.simulate_story("bia.promo")
    assert first["campaign_id"] == newer["id"] and first["points_awarded"] == 100  # mais recente
    second = await m.simulate_story("bia.promo")
    assert second["campaign_id"] == older["id"] and second["points_awarded"] == 80
    third = await m.simulate_story("bia.promo")
    assert third["status"] == "duplicate"
    assert await p.balance() == 180


async def test_story_mention_without_active_campaign_is_out_of_window_without_campaign():
    m = await new_manager()
    await new_promoter(m, username="bia.promo")
    it = await m.simulate_story("bia.promo")
    assert it["status"] == "out_of_window" and it["campaign_id"] is None


async def test_idempotent_replay_of_same_event():
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    c = await m.campaign()
    acc = (await m.client.get(f"{API}/instagram/account")).json()["account"]
    ev = event(acc["ig_user_id"], c["ig_media_id"], "same_event", "bia.promo")
    for _ in range(3):
        async with SessionLocal() as db:
            res = await process_event(db, ev)
        assert res.interaction is not None
    assert await p.balance() == 50
    async with SessionLocal() as db:
        n = await db.scalar(select(func.count()).select_from(Interaction))
        txs = await db.scalar(select(func.count()).select_from(PointTransaction))
    assert n == 1 and txs == 1


async def test_concurrent_same_event_awards_once():
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    c = await m.campaign()
    acc = (await m.client.get(f"{API}/instagram/account")).json()["account"]
    ev = event(acc["ig_user_id"], c["ig_media_id"], "race_event", "bia.promo")

    async def run():
        async with SessionLocal() as db:
            return await process_event(db, ev)

    results = await asyncio.gather(*[run() for _ in range(8)])
    assert sum(1 for r in results if r.outcome == "created") == 1
    assert await p.balance() == 50
    async with SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(Interaction)) == 1


async def test_concurrent_distinct_comments_for_same_promoter_award_once():
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    c = await m.campaign()
    acc = (await m.client.get(f"{API}/instagram/account")).json()["account"]

    async def run(i: int):
        async with SessionLocal() as db:
            return await process_event(
                db, event(acc["ig_user_id"], c["ig_media_id"], f"cmt_{i}", "bia.promo")
            )

    results = await asyncio.gather(*[run(i) for i in range(10)])
    statuses = sorted(r.interaction.status for r in results)
    assert statuses.count("awarded") == 1 and statuses.count("duplicate") == 9
    assert await p.balance() == 50
    async with SessionLocal() as db:
        total = await db.scalar(select(func.sum(PointTransaction.amount)))
        bal = await db.scalar(select(Membership.points_balance))
    assert total == bal == 50


async def test_polling_sync_picks_up_comments_and_is_idempotent():
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    c = await m.campaign(starts_at=(datetime.now(UTC) - timedelta(days=1)).isoformat())
    acc = (await m.client.get(f"{API}/instagram/account")).json()["account"]
    now = datetime.now(UTC)
    # comentarios que chegaram so ao "Instagram" (sem webhook), fora de ordem
    await mock_store_comment(
        acc["ig_user_id"], c["ig_media_id"], "poll_2", "bia.promo", "mock_bia.promo", "dois", now
    )
    await mock_store_comment(
        acc["ig_user_id"],
        c["ig_media_id"],
        "poll_1",
        "bia.promo",
        "mock_bia.promo",
        "um",
        now - timedelta(minutes=5),
    )
    await mock_store_comment(
        acc["ig_user_id"], c["ig_media_id"], "poll_3", "fulano", "mock_fulano", "tres", now
    )

    r = await m.client.post(f"{API}/campaigns/{c['id']}/sync")
    assert r.status_code == 200
    assert r.json() == {"fetched": 3, "new_interactions": 3, "awarded": 1}
    assert await p.balance() == 50
    # o primeiro comentario (mais antigo) e o premiado
    awarded = await interactions(m, c["id"], status="awarded")
    assert awarded[0]["text"] == "um"
    again = await m.client.post(f"{API}/campaigns/{c['id']}/sync")
    assert again.json() == {"fetched": 3, "new_interactions": 0, "awarded": 0}


async def test_dispatch_notifies_approved_promoters_and_join_request_notifies_manager():
    m = await new_manager()
    approved = await new_promoter(m, username="ap.rovado")
    pending = await new_promoter(m, approve=False, username="pen.dente")
    mnotes = (await m.client.get(f"{API}/notifications")).json()["items"]
    assert sum(1 for n in mnotes if n["type"] == "join_request") == 2

    c = await m.campaign()
    got = (await approved.client.get(f"{API}/notifications")).json()["items"]
    assert any(n["type"] == "campaign_dispatched" and c["id"] in n["link"] for n in got)
    assert not any(
        n["type"] == "campaign_dispatched"
        for n in (await pending.client.get(f"{API}/notifications")).json()["items"]
    )
    # leitura
    nid = got[0]["id"]
    assert (await approved.client.post(f"{API}/notifications/{nid}/read")).status_code == 204
    assert (await approved.client.post(f"{API}/notifications/read-all")).status_code == 204
    assert (await approved.client.get(f"{API}/notifications")).json()["unread_count"] == 0


async def test_membership_approval_and_rejection_notify_promoter():
    m = await new_manager()
    p1 = await new_promoter(m, approve=False, username="um.user")
    p2 = await new_promoter(m, approve=False, username="dois.user")
    await m.client.post(f"{API}/team/members/{(await p1.membership())['id']}/approve")
    await m.client.post(f"{API}/team/members/{(await p2.membership())['id']}/reject")
    t1 = [n["type"] for n in (await p1.client.get(f"{API}/notifications")).json()["items"]]
    t2 = [n["type"] for n in (await p2.client.get(f"{API}/notifications")).json()["items"]]
    assert "membership_approved" in t1 and "membership_rejected" in t2
    p1_story = await m.simulate_story("um.user")  # aprovado participa
    assert p1_story["status"] in ("awarded", "out_of_window")
    assert story_payload  # helper importado
