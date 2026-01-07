from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt


@dataclass(frozen=True)
class JwtConfig:
    secret: str
    issuer: str
    access_ttl_minutes: int


class JwtError(Exception):
    pass


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def encode_access_token(*, cfg: JwtConfig, user_id: str, session_id: str) -> str:
    issued_at = now_utc()
    payload: dict[str, Any] = {
        "typ": "access",
        "iss": cfg.issuer,
        "sub": user_id,
        "sid": session_id,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(minutes=cfg.access_ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, cfg.secret, algorithm="HS256")


def decode_token(*, secret: str, issuer: str, token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "iss", "sub"]},
            issuer=issuer,
        )
    except jwt.PyJWTError as exc:
        raise JwtError("invalid_token") from exc
    if not isinstance(payload, dict):
        raise JwtError("invalid_token")
    return payload


