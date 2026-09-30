"""Shared FastAPI dependencies.

`current_user` is the single place a request turns into a workspace. Every route
that touches user content depends on it, and every query it feeds is scoped by
`principal.workspace_id` -- there is no longer a default workspace to fall back
to, so a forgotten filter fails loudly instead of quietly reading someone
else's library.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_token
from app.db.postgres import get_session


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    email: str
    workspace_id: UUID
    session_id: UUID


_LOOKUP_SQL = text(
    """
    SELECT s.id AS session_id, s.expires_at, u.id AS user_id, u.email,
           w.id AS workspace_id
      FROM sessions s
      JOIN users u ON u.id = s.user_id
      JOIN workspaces w ON w.owner_id = u.id
     WHERE s.token_hash = :token_hash
     ORDER BY w.created_at
     LIMIT 1
    """
)


async def current_user(
    psb_session: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_session),
) -> Principal:
    if not psb_session:
        raise HTTPException(401, "not signed in")

    row = (
        await session.execute(_LOOKUP_SQL, {"token_hash": hash_token(psb_session)})
    ).first()
    if row is None:
        raise HTTPException(401, "session is not valid")

    now = datetime.now(timezone.utc)
    if row.expires_at <= now:
        # Drop it rather than leaving expired rows to accumulate; there is no
        # cleanup job.
        await session.execute(
            text("DELETE FROM sessions WHERE id = :id"), {"id": row.session_id}
        )
        await session.commit()
        raise HTTPException(401, "session has expired")

    settings = get_settings()
    ttl = timedelta(days=settings.session_ttl_days)
    # Slide the expiry forward, but only past the halfway mark, so an active
    # session stays alive without writing to the table on every request.
    if row.expires_at - now < ttl / 2:
        await session.execute(
            text("UPDATE sessions SET expires_at = :expires_at WHERE id = :id"),
            {"expires_at": now + ttl, "id": row.session_id},
        )
        await session.commit()

    return Principal(
        user_id=row.user_id,
        email=row.email,
        workspace_id=row.workspace_id,
        session_id=row.session_id,
    )
