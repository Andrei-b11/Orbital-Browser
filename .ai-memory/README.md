# 🧠 ZONA DE MEMORIA — Orbital

> **LEE ESTE ARCHIVO PRIMERO.** Esta carpeta es la memoria persistente del proyecto.
> Cualquier IA (Claude, Cursor, Windsurf, etc.) que trabaje en el proyecto debe
> leer estos archivos **antes** de tocar código, y **actualizarlos después** de
> cada cambio. El proyecto será muy grande; esta memoria evita perder contexto.

---

## 📌 ¿Qué es este proyecto?

**Orbital**: un navegador web de escritorio centrado en privacidad y estética
minimalista (estilo Zen/Arc), construido en **Python con PyQt6** sobre el motor
**Chromium (QtWebEngine)**. Plan completo en [`../plan.md`](../plan.md).

---

## 📂 Mapa de la memoria

| Archivo | Contenido | Cuándo leerlo / actualizarlo |
|---|---|---|
| `README.md` | Este índice y las reglas de uso | Leer siempre primero |
| `00_PROYECTO.md` | Visión, objetivos y stack tecnológico | Al iniciar / si cambia el alcance |
| `01_ARQUITECTURA.md` | Estructura de carpetas y módulos | Antes de crear/mover archivos |
| `02_ESTADO_ACTUAL.md` | Qué está hecho y qué falta (por fase) | **Cada sesión**: leer al empezar, marcar al terminar |
| `03_CHANGELOG.md` | Registro cronológico de cambios | **Después de cada cambio** |
| `04_DECISIONES.md` | Decisiones técnicas y su justificación | Al tomar una decisión de diseño |
| `05_CONVENCIONES.md` | Estilo de código, nombres y reglas | Antes de escribir código |

---

## 🔁 PROTOCOLO PARA LA IA (obligatorio)

**Al empezar una sesión:**
1. Lee `README.md` → `02_ESTADO_ACTUAL.md` → `01_ARQUITECTURA.md`.
2. Revisa `04_DECISIONES.md` para no contradecir decisiones previas.

**Al terminar un cambio:**
1. Añade una entrada en `03_CHANGELOG.md` (fecha, qué, por qué, archivos tocados).
2. Actualiza las casillas de `02_ESTADO_ACTUAL.md`.
3. Si tomaste una decisión de diseño, anótala en `04_DECISIONES.md`.

**Regla de oro:** si algo no está escrito aquí, asúmelo como *no hecho*.
Nunca borres historial del changelog; sólo se añade.

---

_Memoria inicializada el 2026-05-30._
