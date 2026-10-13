"""Configuracao da aplicacao (variaveis de ambiente) e verificacoes de producao."""

import base64
import hashlib
import hmac
from functools import lru_cache
from typing import Literal
from urllib.parse import quote

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
    # Banco. O app conecta com o papel de APLICACAO (APP_DB_USER: sem superusuario, sem
    # BYPASSRLS, nao e dono das tabelas): e ele que faz o RLS valer. O dono das tabelas
    # (POSTGRES_USER) so e usado por `python -m app.cli preparar-banco`.
    # As URLs sao montadas a partir das partes; nenhuma senha precisa aparecer numa URL
    # escrita em arquivo. DATABASE_URL / DATABASE_URL_ADMIN, se definidas, tem prioridade.
    database_url: str = ""
    database_url_admin: str = ""
    db_host: str = "localhost"
    db_port: int = 5432
    postgres_db: str = "vip"
    postgres_user: str = ""
    postgres_password: str = ""
    app_db_user: str = "vip_app"
    app_db_password: str = ""
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = DEFAULT_SECRET_KEY
    # Rotacao: chaves ANTERIORES (separadas por virgula) ainda aceitas na leitura. O
    # SECRET_KEY novo assina; os antigos so validam tokens emitidos antes da troca. O
    # TOKEN_ENCRYPTION_KEY novo cifra; os antigos so decifram, e o worker recifra tudo.
    secret_key_previous: str = ""
    token_encryption_key: str = DEFAULT_TOKEN_ENCRYPTION_KEY
    token_encryption_key_previous: str = ""
    cookie_secure: bool = False
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    meta_mock_mode: bool = True
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_graph_version: str = "v25.0"
    meta_webhook_verify_token: str = DEFAULT_VERIFY_TOKEN
    # Chave que assina X-Hub-Signature-256 e signed_request, se for diferente de
    # META_APP_SECRET (no login do Instagram o painel mostra duas chaves).
    meta_webhook_secret: str = ""
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

    # Retencao (dias). Interacoes de campanhas encerradas ha mais de RETENTION_DAYS sao
    # anonimizadas (texto, @, id do Instagram e link do story apagados; pontos e extrato
    # ficam). 0 desliga. Notificacoes lidas e sessoes expiradas tambem sao limpas.
    retention_days: int = 365
    notification_retention_days: int = 90

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
        if self.meta_webhook_secret:
            return self.meta_webhook_secret
        if self.meta_app_secret:
            return self.meta_app_secret
        if self.meta_mock_mode:
            return hmac.new(
                self.secret_key.encode(), b"dev-webhook-secret", hashlib.sha256
            ).hexdigest()
        return ""

    def _pg_url(self, user: str, password: str) -> str:
        auth = quote(user, safe="") + (":" + quote(password, safe="") if password else "")
        return f"postgresql+asyncpg://{auth}@{self.db_host}:{self.db_port}/{self.postgres_db}"

    @property
    def db_url(self) -> str:
        """URL do papel de aplicacao (a que o app e o worker usam)."""
        if self.database_url:
            return self.database_url
        if not self.app_db_password:
            raise RuntimeError("Defina APP_DB_PASSWORD (ou DATABASE_URL) no .env")
        return self._pg_url(self.app_db_user, self.app_db_password)

    @property
    def db_admin_url(self) -> str:
        """URL do dono das tabelas (so migracoes). Vazia se nao configurada."""
        if self.database_url_admin:
            return self.database_url_admin
        if self.postgres_user and self.postgres_password:
            return self._pg_url(self.postgres_user, self.postgres_password)
        return ""

    @property
    def secret_keys(self) -> list[str]:
        """Chave atual primeiro, depois as anteriores (so para validar)."""
        old = [k.strip() for k in self.secret_key_previous.split(",") if k.strip()]
        return [self.secret_key, *old]

    @property
    def encryption_keys(self) -> list[str]:
        old = [k.strip() for k in self.token_encryption_key_previous.split(",") if k.strip()]
        return [self.token_encryption_key, *old]

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
    if (
        DEFAULT_SECRET_KEY in s.secret_keys[1:]
        or DEFAULT_TOKEN_ENCRYPTION_KEY in s.encryption_keys[1:]
    ):
        problems.append("chave padrao de desenvolvimento listada como chave anterior")
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
