from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.accounts.domain.errors import EmailSendFailed, EmailServiceNotConfigured
from apps.accounts.domain.ports import EmailSender

from .email_templates import render_data_export_requested, render_email_confirmation, render_password_reset_code


class DjangoEmailSender(EmailSender):
    def send_password_reset_code(self, *, to_email: str, code: str) -> None:
        if settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and not settings.EMAIL_HOST:
            raise EmailServiceNotConfigured()

        subject, html, text = render_password_reset_code(code=code, frontend_url=getattr(settings, "FRONTEND_URL", None))
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email],
                reply_to=[settings.DEFAULT_FROM_EMAIL],
            )
            msg.attach_alternative(html, "text/html")
            msg.send(fail_silently=False)
        except Exception as exc:
            raise EmailSendFailed() from exc

    def send_data_export_requested(self, *, to_email: str) -> None:
        if settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and not settings.EMAIL_HOST:
            raise EmailServiceNotConfigured()

        subject, html, text = render_data_export_requested(frontend_url=getattr(settings, "FRONTEND_URL", None))
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email],
                reply_to=[settings.DEFAULT_FROM_EMAIL],
            )
            msg.attach_alternative(html, "text/html")
            msg.send(fail_silently=False)
        except Exception as exc:
            raise EmailSendFailed() from exc

    def send_email_confirmation_link(self, *, to_email: str, confirm_url: str) -> None:
        if settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and not settings.EMAIL_HOST:
            raise EmailServiceNotConfigured()

        subject, html, text = render_email_confirmation(confirm_url=confirm_url, frontend_url=getattr(settings, "FRONTEND_URL", None))
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email],
                reply_to=[settings.DEFAULT_FROM_EMAIL],
            )
            msg.attach_alternative(html, "text/html")
            msg.send(fail_silently=False)
        except Exception as exc:
            raise EmailSendFailed() from exc


