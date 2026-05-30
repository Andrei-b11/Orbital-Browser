"""Zona de configuración: diálogo nativo de ajustes (Fase 2).

Edita un subconjunto seguro de `settings.json`. Algunos cambios (modo privado,
frameless) requieren reiniciar; se avisa al guardar.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QComboBox,
)

from core.config import save_settings


class SettingsDialog(QDialog):
    """Ventana de ajustes que escribe en settings.json."""

    def __init__(self, settings: dict, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setObjectName("SettingsDialog")
        self.setWindowTitle("Configuración · Orbital")
        self.setModal(True)
        self.setMinimumWidth(440)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        title = QLabel("Configuración")
        title.setObjectName("SettingsTitle")
        root.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.home_edit = QLineEdit(self.settings.get("home_url", ""))
        form.addRow("Página de inicio:", self.home_edit)

        self.search_combo = QComboBox()
        self.search_combo.addItems([
            "Google",
            "DuckDuckGo",
            "Bing",
            "Ecosia",
            "Personalizado"
        ])
        
        self.search_edit = QLineEdit(self.settings.get("search_endpoint", ""))
        self.search_edit_label = QLabel("URL del motor de búsqueda:")
        
        current_endpoint = self.settings.get("search_endpoint", "")
        if "google.com/search" in current_endpoint:
            self.search_combo.setCurrentIndex(0)
            self.search_edit.setVisible(False)
            self.search_edit_label.setVisible(False)
        elif "duckduckgo.com" in current_endpoint:
            self.search_combo.setCurrentIndex(1)
            self.search_edit.setVisible(False)
            self.search_edit_label.setVisible(False)
        elif "bing.com" in current_endpoint:
            self.search_combo.setCurrentIndex(2)
            self.search_edit.setVisible(False)
            self.search_edit_label.setVisible(False)
        elif "ecosia.org" in current_endpoint:
            self.search_combo.setCurrentIndex(3)
            self.search_edit.setVisible(False)
            self.search_edit_label.setVisible(False)
        else:
            self.search_combo.setCurrentIndex(4)
            self.search_edit.setVisible(True)
            self.search_edit_label.setVisible(True)

        self.search_combo.currentIndexChanged.connect(self._on_search_engine_changed)

        form.addRow("Motor de búsqueda:", self.search_combo)
        form.addRow(self.search_edit_label, self.search_edit)

        self.chk_private = QCheckBox("Modo privado (sin cookies ni caché en disco)")
        self.chk_private.setChecked(self.settings.get("private_mode", False))
        form.addRow("Privacidad:", self.chk_private)

        self.chk_restore = QCheckBox("Guardar pestañas al cerrar la aplicación (restaurar sesión al abrir)")
        self.chk_restore.setChecked(self.settings.get("restore_session", True))
        form.addRow("Sesión:", self.chk_restore)

        self.chk_tint = QCheckBox("Unificar el color de los favicons")
        self.chk_tint.setChecked(self.settings.get("tint_favicons", True))
        form.addRow("Apariencia:", self.chk_tint)

        self.chk_frameless = QCheckBox("Ventana sin bordes (estilo Orbital)")
        self.chk_frameless.setChecked(self.settings.get("frameless", True))
        form.addRow("Ventana:", self.chk_frameless)

        # Nueva configuración de pestañas
        self.tab_pos_combo = QComboBox()
        self.tab_pos_combo.addItems(["Lateral (vertical)", "Superior (horizontal)"])
        current_pos = self.settings.get("tab_position", "left")
        self.tab_pos_combo.setCurrentIndex(0 if current_pos == "left" else 1)
        form.addRow("Posición de pestañas:", self.tab_pos_combo)

        # Nueva configuración de descargas
        self.dl_view_combo = QComboBox()
        self.dl_view_combo.addItems(["Ventana emergente flotante", "Pestaña de descargas"])
        current_dl = self.settings.get("downloads_view", "panel")
        self.dl_view_combo.setCurrentIndex(0 if current_dl == "panel" else 1)
        form.addRow("Mostrar descargas en:", self.dl_view_combo)

        root.addLayout(form)

        self.note = QLabel("Algunos cambios se aplican al reiniciar el navegador.")
        self.note.setObjectName("SettingsNote")
        root.addWidget(self.note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _on_search_engine_changed(self, index: int) -> None:
        if index == 0:
            self.search_edit.setText("https://www.google.com/search?q=")
            self.search_edit.setVisible(False)
            self.search_edit_label.setVisible(False)
        elif index == 1:
            self.search_edit.setText("https://duckduckgo.com/?q=")
            self.search_edit.setVisible(False)
            self.search_edit_label.setVisible(False)
        elif index == 2:
            self.search_edit.setText("https://www.bing.com/search?q=")
            self.search_edit.setVisible(False)
            self.search_edit_label.setVisible(False)
        elif index == 3:
            self.search_edit.setText("https://www.ecosia.org/search?q=")
            self.search_edit.setVisible(False)
            self.search_edit_label.setVisible(False)
        else:
            self.search_edit.setVisible(True)
            self.search_edit_label.setVisible(True)

    def _on_save(self) -> None:
        self.settings["home_url"] = self.home_edit.text().strip() or self.settings["home_url"]
        self.settings["search_endpoint"] = (
            self.search_edit.text().strip() or self.settings["search_endpoint"]
        )
        self.settings["private_mode"] = self.chk_private.isChecked()
        self.settings["restore_session"] = self.chk_restore.isChecked()
        self.settings["tint_favicons"] = self.chk_tint.isChecked()
        self.settings["frameless"] = self.chk_frameless.isChecked()
        
        self.settings["tab_position"] = "left" if self.tab_pos_combo.currentIndex() == 0 else "top"
        self.settings["downloads_view"] = "panel" if self.dl_view_combo.currentIndex() == 0 else "tab"
        
        save_settings(self.settings)
        self.accept()
