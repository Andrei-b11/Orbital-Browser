"""Gestor de descargas (Fase 1, funcionamiento).

Escucha la señal `downloadRequested` del perfil de Chromium, acepta las
descargas hacia la carpeta `data/downloads` y publica el progreso mediante
señales que la ventana principal muestra en la barra de estado.

El historial se persiste en SQLite (tabla `downloads`), de modo que las
descargas completadas sobreviven al reinicio de la aplicación.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEngineProfile


class DownloadEntry:
    """Representación uniforme de una descarga, viva o restaurada del historial.

    Expone la misma forma que la UI ya consumía de `QWebEngineDownloadRequest`
    (`downloadFileName()`, `downloadDirectory()`, `totalBytes()`, …). Si está
    viva, delega en la petición real; si se restauró de la base de datos,
    devuelve los datos estáticos guardados.
    """

    def __init__(
        self,
        *,
        filename: str,
        directory: str,
        total_bytes: int = 0,
        received_bytes: int = 0,
        finished: bool = False,
        succeeded: bool = False,
        request: QWebEngineDownloadRequest | None = None,
    ) -> None:
        self._filename = filename
        self._directory = directory
        self._total = total_bytes
        self._received = received_bytes
        self._finished = finished
        self._succeeded = succeeded
        self.request = request  # QWebEngineDownloadRequest si la descarga está activa

    def downloadFileName(self) -> str:
        return self.request.downloadFileName() if self.request else self._filename

    def downloadDirectory(self) -> str:
        return self.request.downloadDirectory() if self.request else self._directory

    def totalBytes(self) -> int:
        return self.request.totalBytes() if self.request else self._total

    def receivedBytes(self) -> int:
        return self.request.receivedBytes() if self.request else self._received

    def isFinished(self) -> bool:
        return self.request.isFinished() if self.request else self._finished

    def succeeded(self) -> bool:
        """True si la descarga terminó correctamente."""
        if self.request is not None:
            return self.request.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted
        return self._succeeded


class DownloadManager(QObject):
    """Acepta y supervisa las descargas del perfil, y persiste el historial."""

    started = pyqtSignal(str)            # nombre de archivo
    progress = pyqtSignal(str, int)      # nombre, porcentaje (0-100, -1 si desconocido)
    finished = pyqtSignal(str, bool)     # nombre, éxito

    def __init__(self, profile: QWebEngineProfile, download_dir: str, db=None) -> None:
        super().__init__()
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.db = db
        self.items: list[DownloadEntry] = []

        # Restaurar el historial persistido (más antiguas primero, para que las
        # descargas nuevas de esta sesión se añadan a continuación en orden).
        if db is not None:
            for rec in reversed(db.recent_downloads(limit=100)):
                ok = bool(rec["succeeded"])
                self.items.append(
                    DownloadEntry(
                        filename=rec["filename"],
                        directory=rec["directory"],
                        total_bytes=rec["total_bytes"],
                        received_bytes=rec["total_bytes"] if ok else 0,
                        finished=True,
                        succeeded=ok,
                    )
                )

        profile.downloadRequested.connect(self._on_requested)

    def _on_requested(self, item: QWebEngineDownloadRequest) -> None:
        item.setDownloadDirectory(str(self.download_dir))
        entry = DownloadEntry(
            filename=item.downloadFileName(),
            directory=str(self.download_dir),
            request=item,
        )
        self.items.append(entry)
        item.accept()
        self.started.emit(entry.downloadFileName())

        item.receivedBytesChanged.connect(lambda it=item: self._on_progress(it))
        item.isFinishedChanged.connect(lambda e=entry: self._on_finished(e))

    def _on_progress(self, item: QWebEngineDownloadRequest) -> None:
        total = item.totalBytes()
        received = item.receivedBytes()
        percent = int(received * 100 / total) if total > 0 else -1
        self.progress.emit(item.downloadFileName(), percent)

    def _on_finished(self, entry: DownloadEntry) -> None:
        item = entry.request
        if item is None or not item.isFinished():
            return
        ok = item.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted

        # Persistir el resultado para que sobreviva al reinicio.
        if self.db is not None:
            self.db.add_download(
                item.downloadFileName(),
                item.downloadDirectory(),
                item.totalBytes(),
                ok,
            )
        self.finished.emit(item.downloadFileName(), ok)
