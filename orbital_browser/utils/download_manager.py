"""Gestor de descargas (Fase 1, funcionamiento).

Escucha la señal `downloadRequested` del perfil de Chromium, acepta las
descargas hacia la carpeta `data/downloads` y publica el progreso mediante
señales que la ventana principal muestra en la barra de estado.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEngineProfile


class DownloadManager(QObject):
    """Acepta y supervisa las descargas del perfil."""

    started = pyqtSignal(str)            # nombre de archivo
    progress = pyqtSignal(str, int)      # nombre, porcentaje (0-100, -1 si desconocido)
    finished = pyqtSignal(str, bool)     # nombre, éxito

    def __init__(self, profile: QWebEngineProfile, download_dir: str) -> None:
        super().__init__()
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.items: list[QWebEngineDownloadRequest] = []
        profile.downloadRequested.connect(self._on_requested)

    def _on_requested(self, item: QWebEngineDownloadRequest) -> None:
        item.setDownloadDirectory(str(self.download_dir))
        self.items.append(item)
        item.accept()
        name = item.downloadFileName()
        self.started.emit(name)

        item.receivedBytesChanged.connect(lambda it=item: self._on_progress(it))
        item.isFinishedChanged.connect(lambda it=item: self._on_finished(it))

    def _on_progress(self, item: QWebEngineDownloadRequest) -> None:
        total = item.totalBytes()
        received = item.receivedBytes()
        percent = int(received * 100 / total) if total > 0 else -1
        self.progress.emit(item.downloadFileName(), percent)

    def _on_finished(self, item: QWebEngineDownloadRequest) -> None:
        if not item.isFinished():
            return
        ok = item.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted
        self.finished.emit(item.downloadFileName(), ok)
