from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from apps.accounts.domain.ports import PasswordHasher as PasswordHasherPort


class Argon2PasswordHasher(PasswordHasherPort):
    def __init__(self) -> None:
        # defaults are strong; can be tuned later via env if needed
        self._hasher = PasswordHasher()

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, hashed: str, password: str) -> bool:
        try:
            return self._hasher.verify(hashed, password)
        except VerifyMismatchError:
            return False


