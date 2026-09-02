# Calculadora PRO de Estrategias de Opciones — Análisis Técnico Completo

## 📋 Propósito del Proyecto

Aplicación de escritorio (Tkinter) para construir, analizar y visualizar estrategias de opciones financieras. Calcula payoff al vencimiento, griegos (delta, gamma, vega, theta, rho), breakevens aproximados, probabilidad de beneficio y permite exportar datos a CSV/Excel.

**Audiencia:** Traders educativos, profesores de finanzas, estudiantes. **NO es** herramienta de producción (falta datos en vivo, correlaciones, skew, etc.).

---

## 🎯 Funcionalidades Implementadas

### 1. Construcción de Estrategias
- **Máximo 6 patas** (CALL/PUT × COMPRA/VENTA) por estrategia
- **10 plantillas predefinidas:** Long Call, Bull Call Spread, Iron Condor, Long Straddle, Short Straddle, Long Strangle, Bear Put Spread, Butterfly Call, Call/Put Backspread
- **Especificación por pata:** tipo, lado, cantidad, strike, prima pagada
- **UI:** 6 filas de widgets Tkinter con combobx + entry fields

### 2. Cálculos Matemáticos

#### Payoff al vencimiento
- **Fórmula:** `P&L = (intrinsic_value - premium) × quantity_signed × multiplier`
- **Intrinsic value (CALL):** `max(spot - strike, 0)`
- **Intrinsic value (PUT):** `max(strike - spot, 0)`
- **Agregación:** suma lineal de payoffs de todas las patas
- **Resolución:** discretización en 401 puntos uniformes entre `spot × 0.5` y `spot × 1.5`

#### Black-Scholes-Merton Pricing
- **Modelo:** Analítico para opciones europeas
- **Parámetros:** S (spot), K (strike), T (años), σ (IV), r (tasa), q (dividendo continuo)
- **Conversión de tiempo:** días → años divido por 365 (hardcodeado)
- **Supuestos:** lognormalidad, vol constante, tasa constante, sin costo de transacción
- **Implementación:** `scipy.stats.norm.cdf` y `.pdf` para d1, d2

#### Griegos por Pata y Agregados
- **Delta:** sensibilidad al precio del subyacente
- **Gamma:** curvatura (tasa de cambio de delta)
- **Vega:** cambio por 1% de IV (escalado ÷100)
- **Theta:** decaimiento temporal (escalado ÷365 para daily)
- **Rho:** sensibilidad a tasa de interés (escalado ÷100)
- **Agregación:** `Σ(greek_per_leg × signed_quantity × multiplier)`

#### Breakevens
- **Método:** interpolación lineal entre puntos donde P&L cambia de signo
- **Precisión:** ±0.5 puntos (depende de resolución de 401 puntos)
- **Casos:** soporta múltiples breakevens (ej: 2 en un iron condor)

#### Probabilidad de Beneficio (Q-measure)
- **Método:** integración numérica (trapezoidales) de densidad lognormal
- **Simula:** 20,001 escenarios de precio futuro bajo `spot × exp((r-q-σ²/2)×T + σ√T×Z)`
- **Retorna:** P(payoff > 0) y expected PnL
- **Precisión:** ~±1% (error de cuadratura)

### 3. Visualización e Interfaz

#### Gráfico de Payoff
- **Matplotlib integrado** en Tkinter (FigureCanvasTkAgg)
- Línea de P&L por precio
- Línea horizontal en P&L = 0
- Línea vertical en spot actual
- Auto-redibujo en cada `CALCULAR`

#### Tabla de Escenarios
- **Columnas:** Spot, P&L absoluto, Retorno %
- **Filas:** hasta 150 puntos (downsampling de 401 con paso adaptivo)
- **Interacción:** scroll para inspeccionar P&L en spots específicos

#### Panel de Métricas (11 números)
- P&L inicial (inversión requerida)
- Delta, Gamma, Vega, Theta, Rho (agregados)
- Máximo P&L
- Mínimo P&L (pérdida máxima)
- Breakevens (formateado como "BE1, BE2, ...")
- Probabilidad de beneficio (%)
- P&L esperado (unidades de subyacente)

#### Parámetros de Mercado (inputs)
| Parámetro | Rango | Default | Significado |
|-----------|-------|---------|------------|
| Spot (S) | ℝ+ | 1000 | Precio actual del subyacente |
| IV (σ) | ℝ+ | 35% | Volatilidad implícita anualizada |
| Tasa (r) | ℝ | 5% | Tasa libre de riesgo continua |
| Dividendos (q) | ℝ | 0% | Rendimiento de dividendo continuo |
| Días | ℤ+ | 30 | Tiempo a vencimiento en días calendario |
| Multiplicador | ℝ+ | 1 | Factor de contrato (ej: 100 para índices) |

### 4. Exportación
- **Formatos:** CSV, XLSX
- **Contenido:** columnas Spot y P&L para los 401 puntos
- **Herramienta:** pandas.DataFrame + openpyxl
- **Uso:** análisis posterior en Excel, importación a otros modelos

---

## ⚠️ Limitaciones Actuales

### Que NO soporta
| Característica | Razón | Impacto |
|---|---|---|
| **IV implícita** | No resuelve BSM inverso (S → IV) | No calibra contra precios reales |
| **Opciones americanas** | Solo BSM europeo | Ignora ejercicio temprano |
| **Modelo binomial** | Solo analítico BSM | No maneja dividendos discretos bien |
| **Volatility smile** | σ constante por estrategia | Infraprecia OTM, sobreprecia ATM |
| **Dividendos discretos** | Solo yield continuo (q) | Sesgo cercano a ex-dates |
| **Multi-leg correlaciones** | Suma simple de griegos | Ignora correlación entre movimientos |
| **Leverage effect** | Spot y σ independientes | No captura "volatility smile" negativa |
| **Costo de transacción** | Asume ejecución sin fricción | P&L teórico, no real |

### Hardcodes
| Límite | Valor | Ubicación | Workaround |
|---|---|---|---|
| Máximo 6 patas | `range(6)` en app.py:30 | Crear dos estrategias, calcular por partes |
| Multiplicador universal | 1 valor para toda estrategia | Usar multiplicador global |
| 365 días/año | Línea 38 models.py | Incompatible con 252 trading days |
| Rango gráfico | 0.5x a 1.5x spot | Cambiar y recompilar en app.py:18 |
| Resolución | 401 puntos fijos | Sin zoom interactivo |

### Supuestos Matemáticos
- **Precio ~ Lognormal** → subestima tail risk (crashs extremos)
- **Vol constante** → falla si IV cambia significativamente
- **Tasa r constante** → ignora curve de rendimiento
- **Cero costo transacción** → P&L teórico vs real
- **Ejercicio en vencimiento** → ignora early exercise (americana)
- **Independencia spot-vol** → no captura correlación negativa

---

## 📊 Casos de Uso

### Trader Educativo
**Objetivo:** entender P&L de estrategias antes de tradear real
**Flujo:** Cargar plantilla → variar spot/IV → ver payoff gráfico → decidir
**Validación:** ¿se ve correctamente la estrategia? ¿breakevens tienen sentido?

### Profesor de Finanzas
**Objetivo:** enseñar opciones en clase
**Flujo:** muestra gráfico payoff en vivo → pregunta: "¿máxima pérdida?" → alumnos predicen
**Validación:** ¿gráfico coincide con manual teórico?

### Fintech Educativa
**Objetivo:** MVP calculadora (antes de app web)
**Flujo:** valida flujo usuario → parámetros → resultado → entendimiento
**Validación:** ¿UX es claro? ¿números son exactos?

**NO válido para:** trading real, desk prop, riesgo de crédito, portfolio management

---

## 🏗️ Arquitectura Actual (Pre-Refactor)

### Módulos
```
main.py (7 líneas)
  └→ entry point, crea Tk.mainloop()
  
app.py (81 líneas)
  ├─ clase OptionApp
  ├─ RESPONSABILIDADES MEZCLADAS:
  │  ├─ UI: build(), display de widgets
  │  ├─ Parseo: legs() (StringVar → Leg)
  │  ├─ Orquestación: calculate(), load_template(), export()
  │  └─ Mapeo: actualización de canvas, tabla, métricas
  └─→ imports: models.py, strategies.py, matplotlib, tkinter

models.py (95 líneas)
  ├─ Entidades: @dataclass Leg
  ├─ Lógica de dominio pura:
  │  ├─ payoff_leg(), strategy_payoff()
  │  ├─ approximate_breakevens()
  │  └─ (DEBERÍA ser: agregación de griegos)
  └─ Lógica de PRICING (NO dominio):
     ├─ bsm(), _d1d2(), greeks()
     ├─ strategy_greeks()
     └─ probability_metrics()
  └─→ imports: numpy, scipy.stats

strategies.py (16 líneas)
  └─ TEMPLATES = dict[str, list[Leg]]
  └─→ imports: models.Leg
```

### Problemas Identificados (graphify)
1. **`Leg` es el nodo más conectado (17 aristas)** — usado en app.py, tests, y funciones de pricing
2. **`OptionApp` mezcla UI + negocio** — 9 aristas, ligada a canvas, tabla, y lógica de cálculo
3. **`strategy_payoff()` es puente crítico** — conecta dominio (Leg) con UI (app.py)
4. **models.py NO es puro:** contiene pricing (scipy) + dominio + agregación
5. **Sin interfaces/puertos:** imposible swapear BSM por binomial sin tocar app.py

### Costo de Cambios Hoy
- Agregar modelo binomial → copiar-pegar `greeks()` en nueva función
- Soportar 20 patas → refactorizar `build()` y loop de 6 → N
- Soportar dividendos discretos → editar `payoff_leg()`, `bsm()`, tests
- Exportar griegos por spot → segundo loop `strategy_greeks()` en `calculate()`

---

## 🧪 Tests Actuales (Fase 0 — Characterization)

**Archivo:** `tests/unit/test_models_characterization.py` (10 tests)

### Cobertura
- ✓ BSM contra valor analítico (call + put)
- ✓ strategy_payoff (3 escenarios: OTM, ITM, deep ITM)
- ✓ strategy_greeks (delta neutral en straddle)
- ✓ approximate_breakevens (interpolación lineal)
- ✓ probability_metrics (lognormal integration)

### Red de Seguridad
Estos tests están **acoplados a models.py actual**. En Fase 1-6, se re-apuntarán a las nuevas ubicaciones pero deben pasar con **idénticos números** (±0.01%).

---

## 📋 Plan de Migración (PLAN_MIGRACION.md)

### 7 Fases Incrementales
1. **Fase 0 (✓ HECHO):** Red de seguridad (characterization tests)
2. **Fase 1:** Dominio puro (Value Objects, Entities, Agregación)
3. **Fase 2:** Puertos (Interfaces para Inversión de Dependencias)
4. **Fase 3:** Casos de uso (Orquestación con inyección)
5. **Fase 4:** Adaptadores (Pricing real, Repository, Exporter)
6. **Fase 5:** Strangler fig de UI (Presentación + Controllers)
7. **Fase 6:** Limpieza (Eliminar código legacy)

### Principios
- **Cada fase:** deja pytest en verde + `python main.py` funcional
- **Nunca roto:** siempre se puede hacer rollback
- **TDD ligero:** test antes que código en dominio/casos de uso; no en UI mecánica

---

## 🎓 Próximos Pasos

Antes de empezar Fase 1, necesitamos **clarificar expectativas**:

### Preguntas Clave para el Usuario

1. **¿Cual es el principal objetivo educativo?**
   - ¿Aprender arquitectura hexagonal? ¿Clean Code? ¿TDD? ¿Inyección de dependencias?
   - Esto orienta la velocidad y profundidad de explicaciones en cada fase.

2. **¿Quién será el usuario final después de la migración?**
   - ¿Seguirá siendo educativo (gráfico Tkinter igual)?
   - ¿Pasará a web (FastAPI + HTML/JS)?
   - ¿Será biblioteca Python pura (sin UI)?
   - Esto afecta el scope de la Fase 5 (Presentación).

3. **¿Qué nivel de cobertura de tests quieres?**
   - ¿Mínimo viable (dominio + casos de uso + integración)?
   - ¿Coverage 80% o 100%?
   - ¿Incluir tests de la UI Tkinter?

4. **¿Quieres agregar features durante la migración, o puro refactor?**
   - ¿Mantener solo las 10 estrategias actuales?
   - ¿Agregar modelo binomial en Fase 4?
   - ¿Volatility smile en Fase 4?
   - Esto añade scope significativo.

5. **¿Plazo total?**
   - ¿7 fases rápidas (1 semana)?
   - ¿Profundo (3-4 semanas con pausas pedagógicas)?
   - Condiciones la cadencia.

6. **¿Documentación y ejemplos?**
   - ¿Solo código comentado?
   - ¿README para cada fase?
   - ¿Diagramas de arquitectura?
   - ¿Video walkthrough?

---

## 📁 Estado del Repositorio

- **Git:** inicializado, commit inicial pusheado a `github.com/odinjere/Calculadora-Opciones-Python`
- **Branch:** `master`
- **Teste:** 10 tests en verde (Fase 0 ✓)
- **Estructura:** pre-refactor, listos para Fase 1

---

## 💡 Cita Final

> "El refactor no es sobre hacer el código más bonito. Es sobre hacer el código lo suficientemente claro para que alguien pueda entender qué hace, por qué lo hace, y cuál fue el diseño detrás, sin tener que preguntar." — This project's true value will be educational, not the calculator itself.

