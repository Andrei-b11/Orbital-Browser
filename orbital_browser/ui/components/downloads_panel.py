"""Panel lateral derecho de descargas recientes (Fase 2 + Configuración).

Muestra el listado de descargas de la sesión, indicando el nombre del archivo,
su tamaño, estado de la descarga y progreso actual con una barra de progreso.
Permite cerrar el panel y abrir el historial completo.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRectF, QUrl
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QStyle,
)
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest


def format_size(bytes_count: int) -> str:
    if bytes_count <= 0:
        return "0 B"
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f} KB"
    else:
        return f"{bytes_count / (1024 * 1024):.1f} MB"


class DownloadItemWidget(QWidget):
    """Fila individual de descarga con icono, nombre, progreso y metadatos."""

    def __init__(self, item: QWebEngineDownloadRequest) -> None:
        super().__init__()
        self.item = item
        self.setObjectName("DownloadItem")
        self._build()
        self.update_state()

    def _build(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Icono de archivo Lucide
        self.icon_label = QLabel()
        from utils.icon_loader import get_lucide_pixmap
        self.icon_label.setPixmap(get_lucide_pixmap("file-text", color="#9696a0", size=18))
        self.icon_label.setFixedSize(18, 18)
        layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignTop)

        # Columna de texto
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.name_label = QLabel(self.item.downloadFileName())
        self.name_label.setObjectName("DownloadItemName")
        self.name_label.setStyleSheet("font-weight: 600; font-size: 12px; color: #e3e3e9;")
        self.name_label.setWordWrap(True)
        text_layout.addWidget(self.name_label)

        self.meta_label = QLabel()
        self.meta_label.setObjectName("DownloadItemMeta")
        self.meta_label.setStyleSheet("font-size: 11px; color: #8a8a93;")
        text_layout.addWidget(self.meta_label)

        # Barra de progreso
        self.progress = QProgressBar()
        self.progress.setObjectName("DownloadItemProgress")
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.hide()
        text_layout.addWidget(self.progress)

        layout.addLayout(text_layout, 1)

    def update_state(self) -> None:
        """Actualiza las etiquetas y la barra de progreso basándose en el estado."""
        total = self.item.totalBytes()
        received = self.item.receivedBytes()
        
        # Calcular porcentaje
        if total > 0:
            percent = int(received * 100 / total)
        else:
            percent = -1

        size_str = format_size(total if total > 0 else received)

        if self.item.isFinished():
            self.progress.hide()
            ok = self.item.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted
            if ok:
                self.meta_label.setText(f"{size_str} · Completada")
                self.meta_label.setStyleSheet("font-size: 11px; color: #4ec9b0;")
                self.setToolTip("Doble clic para abrir/ejecutar el archivo")
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.meta_label.setText(f"{size_str} · Fallida")
                self.meta_label.setStyleSheet("font-size: 11px; color: #f44747;")
                self.setToolTip("Descarga fallida")
                self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.progress.show()
            if percent >= 0:
                self.progress.setValue(percent)
                self.meta_label.setText(f"{format_size(received)} de {size_str} ({percent}%)")
            else:
                self.progress.setRange(0, 0)  # indeterminado
                self.meta_label.setText(f"{format_size(received)} (Descargando...)")
            self.meta_label.setStyleSheet("font-size: 11px; color: #ff6b00;")
            self.setToolTip("Descargando...")
            self.setCursor(Qt.CursorShape.ArrowCursor)


class DownloadsPanel(QFrame):
    """Panel flotante de descargas recientes."""

    open_full_downloads = pyqtSignal()

    def __init__(self, download_manager, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.manager = download_manager
        self.setObjectName("DownloadsPanel")
        self.setFixedWidth(320)
        self._build()
        self._wire_events()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Cabecera
        header = QFrame()
        header.setObjectName("DownloadsPanelHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 10, 14, 10)

        title = QLabel("Historial de descargas recientes")
        title.setStyleSheet("font-weight: 600; font-size: 13px; color: #e3e3e9;")
        header_layout.addWidget(title)

        close_btn = QPushButton()
        from utils.icon_loader import get_lucide_icon
        close_btn.setIcon(get_lucide_icon("x", color="#8a8a93", size=10))
        close_btn.setObjectName("DownloadsPanelClose")
        close_btn.setFixedSize(20, 20)
        close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.hide)
        header_layout.addWidget(close_btn)

        layout.addWidget(header)

        # Lista de descargas
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("DownloadsPanelList")
        self.list_widget.setSpacing(4)
        layout.addWidget(self.list_widget, 1)

        # Pie de página (Enlace al historial completo)
        footer = QFrame()
        footer.setObjectName("DownloadsPanelFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 8, 10, 8)

        full_btn = QPushButton("Historial de descargas completo")
        from utils.icon_loader import get_lucide_icon
        full_btn.setIcon(get_lucide_icon("external-link", color="#ff6b00", size=12))
        full_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        full_btn.setObjectName("DownloadsPanelFullLink")
        full_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        full_btn.clicked.connect(self.open_full_downloads.emit)
        footer_layout.addWidget(full_btn, 1)

        layout.addWidget(footer)

    def _wire_events(self) -> None:
        self.manager.started.connect(self.refresh)
        self.manager.progress.connect(self._on_progress)
        self.manager.finished.connect(self._on_finished)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dibujar fondo mate oscuro (#16161a) y borde (#2d2d37)
        painter.setBrush(QColor("#16161a"))
        painter.setPen(QPen(QColor("#2d2d37"), 1))
        
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.drawRoundedRect(rect, 12, 12)
        painter.end()

    def refresh(self) -> None:
        """Reconstruye la lista de descargas basándose en los items del manager."""
        self.list_widget.clear()
        
        # Mostrar placeholder si no hay descargas
        if not self.manager.items:
            placeholder_item = QListWidgetItem()
            self.list_widget.addItem(placeholder_item)
            
            placeholder_widget = QWidget()
            placeholder_layout = QVBoxLayout(placeholder_widget)
            placeholder_layout.setContentsMargins(20, 20, 20, 20)
            placeholder_layout.setSpacing(6)
            placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            from utils.icon_loader import get_lucide_pixmap
            icon_label = QLabel()
            icon_label.setPixmap(get_lucide_pixmap("download", color="#5c5c68", size=24))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder_layout.addWidget(icon_label)
            
            text_label = QLabel("No hay descargas recientes")
            text_label.setStyleSheet("color: #8a8a93; font-size: 12px; font-weight: 500;")
            text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder_layout.addWidget(text_label)
            
            placeholder_item.setSizeHint(QSize(0, 100))
            self.list_widget.setItemWidget(placeholder_item, placeholder_widget)
            return

        # Mostrar los últimos 15 elementos en orden inverso (más recientes primero)
        for item in reversed(self.manager.items[-15:]):
            list_item = QListWidgetItem()
            self.list_widget.addItem(list_item)
            
            widget = DownloadItemWidget(item)
            list_item.setSizeHint(QSize(0, 60))
            self.list_widget.setItemWidget(list_item, widget)

    def _on_progress(self, name: str, percent: int) -> None:
        self._update_item_widget(name)

    def _on_finished(self, name: str, ok: bool) -> None:
        self._update_item_widget(name)

    def _update_item_widget(self, name: str) -> None:
        for i in range(self.list_widget.count()):
            list_item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(list_item)
            if isinstance(widget, DownloadItemWidget) and widget.item.downloadFileName() == name:
                widget.update_state()
                break

    def _on_item_double_clicked(self, list_item: QListWidgetItem) -> None:
        widget = self.list_widget.itemWidget(list_item)
        if isinstance(widget, DownloadItemWidget):
            item = widget.item
            # Solo intentar abrir si el estado es completado y finalizado
            if item.isFinished() and item.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
                import os
                path = os.path.join(item.downloadDirectory(), item.downloadFileName())
                if os.path.exists(path):
                    # Si el archivo es un PDF, lo abrimos en una nueva pestaña del navegador
                    if path.lower().endswith(".pdf"):
                        window = self.window()
                        if window and hasattr(window, "add_new_tab"):
                            window.add_new_tab(QUrl.fromLocalFile(path))
                            self.hide()  # Ocultar el panel emergente de descargas al abrir la pestaña
                            return
                    
                    # Para otros tipos de archivos, abrirlos/ejecutarlos en el sistema operativo
                    try:
                        os.startfile(path)
                    except Exception as e:
                        print(f"Error al abrir el archivo descargado: {e}")
