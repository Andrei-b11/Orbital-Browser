# 05 · Convenciones de Código

## Lenguaje y estilo
- **Python 3.x**, sigue **PEP 8**.
- Nombres: `snake_case` para funciones/variables, `PascalCase` para clases,
  `UPPER_SNAKE` para constantes.
- Cada módulo y clase pública con **docstring** breve (en español, como el plan).
- Type hints en firmas de funciones públicas siempre que sea razonable.

## Organización
- Respeta la estructura de carpetas de `01_ARQUITECTURA.md`. No mezclar UI con lógica de red.
- Un `__init__.py` por paquete (`core/`, `ui/`, `ui/components/`, `utils/`).
- Configuración (colores, flags, endpoints) fuera del código → `config/settings.json` y `config/theme.qss`.

## UI / Tema
- Colores **siempre** desde la paleta definida en `01_ARQUITECTURA.md` (acento `#ff6b00`).
- Preferir cargar QSS desde `config/theme.qss` en vez de strings embebidos en Python.

## Git / commits (cuando exista repo)
- Commits pequeños y descriptivos, en imperativo. Ej: `feat(core): add PrivacyShield interceptor`.
- Prefijos: `feat`, `fix`, `refactor`, `docs`, `chore`.

## Regla de memoria
- Tras cualquier cambio relevante: actualizar `02_ESTADO_ACTUAL.md` y `03_CHANGELOG.md`.
- Decisiones de diseño → `04_DECISIONES.md`.
