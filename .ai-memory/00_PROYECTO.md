# 00 · Visión del Proyecto

## Nombre
**Orbital**

## Objetivo
Navegador de escritorio enfocado en **privacidad**, **velocidad** y una **interfaz
minimalista** (estilo Zen / Arc). Bloqueo nativo de anuncios y telemetría, motor de
búsqueda privado integrado ("OrbitalSearch") y normalización visual de favicons.

## Stack tecnológico
| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.x |
| GUI | PyQt6 (`QtWidgets`) |
| Motor web | Chromium vía `QtWebEngine` (`QWebEngineView`, `QWebEngineProfile`) |
| Persistencia | SQLite (cifrado simétrico previsto) |
| Imágenes / favicons | Pillow (PIL) |
| Puente JS↔Python | `QWebChannel` |
| Compilación | Nuitka (Python → C++) para el binario final |

## Las 6 fases del plan
1. **Core & Arquitectura** — entorno PyQt6 + Chromium, multihilo (`QThread`), SQLite cifrado.
2. **UI/UX & Iconografía** — interfaz frameless, pestañas verticales colapsables, Omnibox, normalización de favicons.
3. **Privacidad & Ad-block** — interceptor de red nativo, aislamiento de almacenamiento por pestaña/perfil.
4. **Sistema de Extensiones** — puente `QWebChannel`, emulación parcial de WebExtensions (`chrome.runtime`, `chrome.tabs`).
5. **Motor de Búsqueda ("OrbitalSearch")** — router meta-query, anonimización, UI de resultados sobre el Omnibox.
6. **Distribución Binaria** — compilación con Nuitka, flags de Chromium para rendimiento.

## Estado de partida
El repositorio contiene **únicamente el documento de plan** (`plan.md`). El código del
"script maestro" descrito en el plan **todavía no existe como archivos reales**; hay que
implementarlo siguiendo la estructura de `01_ARQUITECTURA.md`.

> Nota: el `main.py` de ejemplo dentro de `plan.md` tiene URLs envueltas en markdown
> (`[https://...](...)`) y un fragmento de escritura de archivo roto al final. Al
> implementar de verdad, usar URLs limpias y corregir esos errores.
