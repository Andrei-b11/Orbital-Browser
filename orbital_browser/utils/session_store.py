"""Persistencia de la sesión de navegación (Fase 1, memoria).

Guarda las URLs de las pestañas abiertas al cerrar y las restaura al abrir,
de modo que el usuario recupera su espacio de trabajo entre ejecuciones.
"""
from __future__ import annotations

import json
from pathlib import Path


class SessionStore:
    """Lee/escribe la sesión (lista de URLs + pestaña activa) en un JSON."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def save(self, urls: list[str], active_index: int) -> None:
        data = {"tabs": urls, "active": active_index}
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            # La pérdida de la sesión no debe impedir cerrar el navegador.
            pass

    def load(self) -> tuple[list[str], int]:
        if not self.path.exists():
            return [], 0
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return [], 0
        tabs = [u for u in data.get("tabs", []) if u and not u.startswith("about:")]
        active = data.get("active", 0)
        if not isinstance(active, int) or not (0 <= active < len(tabs)):
            active = 0
        return tabs, active
