# Migración a Clean/Hexagonal Architecture + SOLID + TDD — v2 (ACTUALIZADO)

## 🎯 Contexto Actualizado (Respuestas RDD)

### 1. Objetivo Pedagógico (CLARO)
**Entender el proceso completo:**
- Cada función: qué hace y por qué
- Flujo de datos: entrada → cálculo → salida
- Arquitectura hexagonal: por qué funciona, cuándo la necesitas
- Refactoring: cuándo, por qué, ventajas/desventajas/peligros
- **Estilo:** profundo con pausas pedagógicas, no carrera

### 2. Usuario Final (CLARO)
**Operador de valores sin conocimientos técnicos de programación**
- Conoce bases de operatoria de opciones ✓
- NO es experto en programación
- Necesita: visualización clara de curvas, interfaz intuitiva
- **Entorno:** navegador web (FastAPI backend)
- **Crítico:** la UI visual de payoff/curvas es MUY importante

### 3. Cobertura de Tests (CLARO)
- Mínima viable inicialmente (dominio + casos de uso + integración)
- **NO automatizar UI Tkinter** (es legacy de Fase 0)
- **Framework UI:** Flet (web moderna, no Tkinter)
- Tests de Flet: opcionales (mecánica, no lógica)

### 4. Features (CLARO)
- **Refactor PRIMERO**
- Features adicionales DESPUÉS (en secciones posteriores)
- **NUEVO REQUERIMIENTO CRÍTICO:** persistencia (guardar/cargar simulaciones)

### 5. Plazo (CLARO)
- Profundo con pausas pedagógicas
- No es una carrera; es educación

### 6. Documentación (CLARO)
- README por fase + diagramas de arquitectura + ejemplos concretos
- **Énfasis:** explicar el POR QUÉ de cada cambio

### 7. Stack Actualizado (NUEVO)
- **Package manager:** UV en lugar de pip (más rápido, mejor lock)
- **Backend:** FastAPI (reemplaza Tkinter UI en Fase 5)
- **Frontend:** Flet (UI multiplataforma web-first)
- **Persistencia:** TBD (ver preguntas de clarificación)

---

## ⚠️ Implicaciones Arquitectónicas del Cambio

### Cambio Mayor: Fase 5 (Presentación) se divide en 2

**ANTES (plan v1):**
- Fase 5: Refactorizar Tkinter a Humble Object

**AHORA (plan v2):**
- **Fase 5A:** Crear API REST (FastAPI) como adaptador
- **Fase 5B:** Crear frontend web (Flet) como nuevo adaptador
- Tkinter queda atrás, sin refactor

### Por qué esto es mejor:
1. **Separación clara:** backend (casos de uso) ≠ frontend (Flet)
2. **Usuario final:** accede desde navegador, sin instalar nada
3. **Escalable:** el mismo backend sirve múltiples clientes (web, móvil, etc.)
4. **Testeable:** FastAPI es trivial de testear sin UI

### Impacto en el plan:
- Fase 0-4: **sin cambios** (dominio + casos de uso + adaptadores)
- Fase 5: **nueva estructura** (API + Flet frontend)
- Fase 6: **limpieza** (remover Tkinter viejo)
- **Fase 7 (NUEVA):** Persistencia (guardar/cargar simulaciones)

---

## 🔄 Arquitectura Hexagonal — Visualización Mejorada

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENTE (NAVEGADOR)                      │
│                    Flet Web Frontend                        │
│  (gráficos, inputs, tabla — sin lógica de negocio)         │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP REST
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              ADAPTADOR DE ENTRADA: FastAPI                  │
│           (convierte HTTP → objetos de dominio)             │
└──────────────────────────┬──────────────────────────────────┘
                           │ DTOs
                           ↓
┌─────────────────────────────────────────────────────────────┐
│            CASOS DE USO (APPLICATION LAYER)                │
│  CalculateStrategy, LoadTemplate, ExportStrategy, etc.     │
│        (orquestación pura, sin conocer HTTP/DB)             │
└──────────────────────────┬──────────────────────────────────┘
                           │ interfaces
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              PUERTOS (INTERFACES INVERSAS)                  │
│  PricingPort, StrategyPort, ExporterPort, PersistencePort  │
│           (contratos, sin implementación)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │ implements
          ┌────────────────┼────────────────┬──────────────┐
          ↓                ↓                ↓              ↓
    ┌─────────┐     ┌─────────┐    ┌──────────┐    ┌───────────┐
    │  Domain │     │   BSM   │    │FileExport│    │Persistence│
    │ (Puro) │     │(SciPy)  │    │(Pandas)  │    │(SQLite)   │
    │Entities │     │         │    │          │    │           │
    │ Values  │     │         │    │          │    │           │
    └─────────┘     └─────────┘    └──────────┘    └───────────┘
```

**Flujo de datos:**
```
1. Usuario en Flet: ingresa Spot=1050, IV=35%, elige "Bull Call Spread"
                    ↓
2. Flet envía HTTP POST /calculate con CalculateRequestDTO
                    ↓
3. FastAPI router convierte HTTP → CalculateRequestDTO (dto validation)
                    ↓
4. CalculateStrategyUseCase.execute(dto) recibe
                    ↓
5. UseCase construye Strategy (dominio puro)
                    ↓
6. UseCase llama pricing_port.price_leg() → BSMPricingEngine
                    ↓
7. BSMPricingEngine (scipy) retorna Greeks por pata
                    ↓
8. UseCase agrega Greeks, calcula P&L, breakevens
                    ↓
9. UseCase retorna CalculateResponseDTO
                    ↓
10. FastAPI serializa a JSON
                    ↓
11. Flet recibe JSON, dibuja gráfico, actualiza tabla
```

---

## 📝 Fases Revisadas (v2)

### Fase 0 (✓ COMPLETA)
Red de seguridad con characterization tests.

### Fase 1 — Dominio Puro
(Sin cambios respecto a v1)
- Value Objects: OptionType, PositionSide
- Entities: Leg, Strategy
- Domain Services: breakeven_finder
- **Objetivo:** Lógica pura sin dependencias externas

### Fase 2 — Puertos (Interfaces)
(Sin cambios respecto a v1)
- PricingPort
- StrategyPort
- ExporterPort
- **NUEVA:** PersistencePort (guardar/cargar estrategias)

### Fase 3 — Casos de Uso
(Sin cambios respecto a v1, pero agrega persistencia)
- CalculateStrategyUseCase
- LoadTemplateUseCase
- ExportStrategyUseCase
- **NUEVA:** SaveSimulationUseCase
- **NUEVA:** LoadSimulationUseCase

### Fase 4 — Adaptadores Reales
(Sin cambios respecto a v1, pero agrega persistencia)
- BSMPricingEngine (SciPy)
- InMemoryStrategyRepository (templates)
- PandasFileExporter (CSV/Excel)
- **NUEVA:** SQLitePersistenceAdapter (guardar/cargar)

### Fase 5A — API REST (NUEVO)
**Objetivo:** exponer casos de uso como endpoints HTTP

**Archivos a crear:**
- `api/main.py` — aplicación FastAPI
- `api/routes/strategy.py` — endpoints /calculate, /list-templates, /export
- `api/routes/simulation.py` — endpoints /save-simulation, /load-simulation, /list-simulations
- `api/schemas/dtos.py` — Pydantic DTOs (CalculateRequestDTO, etc.)

**Endpoints:**
```
POST /api/calculate              → CalculateStrategyUseCase
GET  /api/templates              → LoadTemplateUseCase
GET  /api/templates/{name}       → LoadTemplateUseCase
POST /api/export                 → ExportStrategyUseCase
POST /api/simulations            → SaveSimulationUseCase
GET  /api/simulations            → ListSimulationsUseCase
GET  /api/simulations/{id}       → LoadSimulationUseCase
DELETE /api/simulations/{id}     → DeleteSimulationUseCase
```

**Testing:** test de integración con FastAPI TestClient

### Fase 5B — Frontend Web (NUEVO)
**Objetivo:** reemplazar Tkinter con Flet web

**Archivos a crear:**
- `ui/main.py` — aplicación Flet
- `ui/pages/calculator.py` — página principal (inputs + gráfico + tabla)
- `ui/pages/simulations.py` — página de simulaciones guardadas
- `ui/services/api_client.py` — cliente HTTP hacia FastAPI
- `ui/components/graph.py` — componente de gráfico (matplotlib + Flet)

**Características:**
- Inputs: Spot, IV, Tasa, Dividendos, Días, Multiplicador
- Selector de plantillas con botón "Cargar"
- Grid de 6 patas (CALL/PUT × COMPRA/VENTA)
- Gráfico interactivo de payoff
- Tabla de escenarios
- Botón "Guardar simulación" con nombre
- Página de "Mis simulaciones" (cargar, eliminar)

**Testing:** tests unitarios de components (sin Flet UI automation)

### Fase 6 — Limpieza
- Eliminar `app.py`, `main.py` (Tkinter legacy)
- Eliminar `strategies.py` (ahora en templates.py dentro de infrastructure)
- Actualizar imports
- Actualizar README final

### Fase 7 — Persistencia (NUEVA)
**Objetivo:** guardar y cargar simulaciones

**Casos de uso:**
- SaveSimulation: estrategia + parámetros + resultado → base de datos
- LoadSimulation: recuperar simulación guardada
- ListSimulations: listar todas las simulaciones del usuario
- DeleteSimulation: eliminar

**Modelo de datos:**
```
Simulation:
  - id (UUID)
  - timestamp (creación)
  - name (nombre dado por usuario)
  - strategy_legs (JSON)
  - market_params (JSON: spot, IV, r, q, days, mult)
  - result (JSON: payoff array, greeks, breakevens, prob_profit)
```

**Persistencia:** SQLite (simple, sin servidor)

---

## 📚 Pedagogía por Fase

### Fase 1: Entity vs Value Object
**Concepto:** Una entidad tiene identidad (un Leg es único); un VO es intercambiable (dos Leg con mismo strike son equivalentes)
**Enseñanza:** Por qué Leg es Entity (tiene comportamiento + invariantes), por qué OptionType es VO (define valores válidos)

### Fase 2: Puertos = Contratos
**Concepto:** Define lo que se necesita SIN decidir cómo se hace
**Enseñanza:** Por qué PricingPort es una interfaz, qué pasa si alguien quiere agregar modelo binomial

### Fase 3: Inversión de Dependencias (DIP)
**Concepto:** Los casos de uso NO conocen las implementaciones concretas
**Enseñanza:** Cómo se testea con fakes sin tocar la base de datos

### Fase 4: Liskov Substitution
**Concepto:** Un BSMPricingEngine puede reemplazar un BinomialPricingEngine sin romper nada
**Enseñanza:** Por qué la interfaz es lo importante, no la implementación

### Fase 5A: Separación UI-Lógica (Humble Object)
**Concepto:** FastAPI solo traduce HTTP ↔ DTOs, sin lógica de negocio
**Enseñanza:** Por qué la API es testeable (no depende de web framework), por qué es escalable

### Fase 5B: Progressive Enhancement
**Concepto:** Flet se comunica SOLO con la API, no conoce el dominio
**Enseñanza:** Ventajas de arquitectura de capas: podrías reemplazar Flet por React sin tocar backend

### Fase 7: Persistencia como Adaptador
**Concepto:** SaveSimulation es un caso de uso, SQLite es una implementación
**Enseñanza:** Cómo agregar features sin romper lo que ya funciona

---

## 🔍 Preguntas de Clarificación (IMPORTANTES)

Antes de finalizар el plan v2, necesito 4 clarificaciones críticas:

### 1. **Persistencia: ¿Cómo guardar?**
   - [ ] **JSON en archivo** (simple, sin DB)
     - Pros: sin dependencias, fácil debugging
     - Contras: sin búsqueda avanzada, sin seguridad multi-usuario
   - [ ] **SQLite** (local, sin servidor)
     - Pros: queries, índices, sin deps externas
     - Contras: un usuario por PC (si querés multi-usuario, problemático)
   - [ ] **PostgreSQL remoto** (escalable, multi-usuario)
     - Pros: múltiples usuarios, compartir estrategias
     - Contras: requiere servidor, complicación DevOps

### 2. **Autenticación: ¿Usuarios distintos?**
   - [ ] **NO** (una sola persona usa la app, sin login)
   - [ ] **SÍ** (múltiples operadores, cada uno guarda sus simulaciones)
   - Si SÍ: ¿simple username/password o integración con OAuth (Google, etc.)?

### 3. **Compartir estrategias: ¿Colaboración?**
   - [ ] **NO** (cada usuario tiene sus simulaciones privadas)
   - [ ] **SÍ** (usuarios pueden compartir estrategias con otros)
   - Si SÍ: ¿público/privado? ¿comentarios en estrategias?

### 4. **Exportación: ¿Qué formatos?**
   - [ ] CSV + Excel (como ahora)
   - [ ] CSV + Excel + PDF (con gráfico incrustado)
   - [ ] CSV + Excel + PDF + JSON (para reimportar después)

---

## 🛠️ Setup Técnico (Actualizado)

### Package Manager
```bash
# Instalar UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Crear proyecto con UV
uv init --python 3.10

# Agregar dependencias
uv add numpy scipy pandas matplotlib fastapi uvicorn flet sqlalchemy

# Dev dependencies
uv add --dev pytest pytest-cov black ruff mypy

# Correr proyecto
uv run python main.py
```

### Estructura de carpetas (actualizada)
```
calculadora-opciones/
├── domain/                 # Lógica pura (sin deps externas)
│   ├── entities/
│   ├── value_objects/
│   └── services/
├── application/            # Casos de uso + DTOs
│   ├── use_cases/
│   ├── dtos/
│   └── ports/
├── infrastructure/         # Adaptadores reales
│   ├── adapters/
│   ├── repositories/
│   └── config/
├── api/                    # FastAPI (adaptador de entrada)
│   ├── main.py
│   ├── routes/
│   └── schemas/
├── ui/                     # Flet frontend (adaptador de salida)
│   ├── main.py
│   ├── pages/
│   ├── components/
│   └── services/
├── tests/                  # Tests (mismo espejo de estructura)
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── pyproject.toml          # UV config
├── README.md              
└── PLAN_MIGRACION.md
```

---

## ✅ Checklist de Decisiones Tomadas

- [x] **Objetivo:** Entender proceso, arquitectura, refactoring (pedagógico)
- [x] **Usuario final:** Operador no-técnico, web (FastAPI + Flet)
- [x] **Tests:** Mínima viable, NO automatizar Flet UI
- [x] **Features:** Refactor primero, features después
- [x] **Plazo:** Profundo con pausas pedagógicas
- [x] **Docs:** README por fase + diagramas + ejemplos
- [x] **Stack:** UV, FastAPI, Flet, SQLite
- [x] **Persistencia:** Guardar/cargar simulaciones (nuevo requerimiento)
- [ ] **PENDIENTE:** Responder 4 preguntas de clarificación arriba ↑

---

## 🚀 Próximo Paso

**Responde estas 4 preguntas de clarificación:**
1. ¿Persistencia: JSON, SQLite, o PostgreSQL?
2. ¿Autenticación: SÍ o NO?
3. ¿Compartir estrategias: SÍ o NO?
4. ¿Exportación: qué formatos?

Con esas respuestas, el plan v2 está FINALIZADO y listo para Fase 1.

