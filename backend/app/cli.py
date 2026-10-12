"""Tarefas administrativas pela linha de comando.

    python -m app.cli esquecer @fulano     # pedido LGPD de quem comentou e nao tem conta
    python -m app.cli retencao             # roda a politica de retencao agora

No Docker: docker compose exec backend python -m app.cli esquecer @fulano
"""

import asyncio
import sys

from app.core.db import SessionLocal, engine
from app.services import privacy, retention

USO = __doc__ or ""


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
    async def run() -> int:
        try:
            return await _main(sys.argv[1:])
        finally:
            await engine.dispose()

    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
