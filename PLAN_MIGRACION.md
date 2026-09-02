# Migración a Clean/Hexagonal Architecture + SOLID + TDD ligero

## Contexto

El proyecto actual (`main.py`, `app.py`, `models.py`, `strategies.py`, ~350 líneas, cero tests) mezcla en `app.py` la UI de Tkinter con la orquestación del cálculo, y en `models.py` mezcla lógica de dominio pura (payoff, agregación de greeks) con un algoritmo de pricing concreto (Black-Scholes-Merton vía SciPy). El objetivo no es solo reordenar carpetas: es que cada paso enseñe un principio arquitectónico concreto (por qué el dominio no debe conocer SciPy, por qué los casos de uso dependen de interfaces y no de clases concretas, etc.) y que el proyecto **nunca quede roto** entre pasos — siempre se puede correr `python main.py` y `pytest -q`.

Ya existe un diagrama de arquitectura objetivo (`arquitectura_opciones.tex`, ignorado por git) que el usuario aceptó conceptualmente. Este plan sigue esa estructura de carpetas al pie de la letra: `domain/`, `application/`, `infrastructure/`, `presentation/`, `tests/`.

El repo ya tiene un commit inicial pusheado a `github.com/odinjere/Calculadora-Opciones-Python` (rama `master`). Cada fase de este plan termina en un commit propio, dejando siempre `pytest -q` en verde y la app funcional.

**Hallazgo clave que condiciona el diseño:** dentro de `models.py`, la función `greeks()` (y sus helpers `_d1d2`, `bsm`) NO es lógica de dominio — es un modelo de pricing concreto e intercambiable. Por eso migra a `infrastructure/` como adaptador detrás de un `PricingPort`, mientras que la *agregación* de greeks de varias patas (sumar con el signo y multiplicador correctos) sí es dominio puro y migra a `domain/`.

## Enfoque: TDD ligero

- **Dominio y casos de uso** (fases 1 y 3): test antes que código, porque ahí vive la lógica de negocio real.
- **Puertos, wiring, views** (fases 2 y 5 parcialmente): sin test obligatorio — son interfaces o código mecánico sin decisiones que puedan romperse.
- **Fase 0** no es TDD: es "characterization testing" — capturar el comportamiento actual como red de seguridad antes de tocar nada.

## Fases

### Fase 0 — Red de seguridad (characterization tests)
**Por qué:** antes de mover una sola línea, necesitamos una forma automática de detectar si algo se rompió. Se testea el `models.py` actual tal cual, sin tocarlo.

- Crear `requirements-dev.txt` (pytest) — separado de runtime deps.
- Crear `conftest.py` (raíz) + `pyproject.toml` mínimo con `testpaths = tests`.
- `tests/unit/test_models_characterization.py`:
  - BSM contra un valor analítico conocido (S=100,K=100,T=1,σ=0.2,r=0.05,q=0 → call ≈ 10.4506)
  - `strategy_payoff` sobre "Bull Call Spread" en puntos por debajo/entre/encima de los strikes
  - `strategy_greeks` sobre "Long Straddle"
  - `approximate_breakevens` con un cruce simple
  - `probability_metrics` sobre "Long Call" (`pytest.approx`)

**Verificación:** `pytest -q` verde (~6-8 tests). `python main.py` sin tocar.

---

### Fase 1 — Dominio puro
**Por qué:** el dominio es el núcleo hexagonal — no depende de Tkinter, pandas ni scipy. Se aprende la diferencia entre Entity (identidad + comportamiento) y Value Object (inmutable, sin identidad).

Crear:
- `domain/value_objects/option_type.py` — `OptionType(str, Enum)`: CALL/PUT. Hereda de `str` a propósito, para no romper comparaciones existentes mientras se gana seguridad de tipos.
- `domain/value_objects/position_side.py` — mismo patrón: COMPRA/VENTA.
- `domain/entities/leg.py` — migra `Leg` + `signed_quantity` de `models.py:5-15`, tipado con los VOs de arriba.
- `domain/entities/strategy.py` — nueva agregación `list[Leg]` + `multiplier`, con `payoff(spot)` migrando `payoff_leg`+`strategy_payoff` (`models.py:17-28`).
- `domain/entities/greeks.py` — Value Object inmutable con `aggregate(...)`, migra **solo** el loop de suma de `strategy_greeks` (`models.py:66-73`) — NO el cálculo BSM.
- `domain/services/breakeven_finder.py` — migra `approximate_breakevens` (`models.py:75-82`) como domain service (no pertenece a ninguna entidad concreta).

TDD real: test antes de cada clase. Los tests de `Strategy` reusan los mismos números de la Fase 0 (deben coincidir).

**Verificación:** `pytest -q` verde (Fase 0 + nuevos). `app.py` sigue importando `models.py` viejo — nada conectado todavía.

---

### Fase 2 — Puertos (interfaces)
**Por qué:** Inversión de Dependencias — el contrato se define antes que la implementación.

Crear en `application/ports/`:
- `pricing_port.py` — `PricingPort(ABC)` con `price_leg(spot, leg, days, sigma, r, q) -> Greeks`. Se usa `ABC` (no `Protocol`) a propósito: la herencia explícita hace visible dónde ocurre la inversión de dependencia, más didáctico para aprender el patrón.
- `strategy_port.py` — `get_template(name)`, `list_template_names()`.
- `exporter_port.py` — `export(prices, pnl, path)`.

**Testing:** ninguno obligatorio (interfaces sin lógica).
**Verificación:** el proyecto importa sin error. `python main.py` sin tocar.

---

### Fase 3 — Casos de uso, testeados con fakes
**Por qué:** el momento clave para "entender el por qué" del DIP. Se escriben los casos de uso contra los puertos, sin que exista todavía ningún adaptador real — probados con fakes escritos a mano. Esto demuestra que la orquestación de negocio se testea en milisegundos, sin Tkinter/matplotlib/scipy.

Crear:
- `application/dtos/input_dto.py` (`MarketParamsDTO`) y `output_dto.py` (`CalculationResultDTO`) — agrupan lo que hoy son variables sueltas en `app.py`.
- `application/use_cases/calculate_strategy.py` — migra la orquestación de cálculo de `app.calculate()` (`app.py:61-68`), usando `Strategy.payoff()`, `pricing_port` por pata, `Greeks.aggregate()`, `breakeven_finder`.
- `application/use_cases/probability_metrics.py` — migra `probability_metrics` (`models.py:84-94`), compuesto internamente por el caso de uso de arriba.
- `application/use_cases/load_template.py` — migra la parte no-UI de `app.load_template()` (`app.py:55`).
- `application/use_cases/export_strategy.py` — migra la lógica (no el diálogo) de `app.export()` (`app.py:75,78-79`).

TDD real: fakes mínimos (`FakePricingEngine(PricingPort)` devolviendo valores fijos) para probar que el caso de uso combina bien payoff real + greeks fake, aislando "¿la orquestación es correcta?" de "¿el BSM es correcto?".

**Verificación:** `pytest -q` verde con fakes. `python main.py` **todavía sin tocar** — nada de esto está conectado a la UI real todavía.

---

### Fase 4 — Adaptadores reales + test de contrato
**Por qué:** con el puerto y el consumidor ya probados, se escribe la implementación concreta. Demuestra Liskov: el adaptador real debe reemplazar al fake sin que el caso de uso note diferencia.

Crear:
- `infrastructure/adapters/bsm_pricing.py` — `BSMPricingEngine(PricingPort)`, migra `_d1d2`, `bsm`, `greeks` (`models.py:30-64`). Test: reapuntar los tests BSM de la Fase 0 contra este adaptador — deben dar igual.
- `infrastructure/config/templates.py` — migra `TEMPLATES` de `strategies.py`, ahora usando `Leg`/`OptionType`/`PositionSide` del dominio.
- `infrastructure/repositories/strategy_repository.py` — `InMemoryStrategyRepository(StrategyPort)` envolviendo `templates.py`.
- `infrastructure/adapters/file_exporter.py` — `PandasFileExporter(ExporterPort)`, migra `to_csv`/`to_excel` (`app.py:78-79`). Test con `tmp_path` de pytest: exportar y releer.

**Verificación:** `pytest -q` verde completo (dominio + aplicación con fakes + infraestructura real). `python main.py` **sigue sin tocarse** — todo el hexágono ya existe y está probado en paralelo, sin riesgo, porque nada lo usa todavía.

---

### Fase 5 — Strangler fig de la UI (presentation)
**Por qué:** único paso que toca `app.py` de verdad. Patrón "Humble Object": la parte que toca Tkinter directo queda deliberadamente sin lógica de negocio (no necesita test), mientras toda decisión vive en el controller, que al delegar a los casos de uso ya heredó la cobertura de las fases 3-4.

Crear:
- `presentation/views/main_window.py` — migra `app.build()` (`app.py:15-46`), solo construcción de widgets.
- `presentation/models/tk_models.py` — mapper StringVars ↔ dominio: migra `app.legs()` (`app.py:47-53`) y la asignación de `load_template` (`app.py:56-59`). Es la capa anticorrupción: el dominio usa enums, la UI sigue mostrando "CALL"/"COMPRA" en español.
- `presentation/controllers/app_controller.py` — migra la parte de UI de `app.calculate()` (`app.py:68-72`) y `app.export()` (`app.py:76,80`). No calcula nada: llama a los casos de uso y solo pinta el resultado.
- `main.py` (modificado) — se convierte en el Composition Root: único archivo que conoce clases concretas de todas las capas, arma la inyección de dependencias y llama `mainloop()`.

**Testing opcional:** un test de integración sin Tkinter (`tests/integration/test_full_pipeline.py`) que arma el hexágono completo con adaptadores reales y compara contra el golden master de la Fase 0.

**Verificación (la más importante del plan):** correr `python main.py`, probar las 11 plantillas, CALCULAR y EXPORTAR, confirmar que layout/gráfico/tabla/métricas son idénticos a antes (comparables número a número gracias al golden master). `pytest -q` verde completo.

---

### Fase 6 — Limpieza final
**Por qué:** cerrar el strangler fig retirando el andamiaje legacy — nada de código muerto confundiendo a un futuro lector.

- Eliminar `models.py`, `strategies.py`, la versión vieja de `app.py`.
- Actualizar `requirements.txt`/`requirements-dev.txt` y `README.md` (nueva estructura + cómo correr pytest).
- `pytest -q` + `python main.py` de punta a punta como aceptación final.

## Commits

Un commit por fase (0 a 6), cada uno con `pytest -q` verde y `python main.py` funcional — nunca a mitad de fase con el árbol roto.

## Siguiente paso inmediato

Empezar por la Fase 0 (red de seguridad), ya que todo lo demás depende de tener ese golden master antes de mover código.
