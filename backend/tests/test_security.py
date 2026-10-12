import io
import json

import pytest
from PIL import Image

from app.core.config import Settings, settings, validate_production
from app.services.webhooks import handle_webhook_payload, sign_body
from tests.helpers import (
    PASSWORD,
    comment_payload,
    error_code,
    new_manager,
    new_promoter,
    story_payload,
)

API = "/api/v1"


# ---------------------------------------------------------------- CSRF


async def test_csrf_header_required_for_mutations(anon):
    r = await anon.post(f"{API}/auth/login", json={"email": "a@test.com", "password": PASSWORD})
    assert r.status_code == 403 and error_code(r) == "csrf_failed"
    # GET nao exige
    assert (await anon.get(f"{API}/config")).status_code == 200


async def test_csrf_origin_must_be_allowed(anon):
    h = {"X-Requested-With": "XMLHttpRequest"}
    body = {"email": "a@test.com", "password": PASSWORD}
    bad = await anon.post(
        f"{API}/auth/login", json=body, headers=h | {"Origin": "https://evil.test"}
    )
    assert bad.status_code == 403 and error_code(bad) == "csrf_failed"
    ok = await anon.post(
        f"{API}/auth/login", json=body, headers=h | {"Origin": "http://localhost:3000"}
    )
    assert ok.status_code == 401  # passou pelo CSRF; credenciais invalidas


async def test_webhooks_and_meta_are_csrf_exempt(anon):
    r = await anon.post(f"{API}/webhooks/instagram", content=b"{}")
    assert r.status_code == 403 and error_code(r) == "forbidden"  # assinatura, nao CSRF


# ---------------------------------------------------------------- envelope


async def test_error_envelope_shapes(client):
    r = await client.get(f"{API}/rota-que-nao-existe")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "not_found", "message": "Recurso não encontrado."}}
    r = await client.post(f"{API}/auth/login", json={"email": "invalido", "password": ""})
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_error" and set(err["fields"]) == {"email", "password"}
    assert err["fields"]["email"] == "E-mail inválido."
    r = await client.put(f"{API}/config")
    assert r.status_code == 405 and error_code(r) == "method_not_allowed"
    r = await client.post(
        f"{API}/auth/login", content=b"{nao json", headers={"Content-Type": "application/json"}
    )
    assert r.status_code == 422 and error_code(r) == "validation_error"


async def test_unhandled_exception_uses_envelope(client, monkeypatch):
    from app.api.v1 import misc

    def boom(**_):
        raise RuntimeError("segredo interno")

    monkeypatch.setattr(misc, "ConfigOut", boom)  # forca excecao em /config
    r = await client.get(f"{API}/config")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"
    assert "segredo" not in r.text


async def test_security_headers(client):
    r = await client.get(f"{API}/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "referrer-policy" in r.headers
    assert "default-src 'none'" in r.headers["content-security-policy"]


# ---------------------------------------------------------------- webhooks


def _signed(payload: dict, secret: str | None = None) -> tuple[bytes, dict]:
    body = json.dumps(payload).encode()
    return body, {
        "X-Hub-Signature-256": sign_body(body, secret or settings.webhook_secret),
        "Content-Type": "application/json",
    }


async def test_webhook_verification_handshake(anon):
    ok = await anon.get(
        f"{API}/webhooks/instagram",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": settings.meta_webhook_verify_token,
            "hub.challenge": "12345",
        },
    )
    assert ok.status_code == 200 and ok.text == "12345"
    bad = await anon.get(
        f"{API}/webhooks/instagram",
        params={"hub.mode": "subscribe", "hub.verify_token": "errado", "hub.challenge": "1"},
    )
    assert bad.status_code == 403


async def test_webhook_signature_accepted_and_rejected(anon, arq):
    payload = comment_payload("111", "m1", "c1", "alguem")
    body, headers = _signed(payload)
    ok = await anon.post(f"{API}/webhooks/instagram", content=body, headers=headers)
    assert ok.status_code == 200
    assert len(arq.jobs) == 1 and arq.jobs[0][0] == "process_webhook"

    for hdrs in (
        {},  # sem assinatura
        {"X-Hub-Signature-256": "sha256=" + "0" * 64},  # errada
        {"X-Hub-Signature-256": sign_body(body, "outro-segredo")},  # segredo errado
        {"X-Hub-Signature-256": sign_body(b"{}", settings.webhook_secret)},  # corpo diferente
    ):
        r = await anon.post(f"{API}/webhooks/instagram", content=body, headers=hdrs)
        assert r.status_code == 403, hdrs
    assert len(arq.jobs) == 1  # nada novo foi enfileirado


async def test_webhook_end_to_end_comment_and_story(anon, arq):
    m = await new_manager()
    p = await new_promoter(m, username="bia.promo")
    c = await m.campaign()
    acc = (await m.client.get(f"{API}/instagram/account")).json()["account"]

    # comment via webhook assinado + processamento (o que o worker faz)
    pay = comment_payload(acc["ig_user_id"], c["ig_media_id"], "c_100", "bia.promo")
    body, headers = _signed(pay)
    assert (
        await anon.post(f"{API}/webhooks/instagram", content=body, headers=headers)
    ).status_code == 200
    await handle_webhook_payload(arq.jobs[-1][1])
    assert await p.balance() == 50

    # reentrega do mesmo webhook: idempotente
    await handle_webhook_payload(pay)
    assert await p.balance() == 50

    # story mention (sender = IGSID simulado, resolvido para username pelo cliente mock)
    await handle_webhook_payload(story_payload(acc["ig_user_id"], "mock_bia.promo", "mid_1"))
    assert await p.balance() == 130
    # echo e eventos desconhecidos sao ignorados
    await handle_webhook_payload(
        story_payload(acc["ig_user_id"], "mock_bia.promo", "mid_2", echo=True)
    )
    await handle_webhook_payload(
        {
            "object": "instagram",
            "entry": [{"id": acc["ig_user_id"], "changes": [{"field": "mentions", "value": {}}]}],
        }
    )
    assert await p.balance() == 130


async def test_webhook_secret_never_empty_in_mock_mode():
    assert settings.meta_app_secret == "" and settings.meta_mock_mode
    assert len(settings.webhook_secret) >= 32


# ---------------------------------------------------------------- uploads


def _png(w=10, h=10) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", (w, h), (255, 0, 0, 128)).save(buf, "PNG")
    return buf.getvalue()


async def test_upload_rejects_non_image_and_accepts_real_image():
    m = await new_manager(connect=False)
    r = await m.client.post(
        f"{API}/uploads/image", files={"file": ("x.png", b"<?php echo 1;", "image/png")}
    )
    assert r.status_code == 400 and error_code(r) == "upload_invalid"
    r = await m.client.post(
        f"{API}/uploads/image",
        files={"file": ("x.svg", b"<svg onload=alert(1)/>", "image/svg+xml")},
    )
    assert r.status_code == 400
    r = await m.client.post(f"{API}/uploads/image", files={"file": ("a.png", _png(), "image/png")})
    assert r.status_code == 201
    url = r.json()["url"]
    assert url.startswith("http://localhost:3000/api/v1/uploads/") and url.endswith(".jpg")
    got = await m.client.get(url.removeprefix("http://localhost:3000"))
    assert got.status_code == 200 and got.headers["content-type"] == "image/jpeg"
    assert got.headers["x-content-type-options"] == "nosniff"
    assert Image.open(io.BytesIO(got.content)).format == "JPEG"


async def test_upload_rejects_huge_dimensions_and_requires_manager():
    m = await new_manager(connect=False)
    r = await m.client.post(
        f"{API}/uploads/image", files={"file": ("big.png", _png(9000, 5), "image/png")}
    )
    assert r.status_code == 400 and error_code(r) == "upload_invalid"
    p = await new_promoter()
    r = await p.client.post(f"{API}/uploads/image", files={"file": ("a.png", _png(), "image/png")})
    assert r.status_code == 403


@pytest.mark.parametrize(
    "name",
    [
        "..%2f..%2fetc%2fpasswd",
        "....//....//etc/passwd",
        "%2e%2e%2fsecret",
        "a.jpg",
        "x" * 32 + ".jpg",
    ],
)
async def test_upload_path_traversal_safe(client, name):
    r = await client.get(f"{API}/uploads/{name}")
    assert r.status_code == 404


# ---------------------------------------------------------------- producao e mock


def test_production_guard_rejects_insecure_config():
    with pytest.raises(RuntimeError) as exc:
        validate_production(
            Settings(
                environment="production",
                secret_key="",
                token_encryption_key="",
                meta_mock_mode=True,
                cookie_secure=False,
            )
        )
    msg = str(exc.value)
    for expected in ("SECRET_KEY", "META_MOCK_MODE", "COOKIE_SECURE", "TOKEN_ENCRYPTION_KEY"):
        assert expected in msg
    good = Settings(
        environment="production",
        secret_key="x" * 40,
        token_encryption_key="y" * 43 + "=",
        meta_webhook_verify_token="verify-token-123",
        meta_mock_mode=False,
        meta_app_id="1",
        meta_app_secret="s",
        cookie_secure=True,
    )
    validate_production(good)  # nao levanta


def test_environment_defaults_to_production(monkeypatch):
    """Sem ENVIRONMENT definido, a configuracao padrao (insegura) e recusada na subida."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    defaults = Settings()
    assert defaults.is_production
    with pytest.raises(RuntimeError):
        validate_production(defaults)


async def test_dev_routes_and_docs_in_mock_mode(client):
    assert (await client.get(f"{API}/config")).json() == {
        "app_name": "VIP Promoters",
        "mock_mode": True,
    }
    assert (await client.get("/docs")).status_code == 200
    assert (await client.get("/openapi.json")).status_code == 200


def test_dev_routes_not_registered_when_mock_off(monkeypatch):
    from app import main

    monkeypatch.setattr(settings, "meta_mock_mode", False)
    app2 = main.create_app()
    assert not any(p.startswith("/api/v1/dev") for p in app2.openapi()["paths"])
    monkeypatch.setattr(settings, "meta_mock_mode", True)
    assert any(p.startswith("/api/v1/dev") for p in main.create_app().openapi()["paths"])


def test_docs_disabled_in_production(monkeypatch):
    from app import main

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "secret_key", "k" * 40)
    monkeypatch.setattr(settings, "token_encryption_key", "z" * 43 + "=")
    monkeypatch.setattr(settings, "meta_webhook_verify_token", "tok-tok-tok")
    monkeypatch.setattr(settings, "meta_mock_mode", False)
    monkeypatch.setattr(settings, "meta_app_id", "1")
    monkeypatch.setattr(settings, "meta_app_secret", "s")
    monkeypatch.setattr(settings, "cookie_secure", True)
    app2 = main.create_app()
    assert app2.docs_url is None and app2.openapi_url is None
