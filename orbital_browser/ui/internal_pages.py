"""Páginas internas del navegador (Fase 2): inicio, historial, marcadores,
descargas y errores. Se renderizan con `view.setHtml(...)` usando el tema oscuro.

La navegación entre zonas usa enlaces `orbital://…` que intercepta `OrbitalPage`.
"""
from __future__ import annotations

from html import escape
import base64
from pathlib import Path

def _get_logo_base64() -> str:
    try:
        icon_path = Path(__file__).parent.parent / "assets" / "orbital_icon.png"
        if icon_path.exists():
            with open(icon_path, "rb") as fh:
                return base64.b64encode(fh.read()).decode("utf-8")
    except Exception:
        pass
    return ""


_STYLE = """
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    background: #0f0f11; color: #e3e3e9; margin: 0; min-height: 100vh;
    font-family: 'Segoe UI', system-ui, sans-serif;
  }
  nav {
    display: flex; gap: 4px; padding: 10px 24px;
    background: #131316; border-bottom: 1px solid #23232a;
    position: sticky; top: 0;
  }
  nav a {
    color: #9696a0; text-decoration: none; font-size: 13px;
    padding: 6px 14px; border-radius: 8px;
  }
  nav a:hover { background: #1d1d22; color: #fff; }
  nav a.active { background: #212127; color: #fff; }
  header { padding: 28px 40px 12px; }
  h1 { font-size: 24px; margin: 0; font-weight: 600; }
  .sub { color: #6c6c78; font-size: 13px; margin-top: 4px; }
  ul { list-style: none; margin: 0; padding: 8px 24px 48px; }
  li {
    padding: 11px 16px; border-radius: 10px; margin: 2px 0;
    display: flex; gap: 12px; align-items: baseline;
  }
  li:hover { background: #16161a; }
  a.item { color: #e3e3e9; text-decoration: none; font-size: 14px; }
  a.item:hover { color: #ff6b00; }
  .meta { color: #6c6c78; font-size: 12px; margin-left: auto; white-space: nowrap; }
  .empty { color: #6c6c78; padding: 16px 40px; font-style: italic; }
  .accent { color: #ff6b00; }

  /* Página de inicio */
  .hero {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; padding: 14vh 20px 0;
  }
  .logo {
    width: 64px; height: 64px; border-radius: 18px; background: #ff6b00;
    display: flex; align-items: center; justify-content: center;
    font-size: 34px; font-weight: 800; color: #fff; margin-bottom: 18px;
  }
  .logo-img {
    width: 64px; height: 64px; border-radius: 18px;
    margin-bottom: 18px;
    object-fit: contain;
  }
  .brand { font-size: 26px; font-weight: 600; margin-bottom: 26px; }
  form { width: min(560px, 90vw); display: flex; }
  input[type=text] {
    flex: 1; background: #212127; color: #e3e3e9; border: 1px solid #2d2d37;
    border-radius: 12px; padding: 13px 18px; font-size: 15px; outline: none;
    font-family: inherit;
  }
  input[type=text]:focus { border-color: #ff6b00; background: #16161a; }
  .quick { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;
           margin-top: 26px; width: min(560px, 90vw); }
  .chip {
    background: #16161a; border: 1px solid #23232a; border-radius: 10px;
    padding: 9px 14px; font-size: 13px; color: #c8c8d0; text-decoration: none;
    max-width: 170px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .chip:hover { border-color: #ff6b00; color: #fff; }

  /* Páginas de error */
  .center {
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; min-height: 80vh; text-align: center; padding: 20px;
  }
  .glyph { font-size: 56px; margin-bottom: 12px; }
  .center h1 { font-size: 22px; }
  .center p { color: #9696a0; max-width: 460px; }
  .btn {
    margin-top: 18px; background: #ff6b00; color: #fff; text-decoration: none;
    padding: 10px 22px; border-radius: 10px; font-size: 14px;
  }
  .btn:hover { background: #ff7d1f; }
  code { color: #c8c8d0; background: #16161a; padding: 2px 8px; border-radius: 6px; }
</style>
"""

_ZONES = [
    ("orbital://start", "Inicio"),
    ("orbital://history", "Historial"),
    ("orbital://bookmarks", "Marcadores"),
    ("orbital://downloads", "Descargas"),
    ("orbital://settings", "Configuración"),
]


def _nav(active: str) -> str:
    links = []
    for href, label in _ZONES:
        cls = "active" if href == f"orbital://{active}" else ""
        links.append(f"<a class='{cls}' href='{href}'>{label}</a>")
    return "<nav>" + "".join(links) + "</nav>"


def _doc(title: str, active: str, body: str) -> str:
    return (
        f"<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>"
        f"<title>{escape(title)}</title>{_STYLE}</head><body>"
        f"{_nav(active)}{body}</body></html>"
    )


def _list(rows: list[tuple[str, str, str]]) -> str:
    if not rows:
        return "<p class='empty'>No hay elementos todavía.</p>"
    items = []
    for url, title, meta in rows:
        label = escape(title or url)
        items.append(
            f"<li><a class='item' href='{escape(url)}'>{label}</a>"
            f"<span class='meta'>{escape(meta)}</span></li>"
        )
    return "<ul>" + "".join(items) + "</ul>"


def start_page(action: str, query_param: str, quick_links: list[tuple[str, str]]) -> str:
    chips = "".join(
        f"<a class='chip' href='{escape(u)}'>{escape(t or u)}</a>"
        for u, t in quick_links
    )
    
    logo_b64 = _get_logo_base64()
    if logo_b64:
        logo_html = f"<img src='data:image/png;base64,{logo_b64}' class='logo-img' />"
    else:
        logo_html = "<div class='logo'>O</div>"
        
    body = (
        "<div class='hero'>"
        f"{logo_html}"
        "<div class='brand'>Orbital</div>"
        f"<form action='{escape(action)}' method='get'>"
        f"<input type='text' name='{escape(query_param)}' autofocus "
        "placeholder='Busca en la web de forma privada…' "
        "autocomplete='off' spellcheck='false'></form>"
        f"<div class='quick'>{chips}</div>"
        "</div>"
    )
    return _doc("Orbital", "start", body)


def history_page(records: list) -> str:
    rows = [(r["url"], r["title"], (r["visited_at"] or "")[:19].replace("T", " "))
            for r in records]
    body = (f"<header><h1><span class='accent'>◷</span> Historial</h1>"
            f"<div class='sub'>{len(rows)} páginas visitadas (recientes)</div></header>"
            f"{_list(rows)}")
    return _doc("Historial", "history", body)


def bookmarks_page(records: list) -> str:
    rows = [(r["url"], r["title"], (r["created_at"] or "")[:10]) for r in records]
    body = (f"<header><h1><span class='accent'>★</span> Marcadores</h1>"
            f"<div class='sub'>{len(rows)} marcadores guardados</div></header>"
            f"{_list(rows)}")
    return _doc("Marcadores", "bookmarks", body)


def downloads_page(items: list) -> str:
    rows = []
    for it in items:
        name = it.downloadFileName()
        meta = "Completada" if it.isFinished() else "En curso…"
        rows.append((name, name, meta))
    body = (f"<header><h1><span class='accent'>⬇</span> Descargas</h1>"
            f"<div class='sub'>{len(rows)} descargas</div></header>"
            f"{_list(rows)}")
    return _doc("Descargas", "downloads", body)


def error_page(url: str) -> str:
    body = (
        "<div class='center'>"
        "<div class='glyph accent'>⚠</div>"
        "<h1>No se pudo cargar la página</h1>"
        "<p>No se ha podido establecer conexión con el sitio. Comprueba la dirección "
        "o tu conexión a internet.</p>"
        f"<p><code>{escape(url)}</code></p>"
        f"<a class='btn' href='{escape(url)}'>Reintentar</a>"
        "</div>"
    )
    return _doc("Error de carga", "", body)


def crash_page(url: str) -> str:
    body = (
        "<div class='center'>"
        "<div class='glyph accent'>✖</div>"
        "<h1>La pestaña ha dejado de responder</h1>"
        "<p>El proceso de renderizado se cerró inesperadamente. Puedes recargar "
        "la página para continuar.</p>"
        f"<a class='btn' href='{escape(url)}'>Recargar</a>"
        "</div>"
    )
    return _doc("Pestaña interrumpida", "", body)
