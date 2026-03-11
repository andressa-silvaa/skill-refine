"""
Playwright browser manager for PDF generation.

IMPORTANT (Playwright sync API):
- The Playwright sync API is not thread-safe (uses greenlets).
- If you create Playwright/Browser in one thread and use it in another, you get:
  "Cannot switch to a different thread".

Solution adopted:
- Thread-local reuse: each thread keeps its own long-lived Playwright/Browser instance,
  and each request creates/closes only a Page.
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
    Long-lived manager PER THREAD.

    Keeps Playwright+Browser in the current thread and reuses it across requests in that thread.
    """

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._initialized = False
        self._initialization_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "PdfBrowserManager":
        """
        Return the manager instance associated with the current thread.
        """
        inst = getattr(_thread_local, "pdf_browser_manager", None)
        if inst is None:
            inst = cls()
            _thread_local.pdf_browser_manager = inst
        return inst

    def initialize(self) -> None:
        """
        Initialize the Playwright browser (pre-warm).
        Should be called at Django startup (AppConfig.ready()).
        """
        if self._initialized:
            return

        with self._initialization_lock:
            if self._initialized:
                return

            try:
                logger.info("Initializing Playwright browser for PDF (pre-warm)...")
                self._playwright = sync_playwright().start()
                self._browser = self._playwright.chromium.launch(
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                self._initialized = True
                logger.info("Playwright browser initialized successfully.")
            except Exception as e:
                logger.error(f"Error initializing Playwright browser: {e}", exc_info=True)
                self._cleanup()
                raise

    def get_browser(self) -> Browser:
        """
        Return the browser instance. Raises if not initialized.
        """
        # Lazy init per thread: ensures calls from other threads
        # (e.g. requests different from pre-warm) still work.
        if not self._initialized or self._browser is None:
            self.initialize()
        return self._browser

    def create_page(self, viewport: Optional[dict[str, int]] = None) -> Page:
        """
        Create a new page (tab) in the reused browser.

        Args:
            viewport: Viewport dimensions (default: {"width": 1280, "height": 720})

        Returns:
            New Playwright page
        """
        browser = self.get_browser()
        if viewport is None:
            viewport = {"width": 1280, "height": 720}
        return browser.new_page(viewport=viewport)

    def is_initialized(self) -> bool:
        """Check if the browser has been initialized."""
        return self._initialized and self._browser is not None

    def shutdown(self) -> None:
        """
        Close the browser and release resources.
        Should be called at Django shutdown.
        """
        if not self._initialized:
            return

        with self._initialization_lock:
            if not self._initialized:
                return

        logger.info("Closing Playwright browser (thread-local)...")
        self._cleanup()
        logger.info("Playwright browser closed (thread-local).")

    def _cleanup(self) -> None:
        """Release internal resources."""
        try:
            if self._browser:
                self._browser.close()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}", exc_info=True)
        finally:
            self._browser = None

        try:
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.warning(f"Error stopping Playwright: {e}", exc_info=True)
        finally:
            self._playwright = None
            self._initialized = False

    def restart(self) -> None:
        """
        Restart the browser (useful on error or when a reset is needed).
        """
        logger.info("Restarting Playwright browser...")
        self._cleanup()
        self.initialize()


# Helper functions for convenience
def get_pdf_browser() -> Browser:
    """Return the browser singleton instance."""
    return PdfBrowserManager.get_instance().get_browser()


def create_pdf_page(viewport: Optional[dict[str, int]] = None) -> Page:
    """Create a new page in the browser singleton."""
    return PdfBrowserManager.get_instance().create_page(viewport=viewport)
