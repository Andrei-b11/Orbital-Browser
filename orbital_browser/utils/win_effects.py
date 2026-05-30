"""Efectos nativos de ventana en Windows (Fase 2).

Aplica esquinas redondeadas reales y color de borde mediante la API DWM de
Windows 11. En otras plataformas o versiones antiguas las llamadas fallan de
forma silenciosa y la ventana se muestra con esquinas rectas.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

# Atributos DWM (dwmapi.h)
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWA_BORDER_COLOR = 34
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20

# Valores de DWM_WINDOW_CORNER_PREFERENCE
_DWMWCP_ROUND = 2


def _set_attribute(hwnd: int, attribute: int, value: int) -> None:
    try:
        val = ctypes.c_int(value)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd),
            ctypes.c_uint(attribute),
            ctypes.byref(val),
            ctypes.sizeof(val),
        )
    except (OSError, AttributeError):
        # dwmapi inexistente o versión de Windows sin soporte: se ignora.
        pass


def apply_rounded_corners(hwnd: int) -> None:
    """Redondea las esquinas de la ventana (Windows 11)."""
    if sys.platform != "win32" or not hwnd:
        return
    _set_attribute(hwnd, _DWMWA_WINDOW_CORNER_PREFERENCE, _DWMWCP_ROUND)


def apply_dark_titlebar(hwnd: int) -> None:
    """Fuerza el modo oscuro del marco del sistema (por si quedara visible)."""
    if sys.platform != "win32" or not hwnd:
        return
    _set_attribute(hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, 1)
