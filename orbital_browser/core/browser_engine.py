"""Configuración del perfil de QtWebEngine (Fase 1 + 3).

Aplica la política del navegador y la **persistencia**:
- Modo normal: perfil con nombre que guarda cookies y caché HTTP en disco
  (`data/profile` y `data/cache`), de modo que las sesiones de los sitios web
  se recuerdan entre ejecuciones.
- Modo privado (`settings.private_mode`): perfil *off-the-record* en memoria,
  sin rastro en disco.

También inyecta el escudo de privacidad (interceptor de red) y el User-Agent.
"""
from __future__ import annotations

from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings

from core.config import DATA_DIR
from core.privacy_shield import PrivacyShield


def configure_profile(settings: dict) -> tuple[QWebEngineProfile, PrivacyShield]:
    """Crea y configura el perfil de Chromium; devuelve (perfil, escudo)."""
    private = settings.get("private_mode", False)

    if private:
        # Perfil sin nombre -> off-the-record (todo en memoria, nada en disco).
        profile = QWebEngineProfile()
    else:
        # Perfil con nombre -> persistente. Definimos rutas propias dentro de data/.
        profile = QWebEngineProfile("orbital")
        profile.setPersistentStoragePath(str(DATA_DIR / "profile"))
        profile.setCachePath(str(DATA_DIR / "cache"))
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        cache_mb = int(settings.get("cache_max_size_mb", 150))
        profile.setHttpCacheMaximumSize(cache_mb * 1024 * 1024)
        # Cookies persistentes: las sesiones de login sobreviven al reinicio.
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )

    # Activar el visor de PDF nativo de Chromium
    profile.settings().setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)

    # Spoofing de User-Agent para mitigar el fingerprinting del navegador.
    profile.setHttpUserAgent(settings["user_agent"])

    # Idioma de aceptación de contenido.
    accept_lang = settings.get("accept_language")
    if accept_lang:
        profile.setHttpAcceptLanguage(accept_lang)

    # Inyección del escudo de privacidad nativo (interceptor de red).
    shield = PrivacyShield(settings.get("blocklist", []))
    profile.setUrlRequestInterceptor(shield)

    return profile, shield


def clear_browsing_data(profile: QWebEngineProfile) -> None:
    """Borra cookies y caché HTTP del perfil (acción de privacidad bajo demanda)."""
    store = profile.cookieStore()
    if store is not None:
        store.deleteAllCookies()
    profile.clearHttpCache()
    profile.clearAllVisitedLinks()
