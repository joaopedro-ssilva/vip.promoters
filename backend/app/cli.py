"""Tarefas administrativas pela linha de comando.

    python -m app.cli preparar-banco       # migracoes + papel de aplicacao (usa DATABASE_URL_ADMIN)
    python -m app.cli esquecer @fulano     # pedido LGPD de quem comentou e nao tem conta
    python -m app.cli retencao             # roda a politica de retencao agora

No Docker: docker compose exec backend python -m app.cli esquecer @fulano
"""

import asyncio
import os
import re
import subprocess
import sys

import asyncpg

from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.services import privacy, retention

USO = __doc__ or ""


_ROLE_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def _plain_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def prepare_app_role() -> None:
    """Cria/atualiza o papel de aplicacao: LOGIN, sem superusuario, sem BYPASSRLS, sem ser
    dono de nada, so com SELECT/INSERT/UPDATE/DELETE. E ele que faz o RLS valer."""
    role = settings.app_db_user
    if not _ROLE_RE.match(role):
        raise SystemExit("APP_DB_USER invalido")
    if not settings.app_db_password:
        raise SystemExit("APP_DB_PASSWORD e obrigatorio")
    conn = await asyncpg.connect(_plain_dsn(settings.database_url_admin))
    try:
        dbname = await conn.fetchval("SELECT current_database()")
        async with conn.transaction():
            # a senha entra por parametro, nunca concatenada no SQL; o nome do papel e o do
            # banco foram validados/lidos do proprio servidor
            await conn.execute(
                "SELECT set_config('vip.app_pw', $1, true)", settings.app_db_password
            )
            await conn.execute(
                f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                        EXECUTE format('CREATE ROLE %I LOGIN PASSWORD %L', '{role}',
                                       current_setting('vip.app_pw'));
                    ELSE
                        EXECUTE format('ALTER ROLE %I LOGIN PASSWORD %L', '{role}',
                                       current_setting('vip.app_pw'));
                    END IF;
                END $$;
                ALTER ROLE {role} NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
                GRANT CONNECT ON DATABASE "{dbname}" TO {role};
                GRANT USAGE ON SCHEMA public TO {role};
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {role};
                GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role};
                REVOKE ALL ON alembic_version FROM {role};
                ALTER DEFAULT PRIVILEGES IN SCHEMA public
                    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {role};
                """  # noqa: S608
            )
    finally:
        await conn.close()


def prepare_database() -> None:
    if not settings.database_url_admin:
        raise SystemExit("DATABASE_URL_ADMIN e obrigatorio para preparar o banco")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cmd = [sys.executable, "-m", "alembic", "upgrade", "head"]
    subprocess.run(cmd, cwd=root, check=True)  # noqa: S603
    asyncio.run(prepare_app_role())
    print(f"banco pronto; papel de aplicacao: {settings.app_db_user}")


async def _main(args: list[str]) -> int:
    if len(args) == 2 and args[0] == "esquecer":
        async with SessionLocal() as db:
            n = await privacy.forget_instagram_username(db, args[1])
        print(f"{n} interacoes anonimizadas para {args[1]}")
        return 0
    if args == ["retencao"]:
        async with SessionLocal() as db:
            res = await retention.purge(db)
        print(res)
        return 0
    print(USO)
    return 2


def main() -> None:
    if sys.argv[1:] == ["preparar-banco"]:
        prepare_database()
        return

    async def run() -> int:
        try:
            return await _main(sys.argv[1:])
        finally:
            await engine.dispose()

    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
