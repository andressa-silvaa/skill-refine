import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ResumesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.resumes"

    def ready(self) -> None:
        """
        Do NOT start Playwright here.

        Playwright's sync API initializes async/greenlet machinery. If that runs during
        Django startup (before runserver finishes check_migrations / DB access), Django
        raises SynchronousOnlyOperation on synchronous ORM calls.

        PdfBrowserManager.get_browser() already calls initialize() lazily on first PDF use.
        """
        return
