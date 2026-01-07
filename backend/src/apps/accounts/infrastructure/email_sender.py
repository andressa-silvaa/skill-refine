from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail

from apps.accounts.domain.errors import EmailSendFailed, EmailServiceNotConfigured
from apps.accounts.domain.ports import EmailSender


class DjangoEmailSender(EmailSender):
    def send_password_reset_code(self, *, to_email: str, code: str) -> None:
        # Fail fast with a controlled error when SMTP isn't configured.
        if settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and not settings.EMAIL_HOST:
            raise EmailServiceNotConfigured()

        subject = "Seu código de redefinição de senha"
        message = (
            "Você solicitou a redefinição de senha.\n\n"
            f"Código: {code}\n\n"
            "Se você não solicitou, ignore este email."
        )
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)
        except Exception as exc:  # noqa: BLE001
            # Don't leak SMTP/internal details to callers.
            raise EmailSendFailed() from exc

    def send_email_confirmation_link(self, *, to_email: str, confirm_url: str) -> None:
        # Fail fast with a controlled error when SMTP isn't configured.
        if settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and not settings.EMAIL_HOST:
            raise EmailServiceNotConfigured()

        subject = "Confirme seu e-mail"
        message = (
            "Olá!\n\n"
            "Para concluir seu cadastro, confirme seu e-mail no link abaixo:\n\n"
            f"{confirm_url}\n\n"
            "Se você não solicitou, ignore este email."
        )
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)
        except Exception as exc:  # noqa: BLE001
            # Don't leak SMTP/internal details to callers.
            raise EmailSendFailed() from exc


