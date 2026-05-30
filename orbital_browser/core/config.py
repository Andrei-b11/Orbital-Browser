"""Carga centralizada de configuración y rutas del proyecto.

Mantiene todos los parámetros (colores, flags, endpoints) fuera del código,
en `config/settings.json` y `config/theme.qss`, según las convenciones.
"""
from __future__ import annotations

import json
from pathlib import Path

# nexus_browser/  (raíz del paquete)
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"

_SETTINGS_CACHE: dict | None = None


def load_settings() -> dict:
    """Devuelve el diccionario de configuración (cacheado tras la 1ª lectura)."""
    global _SETTINGS_CACHE
    if _SETTINGS_CACHE is None:
        with open(CONFIG_DIR / "settings.json", encoding="utf-8") as fh:
            _SETTINGS_CACHE = json.load(fh)
    return _SETTINGS_CACHE


def load_stylesheet() -> str:
    """Devuelve el contenido del tema QSS, o cadena vacía si no existe."""
    qss_path = CONFIG_DIR / "theme.qss"
    if qss_path.exists():
        content = qss_path.read_text(encoding="utf-8")
        assets_dir = (BASE_DIR / "assets").as_posix()
        return content.replace("{assets_dir}", assets_dir)
    return ""


def save_settings(settings: dict) -> None:
    """Persiste la configuración en settings.json y refresca la caché."""
    global _SETTINGS_CACHE
    with open(CONFIG_DIR / "settings.json", "w", encoding="utf-8") as fh:
        json.dump(settings, fh, indent=2, ensure_ascii=False)
    _SETTINGS_CACHE = settings
