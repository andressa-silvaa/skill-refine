from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.accounts.domain.errors import EmailSendFailed, EmailServiceNotConfigured
from apps.accounts.domain.ports import EmailSender

from .email_templates import render_email_confirmation, render_password_reset_code

logger = logging.getLogger(__name__)


def _smtp_not_configured() -> bool:
    if settings.EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend":
        return False
    if not getattr(settings, "EMAIL_HOST", ""):
        return True
    # Resend / generic SMTP: host set but missing credentials
    return not getattr(settings, "EMAIL_HOST_PASSWORD", "")


def _ensure_smtp_or_raise(*, context: str) -> None:
    if not _smtp_not_configured():
        return
    logger.warning(
        "email_smtp_not_configured context=%s backend=%s email_host=%s has_password=%s",
        context,
        getattr(settings, "EMAIL_BACKEND", ""),
        repr(getattr(settings, "EMAIL_HOST", "") or ""),
        bool(getattr(settings, "EMAIL_HOST_PASSWORD", "")),
    )
    raise EmailServiceNotConfigured()


def _send_message(*, kind: str, to_email: str, msg: EmailMultiAlternatives) -> None:
    try:
        msg.send(fail_silently=False)
        logger.info(
            "email_smtp_send_ok kind=%s to=%s from=%s",
            kind,
            to_email,
            getattr(settings, "DEFAULT_FROM_EMAIL", ""),
        )
    except Exception as exc:
        logger.error(
            "email_smtp_send_failed kind=%s to=%s from=%s host=%s port=%s tls=%s ssl=%s",
            kind,
            to_email,
            getattr(settings, "DEFAULT_FROM_EMAIL", ""),
            getattr(settings, "EMAIL_HOST", "") or "(empty)",
            getattr(settings, "EMAIL_PORT", ""),
            getattr(settings, "EMAIL_USE_TLS", ""),
            getattr(settings, "EMAIL_USE_SSL", ""),
            exc_info=exc,
        )
        raise EmailSendFailed() from exc


class DjangoEmailSender(EmailSender):
    def send_password_reset_code(self, *, to_email: str, code: str) -> None:
        _ensure_smtp_or_raise(context="password_reset")

        subject, html, text = render_password_reset_code(code=code, frontend_url=getattr(settings, "FRONTEND_URL", None))
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
            reply_to=[settings.DEFAULT_FROM_EMAIL],
        )
        msg.attach_alternative(html, "text/html")
        _send_message(kind="password_reset", to_email=to_email, msg=msg)

    def send_email_confirmation_link(self, *, to_email: str, confirm_url: str) -> None:
        _ensure_smtp_or_raise(context="email_confirmation")

        subject, html, text = render_email_confirmation(confirm_url=confirm_url, frontend_url=getattr(settings, "FRONTEND_URL", None))
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
            reply_to=[settings.DEFAULT_FROM_EMAIL],
        )
        msg.attach_alternative(html, "text/html")
        _send_message(kind="email_confirmation", to_email=to_email, msg=msg)
