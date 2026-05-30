"""Árbol de prefijos (Trie) en memoria para autocompletado (Fase 5).

Indexa las URLs visitadas para ofrecer sugerencias predictivas locales en el
Omnibox sin enviar nada a la red. Las búsquedas son por prefijo y devuelven las
cadenas completas almacenadas.
"""
from __future__ import annotations


class _Node:
    __slots__ = ("children", "is_end")

    def __init__(self) -> None:
        self.children: dict[str, _Node] = {}
        self.is_end: bool = False


class Trie:
    """Trie sencillo orientado a autocompletado de URLs/consultas."""

    def __init__(self) -> None:
        self._root = _Node()
        self._size = 0

    def insert(self, word: str) -> None:
        word = (word or "").strip()
        if not word:
            return
        node = self._root
        for ch in word:
            node = node.children.setdefault(ch, _Node())
        if not node.is_end:
            node.is_end = True
            self._size += 1

    def starts_with(self, prefix: str, limit: int = 8) -> list[str]:
        """Devuelve hasta `limit` palabras que comienzan por `prefix`."""
        prefix = (prefix or "").strip()
        if not prefix:
            return []

        # Para que sea intuitivo, si el prefijo no tiene esquema, probamos con variantes estándar
        # e interceptamos coincidencias unificadas sin duplicados.
        prefixes_to_try = [prefix]
        if not prefix.startswith(("http://", "https://", "orbital://", "file://")):
            prefixes_to_try.append("https://" + prefix)
            prefixes_to_try.append("https://www." + prefix)
            prefixes_to_try.append("http://" + prefix)
            prefixes_to_try.append("http://www." + prefix)
            if not prefix.startswith("www."):
                prefixes_to_try.append("www." + prefix)

        results: list[str] = []
        seen = set()

        for pref in prefixes_to_try:
            node = self._root
            possible = True
            for ch in pref:
                node = node.children.get(ch)
                if node is None:
                    possible = False
                    break
            if possible:
                temp_results = []
                self._collect(node, pref, temp_results, limit)
                for r in temp_results:
                    if r not in seen:
                        seen.add(r)
                        results.append(r)
                        if len(results) >= limit:
                            return results

        return results

    def _collect(self, node: _Node, path: str, out: list[str], limit: int) -> None:
        if len(out) >= limit:
            return
        if node.is_end:
            out.append(path)
        for ch, child in node.children.items():
            if len(out) >= limit:
                return
            self._collect(child, path + ch, out, limit)

    def __len__(self) -> int:
        return self._size
