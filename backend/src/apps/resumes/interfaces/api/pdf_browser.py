"""
Gerenciador de browser Playwright para PDF.

IMPORTANTE (Playwright sync API):
- A API síncrona do Playwright não é segura para cruzar threads (usa greenlets).
- Se você cria o Playwright/Browser em uma thread e usa em outra, ocorre erro:
  "Cannot switch to a different thread".

Solução adotada:
- Reuso por thread (thread-local): cada thread mantém sua instância long-lived
  do Playwright/Browser, e cada request cria/fecha apenas uma Page.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

from playwright.sync_api import Browser, Page, Playwright, sync_playwright

logger = logging.getLogger(__name__)


_thread_local = threading.local()


class PdfBrowserManager:
    """
    Gerenciador long-lived POR THREAD.

    Mantém Playwright+Browser na thread atual e reutiliza entre requests nessa mesma thread.
    """

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._initialized = False
        self._initialization_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "PdfBrowserManager":
        """
        Retorna a instância do gerenciador associada à thread atual.
        """
        inst = getattr(_thread_local, "pdf_browser_manager", None)
        if inst is None:
            inst = cls()
            _thread_local.pdf_browser_manager = inst
        return inst

    def initialize(self) -> None:
        """
        Inicializa o browser Playwright (pre-warm).
        Deve ser chamado no startup do Django (AppConfig.ready()).
        """
        if self._initialized:
            return

        with self._initialization_lock:
            if self._initialized:
                return

            try:
                logger.info("Inicializando browser Playwright para PDF (pre-warm)...")
                self._playwright = sync_playwright().start()
                self._browser = self._playwright.chromium.launch(
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                self._initialized = True
                logger.info("Browser Playwright inicializado com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao inicializar browser Playwright: {e}", exc_info=True)
                self._cleanup()
                raise

    def get_browser(self) -> Browser:
        """
        Retorna a instância do browser. Lança exceção se não estiver inicializado.
        """
        # Lazy init por thread: garante que chamadas vindas de outras threads
        # (ex.: requests diferentes do pre-warm) ainda funcionem.
        if not self._initialized or self._browser is None:
            self.initialize()
        return self._browser

    def create_page(self, viewport: Optional[dict[str, int]] = None) -> Page:
        """
        Cria uma nova página (tab) no browser reutilizado.
        
        Args:
            viewport: Dimensões da viewport (padrão: {"width": 1280, "height": 720})
        
        Returns:
            Nova página do Playwright
        """
        browser = self.get_browser()
        if viewport is None:
            viewport = {"width": 1280, "height": 720}
        return browser.new_page(viewport=viewport)

    def is_initialized(self) -> bool:
        """Verifica se o browser foi inicializado."""
        return self._initialized and self._browser is not None

    def shutdown(self) -> None:
        """
        Fecha o browser e limpa recursos.
        Deve ser chamado no shutdown do Django.
        """
        if not self._initialized:
            return

        with self._initialization_lock:
            if not self._initialized:
                return

        logger.info("Fechando browser Playwright (thread-local)...")
        self._cleanup()
        logger.info("Browser Playwright fechado (thread-local).")

    def _cleanup(self) -> None:
        """Limpa recursos internos."""
        try:
            if self._browser:
                self._browser.close()
        except Exception as e:
            logger.warning(f"Erro ao fechar browser: {e}", exc_info=True)
        finally:
            self._browser = None

        try:
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.warning(f"Erro ao parar Playwright: {e}", exc_info=True)
        finally:
            self._playwright = None
            self._initialized = False

    def restart(self) -> None:
        """
        Reinicia o browser (útil em caso de erro ou necessidade de reset).
        """
        logger.info("Reiniciando browser Playwright...")
        self._cleanup()
        self.initialize()


# Função helper para facilitar o uso
def get_pdf_browser() -> Browser:
    """Retorna a instância do browser singleton."""
    return PdfBrowserManager.get_instance().get_browser()


def create_pdf_page(viewport: Optional[dict[str, int]] = None) -> Page:
    """Cria uma nova página no browser singleton."""
    return PdfBrowserManager.get_instance().create_page(viewport=viewport)
