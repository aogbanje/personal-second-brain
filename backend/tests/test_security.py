"""Password and session-token invariants.

These are the properties the auth layer's security claims rest on, and all of
them fail silently: a login that stops burning argon2 work on an unknown email
still works, it just leaks which accounts exist; a session token stored in the
clear still authenticates, it just makes a database dump replayable. Nothing in
the product surfaces either regression, so they are pinned here.

No DB and no event loop of their own -- `asyncio.run` per call keeps this a
plain pytest run with no pytest-asyncio dependency.
"""

import asyncio

import pytest

from app.core import security
from app.core.security import (
    hash_password,
    hash_token,
    mint_session_token,
    needs_rehash,
    verify_password,
)

PASSWORD = "a-sufficiently-long-password"

# The plaintext `security._DUMMY_HASH` is built from. Duplicated here on purpose
# -- see test_the_dummy_hashes_own_plaintext_does_not_authenticate.
DUMMY_PLAINTEXT = "password-for-a-user-that-does-not-exist"


def _run(coro):
    return asyncio.run(coro)


def test_correct_password_verifies():
    stored = _run(hash_password(PASSWORD))

    assert _run(verify_password(PASSWORD, stored)) is True


def test_wrong_password_is_rejected():
    stored = _run(hash_password(PASSWORD))

    assert _run(verify_password(PASSWORD + "x", stored)) is False


def test_same_password_hashes_differently_each_time():
    # Distinct salts. Equal hashes would mean a single rainbow table covers
    # every account that picked the same password.
    assert _run(hash_password(PASSWORD)) != _run(hash_password(PASSWORD))


def test_missing_hash_is_rejected():
    """An unknown email must fail, however convincing the password looks."""
    assert _run(verify_password(PASSWORD, None)) is False


def test_the_dummy_hashes_own_plaintext_does_not_authenticate():
    """The sharp edge of verifying against a dummy hash.

    `verify_password(pw, <missing>)` compares against a module-level hash so the
    unknown-email path costs the same as a wrong password. That makes the
    dummy's plaintext a password that genuinely matches what was compared --
    only the explicit falsiness guard stops it from signing someone in as an
    account that does not exist.
    """
    # Asserted first: if the dummy is ever rebuilt from a different plaintext
    # this fails loudly, rather than leaving the checks below passing for the
    # trivial reason that nothing matches any more.
    assert security._hasher.verify(security._DUMMY_HASH, DUMMY_PLAINTEXT)

    assert _run(verify_password(DUMMY_PLAINTEXT, None)) is False
    # The empty string too: `stored_hash or _DUMMY_HASH` treats it as missing,
    # so the guard has to agree. A guard written as `is not None` would accept
    # this and hand over any account whose password_hash row was blanked.
    assert _run(verify_password(DUMMY_PLAINTEXT, "")) is False


@pytest.mark.parametrize("corrupt", ["", "not-a-hash", "$argon2id$v=19$truncated"])
def test_corrupt_stored_hash_is_a_failed_login_not_a_crash(corrupt):
    # A mangled row should log that user out, not 500 the endpoint for everyone.
    assert _run(verify_password(PASSWORD, corrupt)) is False
    assert needs_rehash(corrupt) is False


def test_fresh_hash_does_not_need_rehashing():
    assert needs_rehash(_run(hash_password(PASSWORD))) is False


def test_minted_token_is_stored_only_as_its_hash():
    token, token_hash = mint_session_token()

    assert token_hash == hash_token(token)
    # The cookie value itself must not be what lands in the sessions table.
    assert token not in token_hash
    assert len(token_hash) == 64


def test_tokens_are_unique():
    tokens = {mint_session_token()[0] for _ in range(100)}

    assert len(tokens) == 100


def test_token_hashing_is_deterministic():
    # Lookup is by hash equality, so a salted digest here would make every
    # session unfindable.
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != hash_token("abd")
