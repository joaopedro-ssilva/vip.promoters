"""Isolamento entre tenants (IDOR): recurso de outra organizacao responde 404."""

import uuid

from tests.helpers import error_code, new_manager, new_promoter

API = "/api/v1"


async def setup_two_tenants():
    a = await new_manager("Clube Alfa")
    b = await new_manager("Clube Beta")
    pa = await new_promoter(a, username="alfa.promo")
    pb = await new_promoter(b, username="beta.promo")
    return a, b, pa, pb


async def test_campaign_isolation():
    a, b, pa, pb = await setup_two_tenants()
    ca = await a.campaign()
    cid = ca["id"]
    # B nao enxerga nada da campanha de A
    assert (await b.client.get(f"{API}/campaigns")).json()["total"] == 0
    for method, path, kw in [
        ("get", f"/campaigns/{cid}", {}),
        ("patch", f"/campaigns/{cid}", {"json": {"title": "Hackeada"}}),
        ("delete", f"/campaigns/{cid}", {}),
        ("post", f"/campaigns/{cid}/dispatch", {}),
        ("post", f"/campaigns/{cid}/end", {}),
        ("post", f"/campaigns/{cid}/sync", {}),
        ("get", f"/campaigns/{cid}/interactions", {}),
        (
            "post",
            "/dev/simulate/comment",
            {"json": {"campaign_id": cid, "username": "x.y", "text": "t"}},
        ),
    ]:
        r = await getattr(b.client, method)(f"{API}{path}", **kw)
        assert r.status_code == 404 and error_code(r) == "not_found", (method, path, r.text)
    # A continua intacta
    assert (await a.client.get(f"{API}/campaigns/{cid}")).json()["title"] == ca["title"]
    # promoter de B nao acessa a campanha de A
    r = await pb.client.get(f"{API}/promoter/campaigns/{cid}")
    assert r.status_code == 404
    assert (await pb.client.get(f"{API}/promoter/campaigns")).json()["total"] == 0
    # promoter de A acessa
    assert (await pa.client.get(f"{API}/promoter/campaigns/{cid}")).status_code == 200


async def test_draft_campaign_hidden_from_promoters():
    a = await new_manager("Clube Alfa")
    p = await new_promoter(a)
    draft = await a.campaign(dispatch=False)
    assert draft["status"] == "draft"
    assert (await p.client.get(f"{API}/promoter/campaigns/{draft['id']}")).status_code == 404
    assert (await p.client.get(f"{API}/promoter/campaigns")).json()["total"] == 0


async def test_member_isolation():
    a, b, pa, pb = await setup_two_tenants()
    mem_a = await pa.membership()
    assert (await b.client.get(f"{API}/team/members")).json()["total"] == 1  # so o promoter de B
    for action in ("approve", "reject", "remove"):
        r = await b.client.post(f"{API}/team/members/{mem_a['id']}/{action}")
        assert r.status_code == 404, action
    r = await b.client.post(
        f"{API}/team/members/{mem_a['id']}/adjust-points", json={"amount": 999, "reason": "Fraude"}
    )
    assert r.status_code == 404
    assert (await pa.membership())["points_balance"] == 0
    assert (await pa.membership())["status"] == "approved"


async def test_reward_and_redemption_isolation():
    a, b, pa, pb = await setup_two_tenants()
    rw = (await a.client.post(f"{API}/rewards", json={"name": "Item A", "cost_points": 10})).json()
    mem_a = await pa.membership()
    await a.client.post(
        f"{API}/team/members/{mem_a['id']}/adjust-points", json={"amount": 100, "reason": "Bônus"}
    )
    red = (
        await pa.client.post(
            f"{API}/promoter/rewards/{rw['id']}/redeem", json={"request_id": str(uuid.uuid4())}
        )
    ).json()

    assert (await b.client.get(f"{API}/rewards")).json()["total"] == 0
    assert (
        await b.client.patch(f"{API}/rewards/{rw['id']}", json={"name": "Hack"})
    ).status_code == 404
    assert (await b.client.delete(f"{API}/rewards/{rw['id']}")).status_code == 404
    assert (await b.client.get(f"{API}/redemptions")).json()["total"] == 0
    for action in ("fulfill", "cancel"):
        r = await b.client.post(f"{API}/redemptions/{red['id']}/{action}", json={})
        assert r.status_code == 404, action
    # promoter de B nao resgata recompensa de A (nao e membro) nem ve a lojinha dela
    r = await pb.client.post(
        f"{API}/promoter/rewards/{rw['id']}/redeem", json={"request_id": str(uuid.uuid4())}
    )
    assert r.status_code == 404
    assert (
        await pb.client.get(f"{API}/promoter/rewards", params={"org_id": a.org["id"]})
    ).status_code == 403
    assert (await pb.client.get(f"{API}/promoter/rewards")).json()["total"] == 0
    # A segue com tudo
    assert (await a.client.get(f"{API}/redemptions")).json()["total"] == 1
    assert (await pa.membership())["points_balance"] == 90


async def test_promoter_only_sees_own_data():
    a = await new_manager("Clube Alfa")
    p1 = await new_promoter(a, username="um.promo")
    p2 = await new_promoter(a, username="dois.promo")
    c = await a.campaign()
    await a.simulate_comment(c["id"], "um.promo")
    await a.simulate_comment(c["id"], "dois.promo")
    d1 = (await p1.client.get(f"{API}/promoter/campaigns/{c['id']}")).json()
    assert d1["my"] == {"comment_done": True, "story_mentions_done": 0, "points_earned": 50}
    assert len(d1["my_interactions"]) == 1 and d1["my_interactions"][0]["ig_username"] == "um.promo"
    assert len((await p1.client.get(f"{API}/promoter/transactions")).json()["items"]) == 1
    # outro promoter nao pode apagar/ler membership alheio
    mem2 = await p2.membership()
    assert (await p1.client.delete(f"{API}/promoter/memberships/{mem2['id']}")).status_code == 404
    # org_id de outra equipe: 403
    other = await new_manager("Clube Beta")
    r = await p1.client.get(f"{API}/promoter/home", params={"org_id": other.org["id"]})
    assert r.status_code == 403 and error_code(r) == "membership_not_approved"


async def test_instagram_media_and_invite_visibility():
    a, b, pa, pb = await setup_two_tenants()
    assert a.org["invite_code"] != b.org["invite_code"]
    r = await pa.client.get(f"{API}/instagram/media")
    assert r.status_code == 403
    pub = await pa.client.get(f"{API}/orgs/invite/{a.org['invite_code'].lower()}")
    assert pub.status_code == 200 and pub.json()["name"] == "Clube Alfa"
    assert pub.json()["promoters_count"] == 1
    assert (await pa.client.get(f"{API}/orgs/invite/NAOEXIST")).status_code == 404
    # rotacionar o convite invalida o antigo
    old = a.org["invite_code"]
    new = (await a.client.post(f"{API}/team/invite/rotate")).json()["invite_code"]
    assert new != old
    assert (await pa.client.get(f"{API}/orgs/invite/{old}")).status_code == 404


async def test_leaderboard_rules():
    a = await new_manager("Clube Alfa")
    p1 = await new_promoter(a, username="um.promo")
    p2 = await new_promoter(a, username="dois.promo")
    p3 = await new_promoter(a, username="tres.promo")
    c = await a.campaign()
    await a.simulate_comment(c["id"], "dois.promo")
    await a.simulate_comment(c["id"], "um.promo")  # mesmo score, chegou depois
    lb = (await a.client.get(f"{API}/team/leaderboard")).json()["items"]
    assert [e["instagram_username"] for e in lb] == ["dois.promo", "um.promo"]  # sem quem tem 0
    assert [e["rank"] for e in lb] == [1, 2]
    me = (await p3.client.get(f"{API}/promoter/leaderboard")).json()
    assert me["me"] == {"rank": 3, "points": 0}
    # resgatar nao reduz o ranking
    rw = (await a.client.post(f"{API}/rewards", json={"name": "Item", "cost_points": 50})).json()
    await p2.client.post(
        f"{API}/promoter/rewards/{rw['id']}/redeem", json={"request_id": str(uuid.uuid4())}
    )
    lb = (await a.client.get(f"{API}/team/leaderboard")).json()["items"]
    assert lb[0]["points"] == 50 and lb[0]["instagram_username"] == "dois.promo"
    assert p1 and p2


async def test_dashboard_has_14_zero_filled_days():
    a = await new_manager("Clube Alfa")
    await new_promoter(a, username="um.promo")
    c = await a.campaign()
    await a.simulate_comment(c["id"], "um.promo")
    d = (await a.client.get(f"{API}/dashboard/manager")).json()
    assert d["instagram_connected"] is True and len(d["interactions_by_day"]) == 14
    assert d["interactions_by_day"][-1]["comments"] == 1
    assert d["kpis"]["promoters_approved"] == 1 and d["kpis"]["campaigns_active"] == 1
    assert d["kpis"]["points_issued_30d"] == 50 and len(d["recent_interactions"]) == 1


async def test_validation_rules_for_campaigns():
    a = await new_manager("Clube Alfa")
    media = (await a.media_ids())[0]
    base = {"title": "Campanha ok", "source": "existing", "ig_media_id": media}
    r = await a.client.post(
        f"{API}/campaigns", json=base | {"points_comment": 0, "points_story_mention": 0}
    )
    assert r.status_code == 422 and "points_story_mention" in r.json()["error"]["fields"]
    r = await a.client.post(f"{API}/campaigns", json=base | {"max_story_mentions": 11})
    assert r.status_code == 422
    r = await a.client.post(f"{API}/campaigns", json={"title": "Campanha ok", "source": "existing"})
    assert r.status_code == 422 and "ig_media_id" in r.json()["error"]["fields"]
    r = await a.client.post(f"{API}/campaigns", json=base)
    assert r.status_code == 201
    c = r.json()
    assert (c["points_comment"], c["points_story_mention"], c["max_story_mentions"]) == (10, 25, 1)
    # draft: pode editar pontos; ativa: nao
    assert (
        await a.client.patch(f"{API}/campaigns/{c['id']}", json={"points_comment": 20})
    ).status_code == 200
    assert (await a.client.post(f"{API}/campaigns/{c['id']}/dispatch")).status_code == 200
    r = await a.client.patch(f"{API}/campaigns/{c['id']}", json={"points_comment": 30})
    assert r.status_code == 400 and error_code(r) == "campaign_not_editable"
    r = await a.client.delete(f"{API}/campaigns/{c['id']}")
    assert r.status_code == 400 and error_code(r) == "campaign_not_editable"
    r = await a.client.post(f"{API}/campaigns/{c['id']}/dispatch")
    assert r.status_code == 400
    assert (await a.client.post(f"{API}/campaigns/{c['id']}/end")).status_code == 200
    r = await a.client.post(f"{API}/campaigns/{c['id']}/end")
    assert r.status_code == 400 and error_code(r) == "campaign_not_active"
    r = await a.client.post(f"{API}/campaigns/{c['id']}/sync")
    assert r.status_code == 400 and error_code(r) == "campaign_not_active"


async def test_publish_campaign_flow_and_instagram_not_connected():
    a = await new_manager("Clube Alfa", connect=False)
    r = await a.client.post(
        f"{API}/campaigns",
        json={
            "title": "Sem IG",
            "source": "publish",
            "image_url": "https://x.test/a.jpg",
            "caption": "oi",
        },
    )
    assert r.status_code == 400 and error_code(r) == "instagram_not_connected"
    await a.connect_instagram()
    r = await a.client.post(
        f"{API}/campaigns",
        json={
            "title": "Publicada",
            "source": "publish",
            "image_url": "https://x.test/a.jpg",
            "caption": "Legenda",
        },
    )
    assert (
        r.status_code == 201 and r.json()["status"] == "draft" and r.json()["ig_media_id"] is None
    )
    d = await a.client.post(f"{API}/campaigns/{r.json()['id']}/dispatch")
    assert d.status_code == 200
    body = d.json()
    assert body["status"] == "active" and body["ig_media_id"] and body["permalink"]
    r = await a.client.post(f"{API}/campaigns", json={"title": "Faltando", "source": "publish"})
    assert r.status_code == 422 and set(r.json()["error"]["fields"]) == {"image_url", "caption"}
