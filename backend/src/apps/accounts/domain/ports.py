from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class UserDTO:
    id: str
    email: str
    full_name: str
    email_verified: bool


@dataclass(frozen=True)
class GoogleProfile:
    sub: str
    email: str
    email_verified: bool
    full_name: str | None


class UserRepository(Protocol):
    def get_by_email(self, email: str): ...
    def get_by_id(self, user_id: str): ...
    def create_user(self, *, email: str, full_name: str, birth_date: date | None): ...
    def mark_email_verified(self, *, user_id: str, when: datetime) -> None: ...
    def soft_delete(self, *, user_id: str, when: datetime) -> None: ...


class PasswordRepository(Protocol):
    def set_password(self, *, user_id: str, password_hash: str, when: datetime) -> None: ...
    def get_password_hash(self, *, user_id: str) -> str | None: ...


class AuthIdentityRepository(Protocol):
    def ensure_password_identity(self, *, user_id: str, when: datetime) -> None: ...
    def touch_last_login(self, *, user_id: str, provider: str, when: datetime) -> None: ...
    def get_google_identity_by_sub(self, *, sub: str): ...
    def upsert_google_identity(self, *, user_id: str, sub: str, email: str, when: datetime) -> None: ...


class SessionRepository(Protocol):
    def create_session(
        self,
        *,
        user_id: str,
        refresh_token_hash: str,
        expires_at: datetime,
        ip: str | None,
        user_agent: str | None,
    ): ...

    def get_session(self, session_id: str): ...
    def revoke_session(self, *, session_id: str, when: datetime, replaced_by_session_id: str | None = None) -> None: ...
    def revoke_all_for_user(self, *, user_id: str, when: datetime) -> None: ...


class PasswordResetRepository(Protocol):
    def create_request(
        self,
        *,
        user_id: str,
        email: str,
        code_hash: str,
        expires_at: datetime,
    ): ...

    def latest_active_for_email(self, *, email: str): ...
    def consume_all_active_for_user(self, *, user_id: str, when: datetime) -> None: ...
    def increment_attempts(self, *, request_id: str, when: datetime) -> None: ...
    def mark_verified_and_set_grant(
        self,
        *,
        request_id: str,
        when: datetime,
        reset_token_hash: str,
        reset_token_expires_at: datetime,
    ) -> None: ...
    def consume(self, *, request_id: str, when: datetime) -> None: ...


class EmailConfirmationRepository(Protocol):
    def latest_active_for_email(self, *, email: str): ...
    def count_recent_for_email(self, *, email: str, since: datetime) -> int: ...
    def count_recent_for_ip(self, *, ip: str, since: datetime) -> int: ...
    def create_token(
        self,
        *,
        user_id: str,
        email: str,
        token_hash: str,
        expires_at: datetime,
        ip: str | None,
        user_agent: str | None,
    ):
        ...

    def get_active_by_token_hash(self, *, token_hash: str): ...
    def get_latest_by_token_hash(self, *, token_hash: str): ...
    def consume(self, *, token_id: str, when: datetime) -> None: ...
    def consume_if_active(self, *, token_id: str, when: datetime) -> bool: ...
    def consume_all_active_for_user(self, *, user_id: str, when: datetime) -> None: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, hashed: str, password: str) -> bool: ...


class GoogleTokenVerifier(Protocol):
    def verify(self, *, id_token: str) -> GoogleProfile: ...


class EmailSender(Protocol):
    def send_password_reset_code(self, *, to_email: str, code: str) -> None: ...
    def send_email_confirmation_link(self, *, to_email: str, confirm_url: str) -> None: ...


