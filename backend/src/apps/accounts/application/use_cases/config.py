"""Auth/config types used across use case modules."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AccountsAuthConfig:
    jwt_secret: str
    jwt_issuer: str
    jwt_access_ttl_minutes: int

    refresh_token_pepper: str
    refresh_ttl_days: int

    password_reset_code_ttl_minutes: int
    password_reset_grant_ttl_minutes: int
    password_reset_code_pepper: str

    email_confirmation_token_ttl_hours: int
    email_confirmation_token_pepper: str
    frontend_url: str

    google_oauth_client_id: str
