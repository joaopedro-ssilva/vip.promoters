"""Dados de demonstracao (SEED_DEMO=true, so em desenvolvimento, so com a tabela de usuarios vazia).

Tudo passa pelas mesmas funcoes de servico da API, entao saldos e extrato ficam consistentes.
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.config import settings
from app.core.crypto import encrypt
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import (
    Campaign,
    InstagramAccount,
    Membership,
    Organization,
    PromoterProfile,
    Reward,
    User,
)
from app.services import campaigns as campaigns_svc
from app.services import rewards as rewards_svc
from app.services.instagram.mock import mock_ig_user_id
from app.services.interactions import InboundEvent, process_event
from app.services.points import adjust_points

log = logging.getLogger("app.seed")

DEMO_PASSWORD = "Demo@12345"
DEMO_INVITE = "KP7DM42X"
MANAGER_IG = "clubedemo"


async def run_seed() -> bool:
    if settings.is_production or not settings.meta_mock_mode:
        return False
    async with SessionLocal() as db:
        if ((await db.scalar(select(func.count()).select_from(User))) or 0) > 0:
            return False
        await _seed(db)
    log.info("seed de demonstracao concluido")
    return True


async def _seed(db) -> None:
    now = datetime.now(UTC)
    pw = await hash_password(DEMO_PASSWORD)

    manager = User(email="gestor@demo.com", password_hash=pw, name="Gestor Demo", role="manager")
    db.add(manager)
    await db.flush()
    org = Organization(owner_id=manager.id, name="Clube Demo", invite_code=DEMO_INVITE)
    db.add(org)
    ig_user_id = mock_ig_user_id(MANAGER_IG)
    db.add(
        InstagramAccount(
            user_id=manager.id,
            ig_user_id=ig_user_id,
            username=MANAGER_IG,
            name="Clube Demo",
            profile_picture_url=f"https://picsum.photos/seed/{MANAGER_IG}/200/200",
            account_type="BUSINESS",
            followers_count=5400,
            access_token_enc=encrypt(f"mock_token_{MANAGER_IG}_seed0001"),
            token_expires_at=now + timedelta(days=60),
            scopes=["instagram_business_basic", "instagram_business_manage_comments"],
            webhook_subscribed=True,
            status="active",
        )
    )

    promoters = {}
    for email, name, handle, status in (
        ("bia@demo.com", "Bia Santos", "bia.promo", "approved"),
        ("caio@demo.com", "Caio Lima", "caio.vip", "approved"),
        ("duda@demo.com", "Duda Rocha", "duda.eventos", "pending"),
    ):
        u = User(email=email, password_hash=pw, name=name, role="promoter")
        db.add(u)
        await db.flush()
        db.add(PromoterProfile(user_id=u.id, instagram_username=handle))
        m = Membership(
            organization_id=org.id,
            promoter_id=u.id,
            status=status,
            approved_at=now - timedelta(days=12) if status == "approved" else None,
            approved_by=manager.id if status == "approved" else None,
            joined_at=now - timedelta(days=13),
        )
        db.add(m)
        promoters[handle] = (u, m)
    await db.commit()

    account = await campaigns_svc.require_account(db, org)
    media_ids = [m_id for m_id in ("17895000000000100", "17895000000000101", "17895000000000102")]

    def data(title, media_id, **extra):
        return {
            "title": title,
            "description": extra.pop("description", None),
            "instructions": extra.pop("instructions", None),
            "source": "existing",
            "ig_media_id": media_id,
            "points_comment": extra.pop("points_comment", 50),
            "points_story_mention": extra.pop("points_story_mention", 80),
            "max_story_mentions": extra.pop("max_story_mentions", 1),
            **extra,
        }

    active = await campaigns_svc.create_campaign(
        db,
        org,
        data(
            "Sexta VIP: lista aberta",
            media_ids[0],
            description="Comente no post para garantir seu nome na lista.",
            instructions="1) Comente no post. 2) Poste um story marcando @clubedemo.",
            starts_at=now - timedelta(days=10),
        ),
    )
    ended = await campaigns_svc.create_campaign(
        db,
        org,
        data(
            "Aftermovie da última edição",
            media_ids[1],
            description="Campanha anterior, já encerrada.",
            points_comment=40,
            points_story_mention=0,
            starts_at=now - timedelta(days=30),
            ends_at=now - timedelta(days=15),
        ),
    )
    await campaigns_svc.create_campaign(
        db,
        org,
        data(
            "Novo drink da casa (rascunho)",
            media_ids[2],
            points_comment=30,
            points_story_mention=60,
            max_story_mentions=2,
        ),
    )
    await db.commit()
    active = await campaigns_svc.dispatch_campaign(db, org, active.id)
    ended = await campaigns_svc.dispatch_campaign(db, org, ended.id)

    def comment(eid, handle, media_id, text, when):
        return InboundEvent(
            type="comment",
            ig_event_id=f"seed_c_{eid}",
            account_ig_id=account.ig_user_id,
            occurred_at=when,
            from_id=f"mock_{handle}",
            from_username=handle,
            media_id=media_id,
            text=text,
        )

    def story(eid, handle, when):
        return InboundEvent(
            type="story_mention",
            ig_event_id=f"seed_m_{eid}",
            account_ig_id=account.ig_user_id,
            occurred_at=when,
            from_id=f"mock_{handle}",
            media_url=f"https://picsum.photos/seed/story{eid}/540/960",
        )

    events = [
        comment("e1", "bia.promo", media_ids[1], "Que noite foi essa!", now - timedelta(days=20)),
        comment("e2", "caio.vip", media_ids[1], "Melhor edição.", now - timedelta(days=18)),
        comment(
            "a1", "bia.promo", media_ids[0], "Quero ir! Lista aberta?", now - timedelta(days=5)
        ),
        story("s0", "caio.vip", now - timedelta(days=4)),
        comment("a2", "caio.vip", media_ids[0], "Já confirmado!", now - timedelta(days=3)),
        comment("a3", "bia.promo", media_ids[0], "De novo, bora!", now - timedelta(days=2)),
        comment("a4", "fulano.externo", media_ids[0], "Posso ir também?", now - timedelta(days=2)),
        story("s1", "bia.promo", now - timedelta(days=1)),
        story("s2", "caio.vip", now - timedelta(hours=20)),
        comment(
            "a5", "duda.eventos", media_ids[0], "Aguardando aprovação :)", now - timedelta(hours=10)
        ),
    ]
    for ev in events:
        await process_event(db, ev)

    # encerra a campanha antiga e registra um comentario tardio (fora da janela)
    ended_row = await db.get(Campaign, ended.id, populate_existing=True)
    ended_row.status = "ended"
    ended_row.dispatched_at = now - timedelta(days=30)
    await db.commit()
    await process_event(
        db, comment("late", "bia.promo", media_ids[1], "Cheguei tarde...", now - timedelta(hours=5))
    )

    _, caio_m = promoters["caio.vip"]
    _, bia_m = promoters["bia.promo"]
    await adjust_points(db, org.id, caio_m.id, 200, "Bônus de boas-vindas", manager.id)
    await db.commit()

    rewards = [
        Reward(
            organization_id=org.id,
            name="Entrada VIP",
            description="Entrada sem fila em qualquer sexta.",
            cost_points=100,
            stock=20,
            max_per_promoter=1,
            image_url="https://picsum.photos/seed/entrada/600/400",
        ),
        Reward(
            organization_id=org.id,
            name="Camiseta do Clube",
            description="Camiseta oficial, tamanhos P ao GG.",
            cost_points=250,
            stock=10,
            image_url="https://picsum.photos/seed/camiseta/600/400",
        ),
        Reward(
            organization_id=org.id,
            name="Mesa para 4 pessoas",
            description="Reserva de mesa no camarote.",
            cost_points=600,
            stock=0,
            image_url="https://picsum.photos/seed/mesa/600/400",
        ),
        Reward(
            organization_id=org.id,
            name="Drink de boas-vindas",
            description="Um drink por nossa conta.",
            cost_points=40,
            stock=None,
            image_url="https://picsum.photos/seed/drink/600/400",
        ),
    ]
    db.add_all(rewards)
    await db.commit()
    entrada, _, _, drink = rewards

    await rewards_svc.redeem(db, caio_m.id, entrada.id, uuid.uuid4())
    done = await rewards_svc.redeem(db, bia_m.id, drink.id, uuid.uuid4())
    await rewards_svc.fulfill(db, org.id, done.id, manager.id, "Entregue na portaria.")
