import uuid
from collections.abc import Iterable

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification


async def notify(
    db: AsyncSession,
    user_id: uuid.UUID,
    type_: str,
    title: str,
    body: str,
    link: str | None = None,
) -> None:
    db.add(Notification(user_id=user_id, type=type_, title=title[:160], body=body, link=link))


async def notify_many(
    db: AsyncSession,
    user_ids: Iterable[uuid.UUID],
    type_: str,
    title: str,
    body: str,
    link: str | None = None,
) -> int:
    rows = [
        {
            "id": uuid.uuid4(),
            "user_id": uid,
            "type": type_,
            "title": title[:160],
            "body": body,
            "link": link,
        }
        for uid in user_ids
    ]
    if rows:
        await db.execute(insert(Notification), rows)
    return len(rows)
