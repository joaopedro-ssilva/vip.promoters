"""Simulador (registrado SOMENTE com META_MOCK_MODE=true)."""

import base64
import re
import secrets
import uuid
from datetime import UTC, datetime
from urllib.parse import urlencode

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from app.api.deps import DB, Manager
from app.core.config import settings
from app.core.errors import AppError
from app.core.rate_limit import check_rate_limit
from app.schemas.models import InteractionEnvelope, SimulateCommentIn, SimulateStoryIn
from app.services.campaigns import get_org_campaign, require_account
from app.services.instagram.mock import MOCK_SCOPED_PREFIX, mock_store_comment
from app.services.interactions import normalize_username, process_event
from app.services.views import load_interaction
from app.services.webhooks import parse_payload

router = APIRouter(prefix="/dev", tags=["dev"])
_HINT_RE = re.compile(r"^[a-z0-9._]{1,30}$")


@router.get("/instagram/authorize")
async def mock_authorize(
    state: str = Query(..., max_length=512),
    redirect_uri: str = Query(..., max_length=512),
    hint: str = Query("conta.demo", max_length=30),
):
    if redirect_uri != settings.redirect_uri:
        raise AppError(400, "validation_error", "redirect_uri inválido.")
    hint = hint.lower()
    if not _HINT_RE.match(hint):
        hint = "conta.demo"
    code = "mock-" + base64.urlsafe_b64encode(hint.encode()).decode().rstrip("=")
    return RedirectResponse(
        f"{redirect_uri}?{urlencode({'code': code, 'state': state})}", status_code=302
    )


async def _run(db, payload: dict):
    """Entrega o payload ao MESMO pipeline do webhook real."""
    last = None
    for ev in parse_payload(payload):
        res = await process_event(db, ev)
        if res.interaction is not None:
            last = res.interaction
    if last is None:
        raise AppError(400, "validation_error", "O evento simulado foi descartado pelo pipeline.")
    return last


@router.post("/simulate/comment", response_model=InteractionEnvelope)
async def simulate_comment(body: SimulateCommentIn, ctx: Manager, db: DB):
    await check_rate_limit("simulate", f"user:{ctx.user.id}")
    campaign = await get_org_campaign(db, ctx.org.id, body.campaign_id)
    account = await require_account(db, ctx.org)
    if not campaign.ig_media_id:
        raise AppError(400, "campaign_not_active", "A campanha ainda não tem post vinculado.")
    username = normalize_username(body.username) or "anonimo"
    now = datetime.now(UTC)
    comment_id = f"mock_c_{uuid.uuid4().hex[:16]}"
    from_id = f"{MOCK_SCOPED_PREFIX}{username}"
    await mock_store_comment(
        account.ig_user_id, campaign.ig_media_id, comment_id, username, from_id, body.text, now
    )
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": account.ig_user_id,
                "time": int(now.timestamp()),
                "changes": [
                    {
                        "field": "comments",
                        "value": {
                            "from": {"id": from_id, "username": username},
                            "media": {
                                "id": campaign.ig_media_id,
                                "media_product_type": "FEED",
                            },
                            "id": comment_id,
                            "text": body.text,
                        },
                    }
                ],
            }
        ],
    }
    it = await _run(db, payload)
    return InteractionEnvelope(interaction=await load_interaction(db, it.id))


@router.post("/simulate/story-mention", response_model=InteractionEnvelope)
async def simulate_story(body: SimulateStoryIn, ctx: Manager, db: DB):
    await check_rate_limit("simulate", f"user:{ctx.user.id}")
    account = await require_account(db, ctx.org)
    username = normalize_username(body.username) or "anonimo"
    now = datetime.now(UTC)
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": account.ig_user_id,
                "time": int(now.timestamp()),
                "messaging": [
                    {
                        "sender": {"id": f"{MOCK_SCOPED_PREFIX}{username}"},
                        "recipient": {"id": account.ig_user_id},
                        "timestamp": int(now.timestamp() * 1000),
                        "message": {
                            "mid": f"mock_m_{secrets.token_hex(12)}",
                            "attachments": [
                                {
                                    "type": "story_mention",
                                    "payload": {
                                        "url": f"https://picsum.photos/seed/{secrets.token_hex(4)}/540/960"
                                    },
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }
    it = await _run(db, payload)
    return InteractionEnvelope(interaction=await load_interaction(db, it.id))
