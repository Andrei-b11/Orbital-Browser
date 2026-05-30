"""Enrutador de búsquedas / direcciones (OrbitalSearch Router, Fase 5).

Determina si la entrada del Omnibox es una dirección directa o una consulta
de búsqueda y construye la `QUrl` correspondiente.

TODO (Fase 5): autocompletado local con Trie en RAM y UI de resultados sobre
el Omnibox sin cargar página completa.
"""
from __future__ import annotations

from urllib.parse import quote

from PyQt6.QtCore import QUrl

_SCHEMES = ("http://", "https://", "file://", "about:")


class OrbitalSearchRouter:
    """Resuelve texto del Omnibox a una `QUrl` (navegación directa o búsqueda)."""

    def __init__(self, endpoint: str) -> None:
        # Endpoint del motor de búsqueda privado por defecto.
        self.endpoint = endpoint

    def resolve(self, input_text: str) -> QUrl | None:
        cleaned = input_text.strip()
        if not cleaned:
            return None

        # 1. Ya trae un esquema explícito -> navegación directa.
        if cleaned.startswith(_SCHEMES):
            return QUrl(cleaned)

        # 2. Heurística de dominio: tiene punto y no tiene espacios.
        if "." in cleaned and " " not in cleaned:
            return QUrl(f"https://{cleaned}")

        # 3. En cualquier otro caso, búsqueda cifrada en el motor privado.
        return QUrl(f"{self.endpoint}{quote(cleaned)}")
