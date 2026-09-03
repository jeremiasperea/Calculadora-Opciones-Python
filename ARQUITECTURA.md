# Calculadora de Opciones — Arquitectura y Plan de Migración

> Documento único. Reemplaza a `PLAN_MIGRACION.md`, `PLAN_MIGRACION_v2.md`,
> `ARQUITECTURA_FINAL.md` y `README_DETALLADO.md`.

---

## 1. Qué es este proyecto

Calculadora de estrategias de opciones financieras. Construye estrategias de
hasta 6 patas (CALL/PUT × compra/venta), calcula el P&L al vencimiento, los
griegos vía Black-Scholes-Merton, los puntos de equilibrio y la probabilidad
de beneficio. Grafica el perfil de riesgo y exporta los escenarios.

**Usuario final:** un operador de valores que conoce la operatoria de opciones
pero **no programa**. Corre la app en su propia máquina, sin instalar nada
complicado y sin cuenta de usuario.

**Objetivo del trabajo:** migrar de un monolito acoplado a arquitectura
hexagonal, entendiendo en cada paso *qué* se hace, *por qué*, y *qué riesgo*
tiene. El aprendizaje vale más que el resultado.

---

## 2. Estado actual (pre-migración)

```
main.py         7 líneas   entry point
app.py         81 líneas   UI Tkinter + parseo + orquestación + pintado
models.py      95 líneas   entidad Leg + payoff + BSM + griegos + probabilidades
strategies.py  16 líneas   11 plantillas de estrategias
```

### Los dos problemas de fondo

**1. `app.py` hace cuatro trabajos a la vez.** Construye widgets, parsea lo que
el usuario escribió, orquesta el cálculo y pinta el resultado. No se puede
probar ninguna de esas cuatro cosas sin levantar una ventana.

**2. `models.py` mezcla dos capas distintas.** Tiene lógica de negocio pura
(el payoff al vencimiento, la agregación de griegos) *y* un modelo de pricing
concreto (`bsm`, `_d1d2`, `greeks`, que dependen de SciPy).

Esa segunda confusión es la más importante de entender, porque decide toda la
migración: **el payoff de una opción es una definición contractual** — un call
vale `max(spot - strike, 0)` al vencimiento y punto, eso es dominio. En cambio
**Black-Scholes es *una* forma de estimar el precio antes del vencimiento**,
intercambiable por un árbol binomial o Monte Carlo. Eso es infraestructura.

Mucha gente mete el pricing en el "core" porque "es matemática de negocio".
No lo es: es una implementación entre varias posibles.

### Limitaciones conocidas (no se resuelven en la migración)

| No soporta | Motivo |
|---|---|
| Volatilidad implícita | No resuelve BSM inverso |
| Opciones americanas | BSM es europeo |
| Volatility smile | σ constante por estrategia |
| Dividendos discretos | Sólo yield continuo `q` |
| Costos de transacción | P&L teórico, sin spread ni comisiones |

Supuestos del modelo: precios lognormales, volatilidad y tasa constantes,
365 días por año, ejercicio sólo al vencimiento.

---

## 3. Arquitectura objetivo

```
┌──────────────────────────────────────────────┐
│  Flet  (navegador)                           │  ← adaptador de entrada/salida
│  inputs · gráfico de payoff · tabla · botones│
└───────────────────┬──────────────────────────┘
                    │ llamadas Python directas
                    ▼
┌──────────────────────────────────────────────┐
│  Casos de uso (application/)                 │  ← orquestación
│  CalculateStrategy · LoadTemplate            │
│  ExportStrategy · SaveSimulation             │
└───────────────────┬──────────────────────────┘
                    │ depende de interfaces, no de clases
                    ▼
┌──────────────────────────────────────────────┐
│  Puertos (application/ports/)                │  ← contratos
│  PricingPort · StrategyPort                  │
│  ExporterPort · PersistencePort              │
└───────────────────┬──────────────────────────┘
                    │ implementados por
        ┌───────────┴────────────┐
        ▼                        ▼
┌────────────────┐    ┌─────────────────────────┐
│ Dominio        │    │ Infraestructura         │
│ (sin imports   │    │ BSMPricingEngine → SciPy│
│  externos)     │    │ FileExporter    → Pandas│
│ Leg · Strategy │    │ SQLitePersist.  → SQLite│
│ Greeks · VOs   │    │ TemplateRepo    → dict  │
└────────────────┘    └─────────────────────────┘
```

**La regla que ordena todo:** las flechas apuntan hacia adentro. El dominio no
importa nada. Los casos de uso importan el dominio y los puertos, nunca una
implementación concreta. La infraestructura implementa los puertos.

### Por qué Flet llama directo a los casos de uso (y no hay FastAPI)

La app es **local y monousuario**. Meter un servidor HTTP en el medio agrega
dos procesos, serialización JSON de arrays de 401 floats en cada cálculo, DTOs
duplicados y un modo de falla nuevo — a cambio de nada.

**El punto pedagógico:** si la arquitectura está bien hecha, agregar FastAPI
después es *un adaptador de entrada más*, sin tocar el núcleo. Dejarlo para
una fase posterior no es postergarlo: es la **demostración empírica** de que la
separación en capas sirve. Meterlo desde el principio te lo cuenta; agregarlo
al final te lo prueba.

---

## 4. Plan de fases

Cada fase termina con `pytest` en verde y la app funcionando. Un commit por
fase. Nunca se commitea con el árbol roto.

### Fase 0 — Red de seguridad ✅ COMPLETA

Tests de caracterización sobre el código actual, **sin tocarlo**. No es TDD:
es capturar el comportamiento que hay hoy como especificación.

16 tests, incluyendo:
- BSM contra el valor analítico conocido (10.4506 para el caso de manual)
- Payoff del Bull Call Spread en tres zonas
- **Golden master end-to-end** del pipeline completo (Iron Condor)
- Escalado lineal del multiplicador

**Validada con pruebas de mutación:** se inyectaron tres bugs a propósito
(signo invertido, multiplicador al cuadrado, theta sin escalar) y se verificó
que los tests los detectan. La segunda mutación descubrió un agujero real —
todos los tests usaban `multiplier=1`, y `1×1=1` hace el bug invisible. De ahí
salió `TestMultiplicador`.

> **Lección:** un parámetro con valor neutro (1 al multiplicar, 0 al sumar)
> nunca debe testearse sólo con ese valor.

### Fase 1 — Dominio puro ✅ COMPLETA

`domain/` sin un solo import externo. Ni SciPy, ni Pandas, ni Flet.

- `value_objects/option_type.py` — `OptionType(str, Enum)`: CALL/PUT
- `value_objects/position_side.py` — `PositionSide(str, Enum)`: COMPRA/VENTA
- `entities/leg.py` — migra `Leg` y `signed_quantity`
- `entities/strategy.py` — agregado nuevo: `list[Leg]` + `payoff(spot)`
- `entities/greeks.py` — value object + `aggregate()` (**sólo la suma**, no BSM)
- `services/breakeven_finder.py` — migra `approximate_breakevens`

**Concepto:** Entity vs Value Object. Un `Leg` tiene comportamiento e
invariantes. Un `OptionType` sólo define qué valores son válidos.

**TDD real acá:** test primero, después la clase.

### Fase 2 — Puertos ✅ COMPLETA

`application/ports/` con `ABC`. Interfaces sin implementación.

`PricingPort` · `StrategyPort` · `ExporterPort` · `PersistencePort`

**Concepto:** definir el contrato antes que la implementación. Se usa `ABC` y
no `Protocol` a propósito: la herencia explícita hace *visible* dónde se
invierte la dependencia.

### Fase 3 — Casos de uso ✅ COMPLETA

`application/use_cases/`, escritos contra los puertos, **antes de que exista
ningún adaptador real**. Se prueban con *fakes* escritos a mano.

**Concepto:** inversión de dependencias. Acá se ve en carne propia que la
lógica de negocio se testea en milisegundos sin SciPy, sin base de datos y sin
interfaz gráfica.

### Fase 4 — Adaptadores ✅ COMPLETA

`infrastructure/`: `BSMPricingEngine`, `TemplateRepository`, `FileExporter`
(CSV/Excel/**JSON**/PDF), `SQLitePersistence`.

Los tests BSM de la Fase 0 se re-apuntan al adaptador nuevo: deben dar los
**mismos números**.

**Concepto:** sustitución de Liskov. El adaptador real reemplaza al fake sin
que el caso de uso note la diferencia.

### Fase 5 — Interfaz Flet ✅ COMPLETA

`ui/` con Flet, llamando directo a los casos de uso. Patrón *humble object*:
la parte que toca Flet no toma decisiones de negocio, así que no necesita
tests automatizados.

`main.py` pasa a ser el **composition root**: el único archivo que conoce
clases concretas de todas las capas y arma la inyección de dependencias.

### Fase 6 — Limpieza ✅ COMPLETA

Eliminar `app.py`, `models.py`, `strategies.py`. Actualizar `README.md`.

### Fase 7 — Persistencia ✅ COMPLETA

Guardar y recuperar simulaciones en SQLite.

```sql
CREATE TABLE simulations (
  id            TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  strategy_legs JSON NOT NULL,
  market_params JSON NOT NULL,
  result        JSON NOT NULL
);
```

### Fase 8 — API REST con FastAPI ✅ COMPLETA

Exponer los mismos casos de uso por HTTP. **Es un adaptador de entrada más:
no debería tocar ni una línea del dominio ni de los casos de uso.** Si hay que
modificarlos, la arquitectura de las fases 1-4 estaba mal, y eso mismo es la
lección.

---

## 5. Decisiones tomadas

| Decisión | Elegido | Por qué |
|---|---|---|
| Persistencia | SQLite | Local, sin servidor, con queries |
| Autenticación | No | App local, un operador |
| Compartir estrategias | No (MVP) | Exportar JSON alcanza por ahora |
| Exportación | CSV · Excel · JSON · PDF | JSON permite reimportar |
| Frontend | Flet | Web moderna, sin backend separado |
| FastAPI | Fase 8, no MVP | Demuestra que la arquitectura sirve |
| Gestor de paquetes | UV | Más rápido, mejor lockfile |
| Tests | Mínimo viable | Dominio 100%, casos de uso alto, UI manual |

### Honestidad sobre el alcance

Esto **no es un refactor**: es una reescritura con arquitectura nueva. Cambia
la UI, se agrega base de datos, se agregan formatos de exportación y cambia el
gestor de paquetes. Está bien que así sea, pero conviene llamarlo por su
nombre para no subestimar el esfuerzo.

También: para 195 líneas de código, esta ceremonia arquitectónica sería
excesiva en un proyecto real. Se justifica porque **el objetivo declarado es
aprender la arquitectura**, y lo que se practica acá se paga solo cuando el
proyecto tiene 20.000 líneas y varias personas tocándolo.

---

## 6. Cómo correr

```bash
# Tests
pytest -q

# App (estado actual, Tkinter — hasta la Fase 5)
python main.py
```

Desde la Fase 1 el proyecto migra a UV:

```bash
uv sync            # instalar dependencias
uv run pytest -q   # tests
uv run python -m ui.main
```
