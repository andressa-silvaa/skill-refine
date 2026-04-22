"""Server-side peppered Argon2id password hasher.

The pepper is never stored in the database: it lives only in the environment
(``settings.PASSWORD_HASH_PEPPER``). Stored format is ``peppered$v1$<argon2id>``.
Hashes without the prefix are treated as legacy and still accepted by
``verify`` so existing users can log in; ``needs_rehash`` reports True for them
so the login flow can upgrade them transparently.
"""
from __future__ import annotations

import hmac
import warnings
from hashlib import sha256

from argon2 import PasswordHasher as _Argon2PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from apps.accounts.domain.ports import PasswordHasher as PasswordHasherPort

PEPPER_PREFIX = "peppered$v1$"

_DEV_FALLBACK_PEPPER = "change-me-in-dev"


def resolve_pepper_or_raise(*, debug: bool, raw: str | None) -> str:
    value = (raw or "").strip()
    if value:
        return value
    if debug:
        warnings.warn(
            "PASSWORD_HASH_PEPPER is not set; falling back to the insecure dev "
            "default. Set PASSWORD_HASH_PEPPER in your environment before "
            "running in production.",
            stacklevel=2,
        )
        return _DEV_FALLBACK_PEPPER
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "PASSWORD_HASH_PEPPER must be set when DEBUG=False. This value is used "
        "to HMAC user passwords before hashing and must live outside the "
        "database (environment only). See backend/README.md."
    )


class PepperedArgon2PasswordHasher(PasswordHasherPort):
    def __init__(self, pepper: str, *, _inner: _Argon2PasswordHasher | None = None) -> None:
        if not isinstance(pepper, str) or pepper == "":
            raise ValueError("pepper must be a non-empty string")
        self._pepper_bytes = pepper.encode("utf-8")
        self._hasher = _inner or _Argon2PasswordHasher()

    def _apply_pepper(self, password: str) -> str:
        return hmac.new(self._pepper_bytes, password.encode("utf-8"), sha256).hexdigest()

    def hash(self, password: str) -> str:
        peppered = self._apply_pepper(password)
        return PEPPER_PREFIX + self._hasher.hash(peppered)

    def verify(self, hashed: str, password: str) -> bool:
        if not hashed:
            return False
        if hashed.startswith(PEPPER_PREFIX):
            raw_hash = hashed[len(PEPPER_PREFIX) :]
            candidate = self._apply_pepper(password)
        else:
            raw_hash = hashed
            candidate = password
        try:
            return self._hasher.verify(raw_hash, candidate)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, hashed: str) -> bool:
        if not hashed:
            return False
        if not hashed.startswith(PEPPER_PREFIX):
            return True
        raw_hash = hashed[len(PEPPER_PREFIX) :]
        try:
            return self._hasher.check_needs_rehash(raw_hash)
        except InvalidHashError:
            return True


def build_default_password_hasher() -> PepperedArgon2PasswordHasher:
    from django.conf import settings

    return PepperedArgon2PasswordHasher(pepper=settings.PASSWORD_HASH_PEPPER)
