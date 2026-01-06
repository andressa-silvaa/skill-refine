from __future__ import annotations

from django.core.mail import send_mail

from apps.accounts.domain.ports import EmailSender


class DjangoEmailSender(EmailSender):
    def send_password_reset_code(self, *, to_email: str, code: str) -> None:
        subject = "Seu código de redefinição de senha"
        message = (
            "Você solicitou a redefinição de senha.\n\n"
            f"Código: {code}\n\n"
            "Se você não solicitou, ignore este email."
        )
        send_mail(subject, message, None, [to_email], fail_silently=False)


