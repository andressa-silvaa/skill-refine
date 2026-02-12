"""Result types returned by use cases."""
from __future__ import annotations

from dataclasses import dataclass

from apps.accounts.domain.ports import UserDTO


@dataclass(frozen=True)
class AuthResult:
    access_token: str
    user: UserDTO


@dataclass(frozen=True)
class RefreshResult:
    access_token: str


@dataclass(frozen=True)
class PasswordResetVerifyResult:
    reset_token: str
