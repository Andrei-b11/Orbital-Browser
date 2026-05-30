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

_SETTINGS_CACHES: dict[str, dict] = {}


def load_global_settings() -> dict:
    """Carga o inicializa el registro global de perfiles."""
    global_path = DATA_DIR / "global_settings.json"
    if not global_path.exists():
        global_path.parent.mkdir(parents=True, exist_ok=True)
        default_global = {
            "current_profile": "Default",
            "profiles": ["Default"]
        }
        with open(global_path, "w", encoding="utf-8") as fh:
            json.dump(default_global, fh, indent=2, ensure_ascii=False)
        return default_global
    try:
        with open(global_path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"current_profile": "Default", "profiles": ["Default"]}


def save_global_settings(global_settings: dict) -> None:
    """Guarda el registro global de perfiles."""
    global_path = DATA_DIR / "global_settings.json"
    global_path.parent.mkdir(parents=True, exist_ok=True)
    with open(global_path, "w", encoding="utf-8") as fh:
        json.dump(global_settings, fh, indent=2, ensure_ascii=False)


def load_settings(profile_name: str | None = None) -> dict:
    """Devuelve la configuración específica de un perfil (cacheada)."""
    global _SETTINGS_CACHES
    if profile_name is None:
        global_settings = load_global_settings()
        profile_name = global_settings.get("current_profile", "Default")
    
    if profile_name not in _SETTINGS_CACHES:
        profile_settings_path = DATA_DIR / "profiles" / profile_name / "settings.json"
        if not profile_settings_path.exists():
            profile_settings_path.parent.mkdir(parents=True, exist_ok=True)
            # Copiar del settings.json base
            with open(CONFIG_DIR / "settings.json", encoding="utf-8") as fh:
                default_settings = json.load(fh)
            with open(profile_settings_path, "w", encoding="utf-8") as fh:
                json.dump(default_settings, fh, indent=2, ensure_ascii=False)
            _SETTINGS_CACHES[profile_name] = default_settings
        else:
            with open(profile_settings_path, encoding="utf-8") as fh:
                _SETTINGS_CACHES[profile_name] = json.load(fh)
                
    return _SETTINGS_CACHES[profile_name]


def load_stylesheet() -> str:
    """Devuelve el contenido del tema QSS, o cadena vacía si no existe."""
    qss_path = CONFIG_DIR / "theme.qss"
    if qss_path.exists():
        content = qss_path.read_text(encoding="utf-8")
        assets_dir = (BASE_DIR / "assets").as_posix()
        return content.replace("{assets_dir}", assets_dir)
    return ""


def save_settings(settings: dict, profile_name: str = "Default") -> None:
    """Persiste la configuración del perfil indicado y refresca su caché."""
    global _SETTINGS_CACHES
    profile_settings_path = DATA_DIR / "profiles" / profile_name / "settings.json"
    profile_settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(profile_settings_path, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, indent=2, ensure_ascii=False)
    _SETTINGS_CACHES[profile_name] = settings
