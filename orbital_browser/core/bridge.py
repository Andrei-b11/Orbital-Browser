"""Puente nativo JavaScript ↔ Python mediante QWebChannel (Fase 4).

Expone un objeto `orbital` al contexto web para que las páginas y, más adelante,
las extensiones puedan invocar funciones nativas del navegador de forma segura.

NOTA: para que `window.orbital` esté disponible en la página, el cliente
`qwebchannel.js` debe inyectarse y conectarse al transporte. Esa inyección
automática queda como siguiente paso de la Fase 4; la infraestructura de canal
(registro del objeto) ya está operativa aquí.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class OrbitalBridge(QObject):
    """Objeto nativo expuesto al JavaScript de las páginas."""

    # Señal emitida hacia JS (p. ej. para notificaciones del navegador).
    notify = pyqtSignal(str)

    def __init__(self, db=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db = db

    @pyqtSlot(result=str)
    def version(self) -> str:
        """Devuelve la versión del navegador a JS."""
        return "Orbital 0.1.0"

    @pyqtSlot(str, str, result=bool)
    def addBookmark(self, url: str, title: str) -> bool:
        """Permite a la página guardar un marcador nativo."""
        if self._db is None or not url:
            return False
        self._db.add_bookmark(url, title)
        return True

    @pyqtSlot(str, result=str)
    def echo(self, message: str) -> str:
        """Eco de prueba para validar el canal."""
        return f"orbital:{message}"
