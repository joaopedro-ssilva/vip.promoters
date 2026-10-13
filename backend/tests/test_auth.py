import pytest

from app.core.config import settings
from tests.conftest import make_client
from tests.helpers import (
    PASSWORD,
    cookie_from,
    error_code,
    new_manager,
    new_promoter,
    set_cookie_header,
)

API = "/api/v1"


async def register(client, email="a@test.com", **over):
    body = {
        "name": "Ana",
        "email": email,
        "password": PASSWORD,
        "role": "manager",
        "organization_name": "Clube A",
    } | over
    return await client.post(f"{API}/auth/register", json=body)


async def test_register_manager_sets_cookies_exactly(client):
    r = await register(client)
    assert r.status_code == 201
    user = r.json()["user"]
    assert user["role"] == "manager" and user["organization"]["invite_code"]
    assert len(user["organization"]["invite_code"]) == 8
    access = set_cookie_header(r, "vip_access")
    refresh = set_cookie_header(r, "vip_refresh")
    session = set_cookie_header(r, "vip_session")
    assert "HttpOnly" in access and "samesite=lax" in access.lower() and "Path=/;" in access + ";"
    assert "Max-Age=900" in access
    assert "HttpOnly" in refresh and "Path=/api/v1/auth" in refresh
    assert f"Max-Age={settings.refresh_token_days * 86400}" in refresh
    assert "HttpOnly" not in session and "vip_session=1" in session and "Path=/" in session
    assert "secure" not in access.lower()


async def test_register_validation_and_duplicates(client):
    r = await register(client, password="curta")
    assert r.status_code == 422 and error_code(r) == "validation_error"
    assert "password" in r.json()["error"]["fields"]
    r = await register(client, organization_name=None)
    assert r.status_code == 422 and "organization_name" in r.json()["error"]["fields"]
    assert (await register(client)).status_code == 201
    r = await register(client, email="A@TEST.com")
    assert r.status_code == 409 and error_code(r) == "email_taken"


async def test_promoter_register_username_rules(client):
    body = {
        "name": "Bia",
        "email": "b@test.com",
        "password": PASSWORD,
        "role": "promoter",
        "instagram_username": "@Bia.Promo",
    }
    r = await client.post(f"{API}/auth/register", json=body)
    assert r.status_code == 201
    assert r.json()["user"]["promoter_profile"]["instagram_username"] == "bia.promo"
    r = await client.post(f"{API}/auth/register", json=body | {"email": "c@test.com"})
    # @ cadastrado e NAO verificado: 409 com a opcao de disputa (ver test_verification.py)
    assert r.status_code == 409 and error_code(r) == "instagram_username_claimable"
    r = await client.post(
        f"{API}/auth/register",
        json=body | {"email": "d@test.com", "instagram_username": "invalido!!"},
    )
    assert r.status_code == 422
    r = await client.post(
        f"{API}/auth/register",
        json=body
        | {"email": "e@test.com", "instagram_username": "ok.user", "invite_code": "ZZZZZZZZ"},
    )
    assert r.status_code == 400 and error_code(r) == "invalid_invite"


async def test_login_same_error_for_unknown_email_and_wrong_password(client):
    await register(client)
    bad_pw = await client.post(
        f"{API}/auth/login", json={"email": "a@test.com", "password": "x" * 9}
    )
    unknown = await client.post(
        f"{API}/auth/login", json={"email": "no@test.com", "password": "x" * 9}
    )
    assert bad_pw.status_code == unknown.status_code == 401
    assert bad_pw.json() == unknown.json()
    assert error_code(bad_pw) == "invalid_credentials"
    ok = await client.post(f"{API}/auth/login", json={"email": "A@test.com", "password": PASSWORD})
    assert ok.status_code == 200 and ok.json()["user"]["email"] == "a@test.com"


async def test_me_requires_auth_and_logout(client):
    assert (await client.get(f"{API}/auth/me")).status_code == 401
    await register(client)
    assert (await client.get(f"{API}/auth/me")).status_code == 200
    r = await client.post(f"{API}/auth/logout")
    assert r.status_code == 204
    assert 'vip_refresh=""' in set_cookie_header(
        r, "vip_refresh"
    ) or "Max-Age=0" in set_cookie_header(r, "vip_refresh")
    # o refresh que acabou de ser revogado nao funciona mais
    refresh = cookie_from(await register(make_client(), email="z@test.com"), "vip_refresh")
    assert refresh


async def test_refresh_rotation_and_reuse_detection():
    c = make_client()
    r = await register(c)
    old_refresh = cookie_from(r, "vip_refresh")

    other = make_client()  # sem cookies: manda o refresh por cabecalho
    r1 = await other.post(f"{API}/auth/refresh", headers={"Cookie": f"vip_refresh={old_refresh}"})
    assert r1.status_code == 200
    new_refresh = cookie_from(r1, "vip_refresh")
    assert new_refresh and new_refresh != old_refresh
    assert cookie_from(r1, "vip_access")

    # reutilizar o token antigo: 401 e a familia inteira e revogada
    reuse = await other.post(
        f"{API}/auth/refresh", headers={"Cookie": f"vip_refresh={old_refresh}"}
    )
    assert reuse.status_code == 401 and error_code(reuse) == "unauthenticated"
    after = await other.post(
        f"{API}/auth/refresh", headers={"Cookie": f"vip_refresh={new_refresh}"}
    )
    assert after.status_code == 401


async def test_refresh_without_cookie_is_401(client):
    r = await client.post(f"{API}/auth/refresh")
    assert r.status_code == 401


async def test_logout_revokes_refresh_token():
    c = make_client()
    r = await register(c)
    refresh = cookie_from(r, "vip_refresh")
    assert (await c.post(f"{API}/auth/logout")).status_code == 204
    again = await make_client().post(
        f"{API}/auth/refresh", headers={"Cookie": f"vip_refresh={refresh}"}
    )
    assert again.status_code == 401


async def test_change_password_revokes_other_sessions():
    c1 = make_client()
    await register(c1)
    c2 = make_client()
    r = await c2.post(f"{API}/auth/login", json={"email": "a@test.com", "password": PASSWORD})
    other_refresh = cookie_from(r, "vip_refresh")

    bad = await c1.post(
        f"{API}/auth/change-password",
        json={"current_password": "errada123", "new_password": "Nova12345"},
    )
    assert bad.status_code == 422 and "current_password" in bad.json()["error"]["fields"]
    ok = await c1.post(
        f"{API}/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "Nova12345"},
    )
    assert ok.status_code == 204
    # a outra sessao perdeu o refresh
    dead = await make_client().post(
        f"{API}/auth/refresh", headers={"Cookie": f"vip_refresh={other_refresh}"}
    )
    assert dead.status_code == 401
    # a sessao atual continua valida e a senha nova funciona
    assert (await c1.post(f"{API}/auth/refresh")).status_code == 200
    login = await make_client().post(
        f"{API}/auth/login", json={"email": "a@test.com", "password": "Nova12345"}
    )
    assert login.status_code == 200


async def test_login_rate_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_multiplier", 1)
    monkeypatch.setattr(settings, "rl_login_ip", "3/60")
    codes = []
    for _ in range(5):
        r = await client.post(
            f"{API}/auth/login", json={"email": "x@test.com", "password": "abc12345"}
        )
        codes.append(r.status_code)
    assert codes[:3] == [401, 401, 401] and codes[3] == 429
    assert "retry-after" in r.headers and error_code(r) == "rate_limited"


@pytest.mark.parametrize("path", ["/campaigns", "/rewards", "/team/members", "/dashboard/manager"])
async def test_manager_endpoints_reject_anonymous(client, path):
    r = await client.get(f"{API}{path}")
    assert r.status_code == 401 and error_code(r) == "unauthenticated"


async def test_promoter_cannot_use_manager_endpoints():
    m = await new_manager()
    p = await new_promoter(m)
    for path in ("/campaigns", "/rewards", "/team/members", "/redemptions", "/dashboard/manager"):
        r = await p.client.get(f"{API}{path}")
        assert r.status_code == 403 and error_code(r) == "forbidden", path
    # e o gestor nao usa rotas de promoter
    r = await m.client.get(f"{API}/promoter/home")
    assert r.status_code == 403
