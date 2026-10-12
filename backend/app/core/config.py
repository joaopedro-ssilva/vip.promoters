"""Configuracao da aplicacao (variaveis de ambiente) e verificacoes de producao."""

import base64
import hashlib
import hmac
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "dev-insecure-secret-key-change-me-0123456789"
DEFAULT_TOKEN_ENCRYPTION_KEY = base64.urlsafe_b64encode(
    b"dev-insecure-fernet-key-00000000"
).decode()
DEFAULT_VERIFY_TOKEN = "dev-verify-token"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    # Padrao "production" de proposito: esquecer ENVIRONMENT no deploy nao pode pular a
    # validate_production (o SECRET_KEY padrao e publico no repositorio e permitiria forjar
    # tokens). Desenvolvimento e testes declaram ENVIRONMENT=development explicitamente.
    environment: Literal["development", "production"] = "production"
    app_url: str = "http://localhost:3000"
    allowed_origins: str = "http://localhost:3000"
    database_url: str = "postgresql+asyncpg://vip:vip@db:5432/vip"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = DEFAULT_SECRET_KEY
    token_encryption_key: str = DEFAULT_TOKEN_ENCRYPTION_KEY
    cookie_secure: bool = False
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    meta_mock_mode: bool = True
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_graph_version: str = "v25.0"
    meta_webhook_verify_token: str = DEFAULT_VERIFY_TOKEN
    sync_interval_seconds: int = 120
    seed_demo: bool = False

    upload_dir: str = "/data/uploads"
    upload_max_bytes: int = 8 * 1024 * 1024
    trusted_proxy_hops: int = 1
    trusted_proxy_cidrs: str = "127.0.0.0/8,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
    sync_page_size: int = 50
    sync_pages_per_run: int = 10
    db_pool_size: int = 10
    db_max_overflow: int = 20
    instagram_media_cache_seconds: int = 60
    log_level: str = "INFO"

    # Limites "tentativas/janela_em_segundos". Em desenvolvimento sao multiplicados
    # por rate_limit_multiplier (0 = automatico: 100 em dev, 1 em producao).
    rate_limit_multiplier: int = 0
    rl_login_ip: str = "20/60"
    rl_login_account: str = "10/300"
    rl_register: str = "10/3600"
    rl_refresh: str = "60/60"
    rl_invite: str = "30/60"
    rl_redeem: str = "10/60"
    rl_sync: str = "6/60"
    rl_upload: str = "20/60"
    rl_simulate: str = "60/60"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def effective_multiplier(self) -> int:
        if self.rate_limit_multiplier > 0:
            return self.rate_limit_multiplier
        return 1 if self.is_production else 100

    @property
    def app_base_url(self) -> str:
        return self.app_url.rstrip("/")

    @property
    def redirect_uri(self) -> str:
        return f"{self.app_base_url}/api/v1/instagram/callback"

    @property
    def webhook_secret(self) -> str:
        """Segredo usado para validar X-Hub-Signature-256.

        Sem META_APP_SECRET (modo mock) usa-se um segredo de desenvolvimento derivado
        de SECRET_KEY: a verificacao nunca e ignorada.
        """
        if self.meta_app_secret:
            return self.meta_app_secret
        if self.meta_mock_mode:
            return hmac.new(
                self.secret_key.encode(), b"dev-webhook-secret", hashlib.sha256
            ).hexdigest()
        return ""

    def rate_limit(self, name: str) -> tuple[int, int]:
        raw = getattr(self, f"rl_{name}")
        limit, window = raw.split("/")
        return int(limit) * self.effective_multiplier, int(window)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def validate_production(s: Settings) -> None:
    """Recusa subir em producao com configuracao insegura."""
    if not s.is_production:
        return
    problems: list[str] = []
    if s.secret_key in ("", DEFAULT_SECRET_KEY) or len(s.secret_key) < 32:
        problems.append("SECRET_KEY ausente, padrao ou curta (minimo 32 caracteres)")
    if s.token_encryption_key in ("", DEFAULT_TOKEN_ENCRYPTION_KEY):
        problems.append("TOKEN_ENCRYPTION_KEY ausente ou padrao")
    if s.meta_webhook_verify_token in ("", DEFAULT_VERIFY_TOKEN):
        problems.append("META_WEBHOOK_VERIFY_TOKEN ausente ou padrao")
    if s.meta_mock_mode:
        problems.append("META_MOCK_MODE=true nao e permitido em producao")
    elif not s.meta_app_id or not s.meta_app_secret:
        problems.append("META_APP_ID e META_APP_SECRET sao obrigatorios em producao")
    if not s.cookie_secure:
        problems.append("COOKIE_SECURE=false nao e permitido em producao")
    if s.seed_demo:
        problems.append("SEED_DEMO=true nao e permitido em producao")
    if problems:
        raise RuntimeError("Configuracao insegura para producao: " + "; ".join(problems))
