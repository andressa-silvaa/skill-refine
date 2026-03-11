"""JWT, refresh tokens, password reset, email confirmation, OAuth."""
from __future__ import annotations

from .base import DEBUG, SECRET_KEY, env

JWT_SECRET = env.str("JWT_SECRET", default=SECRET_KEY)
JWT_ISSUER = env.str("JWT_ISSUER", default="skill-refine")
JWT_ACCESS_TTL_MINUTES = env.int("JWT_ACCESS_TTL_MINUTES", default=15)

REFRESH_TOKEN_PEPPER = env.str("REFRESH_TOKEN_PEPPER", default=SECRET_KEY)
REFRESH_TTL_DAYS = env.int("REFRESH_TTL_DAYS", default=30)
REFRESH_COOKIE_NAME = env.str("REFRESH_COOKIE_NAME", default="sr_refresh")
REFRESH_COOKIE_SECURE = env.bool("REFRESH_COOKIE_SECURE", default=(not DEBUG))
REFRESH_COOKIE_SAMESITE = env.str("REFRESH_COOKIE_SAMESITE", default="Lax")
REFRESH_COOKIE_PATH = env.str("REFRESH_COOKIE_PATH", default="/")

PASSWORD_RESET_CODE_TTL_MINUTES = env.int("PASSWORD_RESET_CODE_TTL_MINUTES", default=10)
PASSWORD_RESET_GRANT_TTL_MINUTES = env.int("PASSWORD_RESET_GRANT_TTL_MINUTES", default=15)
PASSWORD_RESET_CODE_PEPPER = env.str("PASSWORD_RESET_CODE_PEPPER", default=SECRET_KEY)

EMAIL_CONFIRMATION_TOKEN_TTL_HOURS = env.int("EMAIL_CONFIRMATION_TOKEN_TTL_HOURS", default=24)
EMAIL_CONFIRMATION_TOKEN_PEPPER = env.str("EMAIL_CONFIRMATION_TOKEN_PEPPER", default=SECRET_KEY)

FRONTEND_URL = env.str("FRONTEND_URL", default="http://localhost:3000")
BACKEND_URL = env.str("BACKEND_URL", default="")

CLOUDINARY_URL = env.str("CLOUDINARY_URL", default="")

GOOGLE_OAUTH_CLIENT_ID = env.str("GOOGLE_OAUTH_CLIENT_ID", default="")
GOOGLE_OAUTH_CLIENT_SECRET = env.str("GOOGLE_OAUTH_CLIENT_SECRET", default="")
