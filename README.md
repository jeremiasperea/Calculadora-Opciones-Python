# Calculadora de Estrategias de Opciones

Construí estrategias de opciones de hasta 6 patas, mirá el perfil de P&L al
vencimiento y analizá el riesgo antes de operar.

- Payoff y P&L al vencimiento, graficado
- Griegos (delta, gamma, vega, theta, rho) vía Black-Scholes-Merton
- Puntos de equilibrio y probabilidad de beneficio
- 11 plantillas: Long Call, Bull Call Spread, Iron Condor, Straddle, Butterfly,
  Backspreads y más
- Exportación de escenarios a CSV y Excel

> **Herramienta educativa.** No usa datos de mercado en vivo y asume
> volatilidad constante, precios lognormales y ejercicio sólo al vencimiento.
> No la uses para decidir operaciones reales sin contrastar con tu bróker.

---

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

---

## 🚧 Estado: en migración

El proyecto está migrando a **arquitectura hexagonal**, con interfaz **Flet**
(navegador) y persistencia de simulaciones en **SQLite**. La versión Tkinter
de arriba sigue siendo la funcional hasta que termine la Fase 5.

El plan completo, las decisiones de diseño y el porqué de cada paso están en
**[ARQUITECTURA.md](ARQUITECTURA.md)**.

| Fase | Estado |
|---|---|
| 0 · Red de seguridad (16 tests) | ✅ |
| 1 · Dominio puro | ✅ |
| 2 · Puertos | ✅ |
| 3 · Casos de uso | ✅ |
| 4 · Adaptadores | ⬜ |
| 5 · Interfaz Flet | ⬜ |
| 6 · Limpieza | ⬜ |
| 7 · Persistencia SQLite | ⬜ |
| 8 · API FastAPI (opcional) | ⬜ |
