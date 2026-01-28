import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ResumesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.resumes"

    def ready(self) -> None:
        """
        Inicializa o browser Playwright no startup (pre-warm).
        Isso evita o cold start do Chromium na primeira requisição de PDF.
        Também registra handlers para shutdown graceful.
        """
        # Importa aqui para evitar import circular
        try:
            import sys

            # IMPORTANT:
            # O Playwright (sync API) inicializa internamente um loop async/greenlets.
            # Se isso acontecer durante comandos de management (ex.: migrate),
            # o Django pode considerar o contexto como "async" e bloquear acesso síncrono ao banco.
            # Portanto, fazemos pre-warm APENAS quando o processo é o servidor (runserver).
            if "runserver" not in sys.argv:
                return

            from apps.resumes.interfaces.api.pdf_browser import PdfBrowserManager

            manager = PdfBrowserManager.get_instance()
            if not manager.is_initialized():
                manager.initialize()
                logger.info("Browser Playwright pre-warmed com sucesso.")

        except Exception as e:
            # Log mas não quebra o startup se o browser falhar
            # O PDF ainda funcionará, só será mais lento na primeira requisição
            logger.warning(
                f"Falha ao fazer pre-warm do browser Playwright: {e}. "
                "PDF ainda funcionará, mas será mais lento na primeira requisição.",
                exc_info=True
            )


