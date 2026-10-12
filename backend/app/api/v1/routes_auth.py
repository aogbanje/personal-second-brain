"""Signup, login, logout.

Sessions live in an httpOnly cookie carrying an opaque token. The cookie is not
a style preference: the ingestion progress stream is an `EventSource`, and that
API cannot set an Authorization header, so a bearer token would have to travel
in the query string where it lands in access logs.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, current_user
from app.core.config import get_settings
from app.core.security import (
    hash_password,
    mint_session_token,
    needs_rehash,
    verify_password,
)
from app.db.postgres import get_session
from app.models.schemas import LoginRequest, SignupRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        httponly=True,
        # Lax is enough here: a genuinely cross-site POST will not carry the
        # cookie, and localhost:3000 -> localhost:8000 is same-site because
        # SameSite ignores the port. A split-domain deploy needs None+Secure
        # and real CSRF tokens.
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


async def _open_session(session: AsyncSession, user_id) -> str:
    token, token_hash = mint_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=get_settings().session_ttl_days
    )
    await session.execute(
        text(
            """
            INSERT INTO sessions (token_hash, user_id, expires_at)
            VALUES (:token_hash, :user_id, :expires_at)
            """
        ),
        {"token_hash": token_hash, "user_id": user_id, "expires_at": expires_at},
    )
    return token


@router.post("/signup", response_model=UserResponse, status_code=201)
async def signup(
    body: SignupRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    email = body.email.strip().lower()
    password_hash = await hash_password(body.password)

    # DO NOTHING rather than catching IntegrityError, so a duplicate is an
    # empty result instead of an exception mid-transaction.
    row = (
        await session.execute(
            text(
                """
                INSERT INTO users (email, password_hash)
                VALUES (:email, :password_hash)
                ON CONFLICT (email) DO NOTHING
                RETURNING id
                """
            ),
            {"email": email, "password_hash": password_hash},
        )
    ).first()
    if row is None:
        raise HTTPException(409, "that email is already registered")

    workspace_id = await session.scalar(
        text(
            """
            INSERT INTO workspaces (owner_id, name)
            VALUES (:owner_id, :name)
            RETURNING id
            """
        ),
        {"owner_id": row.id, "name": "My library"},
    )

    token = await _open_session(session, row.id)
    await session.commit()

    _set_session_cookie(response, token)
    return UserResponse(id=row.id, email=email, workspace_id=workspace_id)


@router.post("/login", response_model=UserResponse)
async def login(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    email = body.email.strip().lower()
    row = (
        await session.execute(
            text(
                """
                SELECT u.id, u.password_hash, w.id AS workspace_id
                  FROM users u
                  LEFT JOIN workspaces w ON w.owner_id = u.id
                 WHERE u.email = :email
                 ORDER BY w.created_at
                 LIMIT 1
                """
            ),
            {"email": email},
        )
    ).first()

    # verify_password still does the full argon2 work when the hash is None, so
    # an unknown email costs the same as a wrong password. The error text is
    # identical either way -- neither timing nor wording should say which
    # accounts exist.
    if not await verify_password(body.password, row.password_hash if row else None):
        raise HTTPException(401, "incorrect email or password")

    if needs_rehash(row.password_hash):
        await session.execute(
            text("UPDATE users SET password_hash = :hash WHERE id = :id"),
            {"hash": await hash_password(body.password), "id": row.id},
        )

    token = await _open_session(session, row.id)
    await session.commit()

    _set_session_cookie(response, token)
    return UserResponse(id=row.id, email=email, workspace_id=row.workspace_id)


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    principal: Principal = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Revoke the session server-side, not just client-side."""
    await session.execute(
        text("DELETE FROM sessions WHERE id = :id"), {"id": principal.session_id}
    )
    await session.commit()
    response.delete_cookie(
        key=get_settings().session_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=get_settings().cookie_secure,
    )


@router.get("/me", response_model=UserResponse)
async def me(principal: Principal = Depends(current_user)) -> UserResponse:
    return UserResponse(
        id=principal.user_id,
        email=principal.email,
        workspace_id=principal.workspace_id,
    )
