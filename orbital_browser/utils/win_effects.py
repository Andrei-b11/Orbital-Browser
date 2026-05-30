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


# ============================================================
#  Marco personalizado (Plan B): ventana nativa con estilos
#  WS_THICKFRAME/WS_CAPTION (para que DWM la redondee y dé
#  sombra) pero sin marco visible, eliminando el área no-cliente
#  en WM_NCCALCSIZE y resolviendo el redimensionado en WM_NCHITTEST.
# ============================================================

# Mensajes de ventana
WM_NCCALCSIZE = 0x0083
WM_NCHITTEST = 0x0084

# Flags de SetWindowPos
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002
_SWP_NOZORDER = 0x0004
_SWP_FRAMECHANGED = 0x0020

# Métricas del sistema
_SM_CXFRAME = 32
_SM_CYFRAME = 33
_SM_CXPADDEDBORDER = 92

# Códigos de resultado de WM_NCHITTEST
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class _NCCALCSIZE_PARAMS(ctypes.Structure):
    _fields_ = [("rgrc", _RECT * 3), ("lppos", ctypes.c_void_p)]


def read_msg(address: int):
    """Devuelve el struct MSG de Windows situado en la dirección dada."""
    return wintypes.MSG.from_address(address)


def _frame_metrics() -> tuple[int, int]:
    g = ctypes.windll.user32.GetSystemMetrics
    cx = g(_SM_CXFRAME) + g(_SM_CXPADDEDBORDER)
    cy = g(_SM_CYFRAME) + g(_SM_CXPADDEDBORDER)
    return cx, cy


def adjust_maximized_client(lparam: int) -> None:
    """Al maximizar, encoge el rect cliente el grosor del marco.

    Una ventana maximizada se posiciona con desbordes negativos para ocultar
    el borde de redimensionado; sin este ajuste el contenido se recortaría y
    se taparía la barra de tareas.
    """
    params = _NCCALCSIZE_PARAMS.from_address(lparam)
    cx, cy = _frame_metrics()
    params.rgrc[0].left += cx
    params.rgrc[0].top += cy
    params.rgrc[0].right -= cx
    params.rgrc[0].bottom -= cy


def hit_test_border(hwnd: int, lparam: int, border: int) -> int | None:
    """Devuelve el código HT* del borde bajo el cursor, o None si es zona cliente."""
    x = ctypes.c_short(lparam & 0xFFFF).value
    y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
    rect = _RECT()
    ctypes.windll.user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect))

    left = x < rect.left + border
    right = x >= rect.right - border
    top = y < rect.top + border
    bottom = y >= rect.bottom - border

    if top and left:
        return HTTOPLEFT
    if top and right:
        return HTTOPRIGHT
    if bottom and left:
        return HTBOTTOMLEFT
    if bottom and right:
        return HTBOTTOMRIGHT
    if left:
        return HTLEFT
    if right:
        return HTRIGHT
    if top:
        return HTTOP
    if bottom:
        return HTBOTTOM
    return None


def force_frame_recalc(hwnd: int) -> None:
    """Provoca un WM_NCCALCSIZE para que se aplique el marco personalizado."""
    if sys.platform != "win32" or not hwnd:
        return
    ctypes.windll.user32.SetWindowPos(
        wintypes.HWND(hwnd),
        None,
        0,
        0,
        0,
        0,
        _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOZORDER | _SWP_FRAMECHANGED,
    )
