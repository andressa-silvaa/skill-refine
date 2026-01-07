from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.infrastructure.email_templates import render_email_confirmation, render_password_reset_code


class Command(BaseCommand):
    help = "Render transactional email HTML to stdout for quick preview (no external deps)."

    def add_arguments(self, parser):
        parser.add_argument("--type", choices=["confirmation", "reset"], required=True)
        parser.add_argument("--url", help="Confirmation URL (for --type confirmation).")
        parser.add_argument("--code", help="Reset code (for --type reset).", default="123456")

    def handle(self, *args, **options):
        email_type = options["type"]
        if email_type == "confirmation":
            url = (options.get("url") or "").strip()
            if not url:
                raise CommandError("--url is required for --type confirmation")
            _subject, html, _text = render_email_confirmation(
                confirm_url=url,
                frontend_url=getattr(settings, "FRONTEND_URL", None),
            )
            self.stdout.write(html)
            return

        if email_type == "reset":
            code = (options.get("code") or "").strip() or "123456"
            _subject, html, _text = render_password_reset_code(code=code, frontend_url=getattr(settings, "FRONTEND_URL", None))
            self.stdout.write(html)
            return

        raise CommandError("Unsupported type")


