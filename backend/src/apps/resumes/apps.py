import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ResumesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.resumes"

    def ready(self) -> None:
        """
        Initialize Playwright browser at startup (pre-warm).
        Avoids Chromium cold start on the first PDF request.
        Also registers handlers for graceful shutdown.
        """
        # Import here to avoid circular import
        try:
            import sys

            # IMPORTANT:
            # Playwright (sync API) internally initializes an async/greenlet loop.
            # If that happens during management commands (e.g. migrate),
            # Django may treat the context as "async" and block synchronous DB access.
            # Therefore, we only pre-warm when the process is the server (runserver).
            if "runserver" not in sys.argv:
                return

            from apps.resumes.interfaces.api.pdf_browser import PdfBrowserManager

            manager = PdfBrowserManager.get_instance()
            if not manager.is_initialized():
                manager.initialize()
                logger.info("Playwright browser pre-warmed successfully.")

        except Exception as e:
            # Log but do not break startup if the browser fails
            # PDF will still work, just slower on the first request
            logger.warning(
                f"Failed to pre-warm Playwright browser: {e}. "
                "PDF will still work, but will be slower on the first request.",
                exc_info=True
            )


