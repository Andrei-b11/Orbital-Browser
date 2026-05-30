"""Escudo de privacidad: interceptor de red de bajo nivel (Fase 3).

Analiza cada petición de Chromium antes de que salga a la red y bloquea
los dominios incluidos en la lista negra (telemetría, rastreo y anuncios).

TODO (Fase 3): cargar dinámicamente filtros EasyList/uBlock de forma asíncrona.
"""
from __future__ import annotations

from PyQt6.QtWebEngineCore import (
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)


class PrivacyShield(QWebEngineUrlRequestInterceptor):
    """Bloqueo estricto e invisible de peticiones según una lista negra."""

    def __init__(self, blocklist: list[str] | None = None) -> None:
        super().__init__()
        self.blocklist: list[str] = blocklist or []
        self.blocked_count: int = 0

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        url_str = info.requestUrl().toString()
        if any(domain in url_str for domain in self.blocklist):
            info.block(True)
            self.blocked_count += 1
