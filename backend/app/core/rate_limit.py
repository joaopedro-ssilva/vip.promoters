"""Rate limiting em Redis (janela fixa) com fallback em memoria se o Redis cair."""

import ipaddress
import logging
import threading
import time
from functools import lru_cache

from fastapi import Request

from app.core.config import settings
from app.core.errors import AppError
from app.core.redis import get_redis

log = logging.getLogger("app.rate_limit")


@lru_cache
def _trusted_networks(raw: str) -> tuple[ipaddress._BaseNetwork, ...]:
    nets = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            nets.append(ipaddress.ip_network(part, strict=False))
    return tuple(nets)


def _is_trusted_peer(peer: str) -> bool:
    try:
        addr = ipaddress.ip_address(peer)
    except ValueError:
        return False
    return any(addr in net for net in _trusted_networks(settings.trusted_proxy_cidrs))


def client_ip(request: Request) -> str:
    """IP do cliente. X-Forwarded-For so e considerado quando o peer direto esta em
    TRUSTED_PROXY_CIDRS; nesse caso usa-se o n-esimo valor a partir da direita
    (TRUSTED_PROXY_HOPS), que o proxy confiavel anexou. Fora disso, o IP do socket."""
    peer = request.client.host if request.client else "unknown"
    hops = settings.trusted_proxy_hops
    if hops > 0 and _is_trusted_peer(peer):
        xff = request.headers.get("x-forwarded-for")
        if xff:
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if len(parts) >= hops:
                return parts[-hops][:64]
    return peer


# ---------------------------------------------------------------- fallback em memoria

_mem_lock = threading.Lock()
_mem: dict[str, tuple[int, int]] = {}  # chave -> (bucket, contagem)


def _memory_hit(redis_key: str, bucket: int) -> int:
    with _mem_lock:
        if len(_mem) > 50_000:  # nunca cresce sem limite
            _mem.clear()
        cur_bucket, count = _mem.get(redis_key, (bucket, 0))
        if cur_bucket != bucket:
            cur_bucket, count = bucket, 0
        count += 1
        _mem[redis_key] = (cur_bucket, count)
        return count


async def check_rate_limit(name: str, key: str) -> None:
    limit, window = settings.rate_limit(name)
    now = int(time.time())
    bucket = now // window
    redis_key = f"rl:{name}:{key}:{bucket}"
    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, window + 1)
        count, _ = await pipe.execute()
    except Exception:  # noqa: BLE001
        # Redis fora: limitador local por processo (nao compartilhado, mas nunca "aberto")
        log.warning("rate limit em modo local (Redis indisponivel)", extra={"event": "rl_local"})
        count = _memory_hit(redis_key, bucket)
    if count > limit:
        retry_after = max(1, (bucket + 1) * window - now)
        raise AppError(
            429,
            "rate_limited",
            "Muitas tentativas. Tente novamente em instantes.",
            headers={"Retry-After": str(retry_after)},
        )


def ip_limit(name: str):
    async def dependency(request: Request) -> None:
        await check_rate_limit(name, f"ip:{client_ip(request)}")

    return dependency
