"""Punto de entrada de Orbital y bucle de eventos (Fase 1).

Ejecutar desde la raíz del repositorio:
    python nexus_browser/main.py
"""
from __future__ import annotations

import os
import sys

# Permite los imports absolutos del paquete (`core`, `ui`, `utils`)
# tanto si se ejecuta como script directo como desde otra ruta.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from core.config import load_settings, load_stylesheet  # noqa: E402
from ui.main_window import MainBrowserWindow  # noqa: E402


def main() -> int:
    settings = load_settings()

    # Configurar el AppUserModelID para que Windows muestre el icono correcto y en alta resolución.
    if sys.platform == "win32":
        import ctypes
        try:
            myappid = "orbital.browser.v1"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    # Los flags de Chromium deben inyectarse en argv ANTES de crear QApplication.
    for flag in settings.get("chromium_flags", []):
        if flag not in sys.argv:
            sys.argv.append(flag)

    app = QApplication(sys.argv)
    app.setApplicationName(settings.get("app_name", "Orbital"))

    from PyQt6.QtGui import QIcon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "orbital_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    window = MainBrowserWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
