"""Row Level Security: o contexto de tenant de cada transacao.

Segunda camada do isolamento entre organizacoes (a primeira e o `where` de cada consulta).
O Postgres so devolve linhas das organizacoes do contexto, mesmo que uma consulta esqueca
o filtro. As policies estao na migration 0003 e leem tres variaveis LOCAIS a transacao
(set_config(..., true): nunca vazam pelo pool de conexoes):

    app.rls_mode   'system' (worker, webhooks, rotas publicas) ou 'tenant'
    app.org_ids    organizacoes visiveis no modo tenant (uuid,uuid,...)
    app.user_id    o usuario logado (ve as proprias participacoes e a propria conta)

Toda transacao comeca aplicando o contexto guardado em `session.info["rls"]` (evento
after_begin). Sessao nova e SYSTEM; `current_user` troca para TENANT assim que autentica.
Sem nenhuma variavel definida (conexao crua, fora da sessao) as policies nao mostram nada.

So vale com o app conectado por um papel SEM superusuario, SEM BYPASSRLS e que NAO e dono
das tabelas (ver `app.cli preparar-banco` e `check_database_role`).
"""

import logging
import uuid
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

log = logging.getLogger("app.rls")

_SET = text(
    "SELECT set_config('app.rls_mode', :mode, true), "
    "set_config('app.org_ids', :orgs, true), "
    "set_config('app.user_id', :user, true)"
)


@dataclass(frozen=True)
class RlsContext:
    mode: str  # system | tenant
    org_ids: tuple[uuid.UUID, ...] = field(default=())
    user_id: uuid.UUID | None = None

    def params(self) -> dict[str, str]:
        return {
            "mode": self.mode,
            "orgs": ",".join(str(o) for o in self.org_ids),
            "user": str(self.user_id) if self.user_id else "",
        }


SYSTEM = RlsContext("system")


class RlsSession(Session):
    """Session que aplica o contexto de RLS no inicio de cada transacao."""


@event.listens_for(RlsSession, "after_begin")
def _apply_on_begin(session: Session, transaction, connection) -> None:  # noqa: ANN001
    ctx: RlsContext = session.info.get("rls", SYSTEM)
    connection.execute(_SET, ctx.params())


async def _apply(db: AsyncSession, ctx: RlsContext) -> None:
    db.info["rls"] = ctx
    if db.in_transaction():
        await db.execute(_SET, ctx.params())


async def set_tenant(db: AsyncSession, user_id: uuid.UUID, org_ids: Iterable[uuid.UUID]) -> None:
    await _apply(db, RlsContext("tenant", tuple(dict.fromkeys(org_ids)), user_id))


async def add_org(db: AsyncSession, org_id: uuid.UUID) -> None:
    """Amplia o contexto atual (ex.: o promoter acabou de entrar numa equipe)."""
    ctx: RlsContext = db.info.get("rls", SYSTEM)
    if ctx.mode == "tenant" and org_id not in ctx.org_ids:
        await _apply(db, RlsContext("tenant", (*ctx.org_ids, org_id), ctx.user_id))


@asynccontextmanager
async def system(db: AsyncSession) -> AsyncIterator[None]:
    """Bloco que age em nome do sistema (atravessa organizacoes de proposito): pipeline do
    Instagram, exclusao de conta, entrada por convite. Restaura o contexto anterior."""
    previous: RlsContext = db.info.get("rls", SYSTEM)
    await _apply(db, SYSTEM)
    try:
        yield
    finally:
        if db.is_active:
            await _apply(db, previous)
        else:
            db.info["rls"] = previous


async def check_database_role(db: AsyncSession, *, strict: bool) -> list[str]:
    """Confere se o papel do banco respeita RLS. Em producao (strict) recusa subir."""
    row = (
        await db.execute(
            text(
                "SELECT r.rolsuper, r.rolbypassrls, "
                "EXISTS (SELECT 1 FROM pg_tables t WHERE t.schemaname = 'public' "
                "AND t.tableowner = current_user) "
                "FROM pg_roles r WHERE r.rolname = current_user"
            )
        )
    ).one()
    problems = []
    if row[0]:
        problems.append("o papel do DATABASE_URL e superusuario")
    if row[1]:
        problems.append("o papel do DATABASE_URL tem BYPASSRLS")
    if row[2]:
        problems.append("o papel do DATABASE_URL e dono das tabelas")
    if problems:
        msg = "RLS sem efeito: " + "; ".join(problems) + ". Use o papel de aplicacao."
        if strict:
            raise RuntimeError(msg)
        log.warning(msg, extra={"event": "rls"})
    return problems
