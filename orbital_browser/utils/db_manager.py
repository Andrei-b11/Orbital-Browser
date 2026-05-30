"""Gestor de persistencia local en SQLite: historial y marcadores (Fase 1).

NOTA DE SEGURIDAD: por ahora la base de datos se almacena en texto plano.
El cifrado simétrico (decisión D-004, pendiente: SQLCipher vs. cifrado por
campo) se incorporará antes de la distribución. Ver `.ai-memory/04_DECISIONES.md`.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class DBManager:
    """Acceso simple y seguro al almacenamiento local del navegador."""

    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: el acceso se hará desde el hilo de UI por ahora;
        # al introducir QThread (Fase 1) se serializará con una cola dedicada.
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._closed = False
        
        # Optimizar base de datos con modo WAL (Write-Ahead Logging) y almacenamiento temporal en memoria
        try:
            self.conn.execute("PRAGMA journal_mode = WAL;")
            self.conn.execute("PRAGMA synchronous = NORMAL;")
            self.conn.execute("PRAGMA temp_store = MEMORY;")
        except Exception:
            pass
            
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                url        TEXT    NOT NULL,
                title      TEXT,
                visited_at TEXT    NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bookmarks (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                url        TEXT    NOT NULL UNIQUE,
                title      TEXT,
                created_at TEXT    NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS downloads (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT    NOT NULL,
                directory   TEXT    NOT NULL,
                total_bytes INTEGER DEFAULT 0,
                succeeded   INTEGER DEFAULT 0,
                created_at  TEXT    NOT NULL
            )
            """
        )
        self.conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # --- Historial -------------------------------------------------------
    def add_history(self, url: str, title: str = "") -> None:
        if self._closed or not url or url.startswith("about:"):
            return
        self.conn.execute(
            "INSERT INTO history (url, title, visited_at) VALUES (?, ?, ?)",
            (url, title, self._now()),
        )
        self.conn.commit()

    def recent_history(self, limit: int = 50) -> list[sqlite3.Row]:
        if self._closed:
            return []
        cur = self.conn.execute(
            "SELECT url, title, visited_at FROM history ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cur.fetchall()

    # --- Marcadores ------------------------------------------------------
    def add_bookmark(self, url: str, title: str = "") -> None:
        if self._closed:
            return
        self.conn.execute(
            "INSERT OR IGNORE INTO bookmarks (url, title, created_at) VALUES (?, ?, ?)",
            (url, title, self._now()),
        )
        self.conn.commit()

    def list_bookmarks(self) -> list[sqlite3.Row]:
        if self._closed:
            return []
        cur = self.conn.execute(
            "SELECT url, title, created_at FROM bookmarks ORDER BY id DESC"
        )
        return cur.fetchall()

    # --- Descargas -------------------------------------------------------
    def add_download(self, filename: str, directory: str, total_bytes: int, succeeded: bool) -> None:
        if self._closed:
            return
        self.conn.execute(
            "INSERT INTO downloads (filename, directory, total_bytes, succeeded, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (filename, directory, int(total_bytes), 1 if succeeded else 0, self._now()),
        )
        self.conn.commit()

    def recent_downloads(self, limit: int = 100) -> list[sqlite3.Row]:
        if self._closed:
            return []
        cur = self.conn.execute(
            "SELECT filename, directory, total_bytes, succeeded, created_at "
            "FROM downloads ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cur.fetchall()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.conn.close()
