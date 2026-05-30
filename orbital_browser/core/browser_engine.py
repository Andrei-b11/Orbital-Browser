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
from PyQt6.QtWidgets import QApplication

from core.config import DATA_DIR
from core.privacy_shield import PrivacyShield


_PROFILE_CACHE: dict[str, tuple[QWebEngineProfile, PrivacyShield]] = {}


def configure_profile(settings: dict, profile_name: str = "Default") -> tuple[QWebEngineProfile, PrivacyShield]:
    """Crea, configura y cachea el perfil de Chromium; devuelve (perfil, escudo)."""
    global _PROFILE_CACHE
    
    private = settings.get("private_mode", False)

    if private:
        # Perfil privado (off-the-record). Parentado a la QApplication para que
        # Qt lo destruya limpiamente al cerrar (evita problemas de orden de GC).
        profile = QWebEngineProfile(QApplication.instance())
        shield = PrivacyShield(settings.get("blocklist", []))
        profile.setUrlRequestInterceptor(shield)
        
        # Activar el visor de PDF nativo de Chromium
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)
        
        # Optimización de carga y rendimiento de Chromium (GPU, WebGL, DNS, etc.)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.BackForwardCacheEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.HyperlinkAuditingEnabled, False)
        
        # Spoofing de User-Agent para mitigar el fingerprinting del navegador.
        profile.setHttpUserAgent(settings["user_agent"])
        
        # Idioma de aceptación de contenido.
        accept_lang = settings.get("accept_language")
        if accept_lang:
            profile.setHttpAcceptLanguage(accept_lang)
            
        return profile, shield

    if profile_name not in _PROFILE_CACHE:
        # Perfil con nombre -> persistente. Definimos rutas propias dentro de data/.
        profile_dir = DATA_DIR / "profiles" / profile_name
        (profile_dir / "profile").mkdir(parents=True, exist_ok=True)
        (profile_dir / "cache").mkdir(parents=True, exist_ok=True)

        # Usar un nombre de almacenamiento persistente único para evitar conflictos con el de Qt.
        # IMPORTANTE: parentar el perfil a la QApplication. Si no, el diccionario
        # _PROFILE_CACHE lo mantiene vivo hasta el final del intérprete y su
        # destructor (que vuelca cookies/almacenamiento a disco) corre cuando Qt
        # ya no existe, perdiéndose los últimos inicios de sesión. Con padre, Qt
        # lo destruye durante el cierre de la app y vuelca los datos.
        storage_name = f"orbital_{profile_name}"
        profile = QWebEngineProfile(storage_name, QApplication.instance())

        profile.setPersistentStoragePath(str(profile_dir / "profile"))
        profile.setCachePath(str(profile_dir / "cache"))
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        cache_mb = int(settings.get("cache_max_size_mb", 512))
        profile.setHttpCacheMaximumSize(cache_mb * 1024 * 1024)
        
        # Cookies persistentes: las sesiones de login sobreviven al reinicio.
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )

        # Activar el visor de PDF nativo de Chromium
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.PdfViewerEnabled, True)

        # Optimización de carga y rendimiento de Chromium (GPU, WebGL, DNS, etc.)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.BackForwardCacheEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.WebAttribute.HyperlinkAuditingEnabled, False)

        # Spoofing de User-Agent para mitigar el fingerprinting del navegador.
        profile.setHttpUserAgent(settings["user_agent"])

        # Idioma de aceptación de contenido.
        accept_lang = settings.get("accept_language")
        if accept_lang:
            profile.setHttpAcceptLanguage(accept_lang)

        # Inyección del escudo de privacidad nativo (interceptor de red).
        shield = PrivacyShield(settings.get("blocklist", []))
        profile.setUrlRequestInterceptor(shield)
        
        _PROFILE_CACHE[profile_name] = (profile, shield)

    return _PROFILE_CACHE[profile_name]


def clear_browsing_data(profile: QWebEngineProfile) -> None:
    """Borra cookies y caché HTTP del perfil (acción de privacidad bajo demanda)."""
    store = profile.cookieStore()
    if store is not None:
        store.deleteAllCookies()
    profile.clearHttpCache()
    profile.clearAllVisitedLinks()
