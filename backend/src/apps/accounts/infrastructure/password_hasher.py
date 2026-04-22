from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from apps.accounts.domain.ports import PasswordHasher as PasswordHasherPort


class Argon2PasswordHasher(PasswordHasherPort):
    """Plain Argon2id hasher (no pepper). Kept for legacy hashes."""

    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, hashed: str, password: str) -> bool:
        try:
            return self._hasher.verify(hashed, password)
        except VerifyMismatchError:
            return False

    def needs_rehash(self, hashed: str) -> bool:
        try:
            return self._hasher.check_needs_rehash(hashed)
        except InvalidHashError:
            return True


