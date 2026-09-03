# Calculadora de Estrategias de Opciones

Construí estrategias de opciones de hasta 6 patas, mirá el perfil de P&L al
vencimiento y analizá el riesgo antes de operar.

- Payoff y P&L al vencimiento, graficado
- Griegos (delta, gamma, vega, theta, rho) vía Black-Scholes-Merton
- Puntos de equilibrio y probabilidad de beneficio
- 11 plantillas: Long Call, Bull Call Spread, Iron Condor, Straddle, Butterfly,
  Backspreads y más
- Exportación a CSV, Excel, JSON (reimportable) y PDF con gráfico
- Guardado de simulaciones para retomarlas después

> **Herramienta educativa.** No usa datos de mercado en vivo y asume
> volatilidad constante, precios lognormales y ejercicio sólo al vencimiento.
> No la uses para decidir operaciones reales sin contrastar con tu bróker.

---

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

```bash
python -m ui.main
```

Se abre como aplicación de escritorio. Para usarla en el navegador:

```bash
python -c "import flet as ft; from ui.main import main; ft.run(main, view=ft.AppView.WEB_BROWSER)"
```

**API REST:**

```bash
uvicorn api.main:app --reload
```

Documentación interactiva en `http://localhost:8000/docs`.

| método | ruta | |
|---|---|---|
| GET | `/api/templates` | plantillas disponibles |
| GET | `/api/templates/{nombre}` | una plantilla |
| POST | `/api/calculate` | calcular una estrategia |
| GET | `/api/simulations` | simulaciones guardadas |
| POST | `/api/simulations` | guardar |
| GET | `/api/simulations/{id}` | abrir |
| DELETE | `/api/simulations/{id}` | borrar |

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

---

## Estructura

```
domain/          entidades y reglas de negocio, sin dependencias externas
application/     casos de uso y puertos (interfaces)
infrastructure/  Black-Scholes, exportadores, persistencia, plantillas
ui/              interfaz Flet (adaptador de entrada)
api/             API REST con FastAPI (otro adaptador de entrada)
tests/           518 tests
```

Arquitectura hexagonal: las dependencias apuntan hacia adentro. El dominio no
importa nada; los casos de uso dependen de interfaces, no de implementaciones.

El plan completo y el porqué de cada decisión están en
**[ARQUITECTURA.md](ARQUITECTURA.md)**.

| Fase | Estado |
|---|---|
| 0 · Red de seguridad (16 tests) | ✅ |
| 1 · Dominio puro | ✅ |
| 2 · Puertos | ✅ |
| 3 · Casos de uso | ✅ |
| 4 · Adaptadores | ✅ |
| 5 · Interfaz Flet | ✅ |
| 6 · Limpieza | ✅ |
| 7 · Persistencia SQLite | ✅ |
| 8 · API REST (FastAPI) | ✅ |
