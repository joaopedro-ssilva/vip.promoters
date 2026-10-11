import itertools
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

from httpx import AsyncClient, Response

from tests.conftest import make_client

PASSWORD = "Senha123"
_counter = itertools.count(1)


def cookie_from(resp: Response, name: str) -> str | None:
    for header in resp.headers.get_list("set-cookie"):
        first = header.split(";", 1)[0]
        k, _, v = first.partition("=")
        if k.strip() == name:
            return v
    return None


def set_cookie_header(resp: Response, name: str) -> str:
    for header in resp.headers.get_list("set-cookie"):
        if header.split("=", 1)[0].strip() == name:
            return header
    raise AssertionError(f"cookie {name} nao enviado")


def error_code(resp: Response) -> str:
    return resp.json()["error"]["code"]


class Manager:
    def __init__(self, client: AsyncClient, user: dict, org_name: str):
        self.client = client
        self.user = user
        self.org = user["organization"]
        self.org_name = org_name

    async def connect_instagram(self) -> dict:
        r = await self.client.post("/api/v1/instagram/connect")
        assert r.status_code == 200, r.text
        url = r.json()["authorize_url"]
        parts = urlsplit(url)
        r = await self.client.get(f"{parts.path}?{parts.query}")
        assert r.status_code == 302, r.text
        loc = urlsplit(r.headers["location"])
        r = await self.client.get(f"{loc.path}?{loc.query}")
        assert r.status_code == 302, r.text
        assert "status=connected" in r.headers["location"], r.headers["location"]
        acc = (await self.client.get("/api/v1/instagram/account")).json()["account"]
        assert acc and acc["status"] == "active"
        return acc

    async def media_ids(self) -> list[str]:
        r = await self.client.get("/api/v1/instagram/media")
        return [m["id"] for m in r.json()["items"]]

    async def campaign(self, *, index: int = 0, dispatch: bool = True, **extra) -> dict:
        media = (await self.media_ids())[index]
        body = {
            "title": f"Campanha {next(_counter)}",
            "source": "existing",
            "ig_media_id": media,
            "points_comment": 50,
            "points_story_mention": 80,
            "max_story_mentions": 1,
            "dispatch": dispatch,
        } | extra
        r = await self.client.post("/api/v1/campaigns", json=body)
        assert r.status_code == 201, r.text
        return r.json()

    async def simulate_comment(self, campaign_id: str, username: str, text: str = "Oi") -> dict:
        r = await self.client.post(
            "/api/v1/dev/simulate/comment",
            json={"campaign_id": campaign_id, "username": username, "text": text},
        )
        assert r.status_code == 200, r.text
        return r.json()["interaction"]

    async def simulate_story(self, username: str) -> dict:
        r = await self.client.post(
            "/api/v1/dev/simulate/story-mention", json={"username": username}
        )
        assert r.status_code == 200, r.text
        return r.json()["interaction"]

    async def member(self, member_id: str) -> dict:
        r = await self.client.get("/api/v1/team/members", params={"limit": 100})
        return next(m for m in r.json()["items"] if m["id"] == member_id)


class Promoter:
    def __init__(self, client: AsyncClient, user: dict, username: str):
        self.client = client
        self.user = user
        self.username = username
        self.membership_id: str | None = None

    async def membership(self) -> dict:
        r = await self.client.get("/api/v1/promoter/memberships")
        return r.json()["items"][0]

    async def balance(self) -> int:
        return (await self.membership())["points_balance"]


async def new_manager(org_name: str | None = None, connect: bool = True) -> Manager:
    n = next(_counter)
    org_name = org_name or f"Clube Teste {n}x"
    c = make_client()
    r = await c.post(
        "/api/v1/auth/register",
        json={
            "name": f"Gestor {n}",
            "email": f"gestor{n}@test.com",
            "password": PASSWORD,
            "role": "manager",
            "organization_name": org_name,
        },
    )
    assert r.status_code == 201, r.text
    m = Manager(c, r.json()["user"], org_name)
    if connect:
        await m.connect_instagram()
    return m


async def new_promoter(
    manager: Manager | None = None, approve: bool = True, username: str | None = None
) -> Promoter:
    n = next(_counter)
    username = username or f"promo.user{n}"
    c = make_client()
    body = {
        "name": f"Promoter {n}",
        "email": f"promoter{n}@test.com",
        "password": PASSWORD,
        "role": "promoter",
        "instagram_username": username,
    }
    if manager is not None:
        body["invite_code"] = manager.org["invite_code"]
    r = await c.post("/api/v1/auth/register", json=body)
    assert r.status_code == 201, r.text
    p = Promoter(c, r.json()["user"], username)
    if manager is not None:
        mem = await p.membership()
        p.membership_id = mem["id"]
        if approve:
            r = await manager.client.post(f"/api/v1/team/members/{mem['id']}/approve")
            assert r.status_code == 200, r.text
    return p


def comment_payload(
    account_ig_id: str, media_id: str, comment_id: str, username: str, *, parent_id=None
) -> dict:
    value = {
        "from": {"id": f"mock_{username}", "username": username},
        "media": {"id": media_id, "media_product_type": "FEED"},
        "id": comment_id,
        "text": "Quero participar",
    }
    if parent_id:
        value["parent_id"] = parent_id
    return {
        "object": "instagram",
        "entry": [
            {
                "id": account_ig_id,
                "time": int(datetime.now(UTC).timestamp()),
                "changes": [{"field": "comments", "value": value}],
            }
        ],
    }


def story_payload(account_ig_id: str, sender: str, mid: str | None = None, *, echo=False) -> dict:
    message = {
        "mid": mid or f"mid_{uuid.uuid4().hex}",
        "attachments": [{"type": "story_mention", "payload": {"url": "https://cdn.test/s.jpg"}}],
    }
    if echo:
        message["is_echo"] = True
    return {
        "object": "instagram",
        "entry": [
            {
                "id": account_ig_id,
                "time": int(datetime.now(UTC).timestamp()),
                "messaging": [
                    {
                        "sender": {"id": sender},
                        "recipient": {"id": account_ig_id},
                        "timestamp": int(datetime.now(UTC).timestamp() * 1000),
                        "message": message,
                    }
                ],
            }
        ],
    }


def iso(delta_days: float = 0) -> str:
    return (datetime.now(UTC) + timedelta(days=delta_days)).isoformat()
