"""Password hashing and session tokens.

Passwords use argon2id via argon2-cffi. Both hashing and verification are
deliberately expensive -- roughly 65 MB and tens of milliseconds at the library
defaults -- so they run in a worker thread rather than on the event loop, where
they would stall every other request in flight.

Session tokens are opaque random strings. Only their SHA-256 is stored, so a
dump of the sessions table cannot be replayed as a cookie.
"""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi.concurrency import run_in_threadpool

_hasher = PasswordHasher()

# Verified against when the email is unknown, so a miss costs the same as a
# wrong password and the response time does not reveal which accounts exist.
_DUMMY_HASH = _hasher.hash("password-for-a-user-that-does-not-exist")

TOKEN_BYTES = 32


async def hash_password(password: str) -> str:
    return await run_in_threadpool(_hasher.hash, password)


async def verify_password(password: str, stored_hash: str | None) -> bool:
    """Check a password. A missing hash still burns the same work on purpose."""
    target = stored_hash or _DUMMY_HASH

    def _verify() -> bool:
        try:
            return _hasher.verify(target, password)
        except (VerificationError, InvalidHashError):
            # VerificationError covers a wrong password; InvalidHashError means
            # the stored value is corrupt, which is also a failed login and not
            # something to 500 over.
            return False

    ok = await run_in_threadpool(_verify)
    # `bool(stored_hash)`, not `is not None`, so this agrees with the `or` above
    # on what counts as missing. If they disagreed, a row with an empty
    # password_hash would fall through to _DUMMY_HASH and then be accepted --
    # handing the account to anyone who sends the dummy's plaintext.
    return ok and bool(stored_hash)


def needs_rehash(stored_hash: str) -> bool:
    """True when the hash predates the current argon2 parameters."""
    try:
        return _hasher.check_needs_rehash(stored_hash)
    except InvalidHashError:
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def mint_session_token() -> tuple[str, str]:
    """Return (token for the cookie, hash to store)."""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    return token, hash_token(token)
