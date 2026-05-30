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
from PyQt6.QtNetwork import QLocalServer, QLocalSocket  # noqa: E402

from core.config import load_settings, load_stylesheet  # noqa: E402
from ui.main_window import MainBrowserWindow  # noqa: E402

# Nombre del servidor local que identifica la instancia única de la app.
_SINGLETON_NAME = "OrbitalBrowserSingleInstance"


def _claim_single_instance() -> QLocalServer | None:
    """Garantiza una sola instancia (un solo proceso usando el perfil).

    Si ya hay otra instancia viva, le pide que se muestre y devuelve None (esta
    debe salir). Si no, reclama el "candado" y devuelve el servidor. Dos procesos
    sobre el mismo perfil bloquean el almacenamiento de Chromium y hacen que se
    pierdan cookies e inicios de sesión, así que esto es imprescindible.
    """
    probe = QLocalSocket()
    probe.connectToServer(_SINGLETON_NAME)
    if probe.waitForConnected(300):
        # Hay una instancia viva: pedirle que traiga su ventana al frente.
        probe.write(b"raise")
        probe.flush()
        probe.waitForBytesWritten(300)
        probe.disconnectFromServer()
        return None

    # Sin instancia previa (o murió): limpiar restos y reclamar el candado.
    # En Windows el named pipe se libera al morir el proceso, así que un cierre
    # real no deja el candado bloqueado.
    QLocalServer.removeServer(_SINGLETON_NAME)
    server = QLocalServer()
    server.listen(_SINGLETON_NAME)
    return server


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

    # Instancia única: si ya hay otra corriendo, traerla al frente y salir, para
    # no abrir dos procesos peleando por el almacenamiento del mismo perfil.
    instance_server = _claim_single_instance()
    if instance_server is None:
        return 0

    from PyQt6.QtGui import QIcon
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "orbital_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)

    # Cuando otra instancia intente arrancar, traer al frente la ventana actual.
    def _on_second_instance() -> None:
        conn = instance_server.nextPendingConnection()
        if conn is not None:
            conn.readyRead.connect(conn.deleteLater)
        for win in list(MainBrowserWindow.windows):
            win.showNormal()
            win.raise_()
            win.activateWindow()

    instance_server.newConnection.connect(_on_second_instance)

    window = MainBrowserWindow()
    window.show()
    rc = app.exec()
    instance_server.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
