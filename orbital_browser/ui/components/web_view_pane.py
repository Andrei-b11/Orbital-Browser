"""Contenedor del renderizador web (Chromium) por pestaña (Fase 2).

`OrbitalPage` intercepta los enlaces internos `orbital://…` (historial, descargas,
configuración, etc.) para que el navegador los gestione de forma nativa en
lugar de enviarlos a la red. `WebViewPane` añade la apertura de pestañas nuevas.
"""
from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import QTimer, QUrl, pyqtSignal
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView


class OrbitalPage(QWebEnginePage):
    """Página que delega la navegación a `orbital://` en la ventana principal."""

    internal_requested = pyqtSignal(QUrl)

    def __init__(self, profile: QWebEngineProfile, parent=None) -> None:
        super().__init__(profile, parent)
        # Mientras renderizamos una página interna no debemos interceptar su
        # propia carga (evita bucles al usar una base orbital://).
        self._suppress = False

    def render_internal(self, html: str, base: QUrl) -> None:
        self._suppress = True
        self.setHtml(html, base)
        QTimer.singleShot(0, self._clear_suppress)

    def _clear_suppress(self) -> None:
        self._suppress = False

    def acceptNavigationRequest(
        self, url: QUrl, nav_type: QWebEnginePage.NavigationType, is_main_frame: bool
    ) -> bool:
        if url.scheme() == "orbital" and not self._suppress:
            self.internal_requested.emit(url)
            return False  # bloquea la petición de red; la maneja el navegador
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class WebViewPane(QWebEngineView):
    """Vista web ligada al perfil de privacidad compartido."""

    def __init__(
        self,
        profile: QWebEngineProfile,
        new_tab_factory: Callable[[], "WebViewPane"] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.new_tab_factory = new_tab_factory
        self.setPage(OrbitalPage(profile, self))

        # Habilitar soporte de pantalla completa en Chromium
        self.settings().setAttribute(
            QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True
        )
        self.page().fullScreenRequested.connect(self._on_full_screen_requested)

    def createWindow(self, _type: QWebEnginePage.WebWindowType) -> QWebEngineView:
        """Chromium solicita una nueva ventana -> abrimos una pestaña nueva."""
        if self.new_tab_factory is not None:
            return self.new_tab_factory()
        return super().createWindow(_type)

    def set_internal_html(self, html: str, base: QUrl) -> None:
        """Renderiza HTML interno (orbital://…) sin disparar la intercepción."""
        self.page().render_internal(html, base)

    def _on_full_screen_requested(self, request) -> None:
        main_win = self.window()
        if main_win and hasattr(main_win, "handle_html5_fullscreen"):
            main_win.handle_html5_fullscreen(self, request)
        else:
            request.reject()
