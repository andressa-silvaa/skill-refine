from __future__ import annotations


class AccountsError(Exception):
    code: str = "accounts_error"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.code)


class ValidationError(AccountsError):
    code = "validation_error"


class EmailAlreadyInUse(AccountsError):
    code = "email_already_in_use"


class InvalidCredentials(AccountsError):
    code = "invalid_credentials"


class UserDisabled(AccountsError):
    code = "user_disabled"


class RefreshInvalid(AccountsError):
    code = "refresh_invalid"


class RefreshRevoked(AccountsError):
    code = "refresh_revoked"


class PasswordResetNotFound(AccountsError):
    code = "password_reset_not_found"


class PasswordResetExpired(AccountsError):
    code = "password_reset_expired"


class PasswordResetTooManyAttempts(AccountsError):
    code = "password_reset_too_many_attempts"


class PasswordResetNotVerified(AccountsError):
    code = "password_reset_not_verified"


class PasswordResetGrantInvalid(AccountsError):
    code = "password_reset_grant_invalid"


class GoogleLoginNotConfigured(AccountsError):
    code = "google_login_not_configured"


class GoogleTokenInvalid(AccountsError):
    code = "google_token_invalid"


class EmailNotRegistered(AccountsError):
    code = "email_not_registered"


class EmailServiceNotConfigured(AccountsError):
    code = "email_service_not_configured"


class EmailSendFailed(AccountsError):
    code = "email_send_failed"


class EmailNotConfirmed(AccountsError):
    code = "email_not_confirmed"


class EmailConfirmationInvalid(AccountsError):
    code = "email_confirmation_invalid"


class EmailConfirmationExpired(AccountsError):
    code = "email_confirmation_expired"


class TooManyRequests(AccountsError):
    code = "too_many_requests"


