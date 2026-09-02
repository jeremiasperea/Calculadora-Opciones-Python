# Arquitectura Final — Calculadora de Opciones (Plan v2 Confirmado)

## 📐 Decisiones Arquitectónicas Confirmadas

### Stack Final
- **Language:** Python 3.10+
- **Backend:** FastAPI (HTTP REST)
- **Frontend:** Flet (web moderna, navegador)
- **Persistencia:** SQLite (local, sin servidor)
- **Package Manager:** UV (más rápido que pip)
- **Build:** Dominio puro → Casos de uso → Adaptadores (Hexagonal)

### Modelo de Usuarios
- **Autenticación:** NO (aplicación local, un operador)
- **Persistencia:** SQLite local (una base de datos por máquina)
- **Compartir estrategias:** NO (MVP) — exportar por CSV/Excel/JSON si necesita compartir
- **Escalabilidad:** Diseñar para que sea trivial agregar autenticación después (TDD: test → code)

### Exportación
- **Formatos:** CSV, Excel (.xlsx), PDF (con gráfico), JSON (para reimportar)
- **Caso de uso:** Operador exporta → comparte; operador recibe JSON → reimporta con 1 click

---

## 🏗️ Arquitectura Hexagonal (Visualización Final)

```
┌────────────────────────────────────────────────────────────────┐
│                  NAVEGADOR (Usuario Final)                     │
│                     Flet Web App                               │
│  Inputs → Gráfico Payoff → Tabla Escenarios → Botones         │
└─────────────────────────────┬────────────────────────────────┘
                              │ HTTP JSON
                              ↓
┌────────────────────────────────────────────────────────────────┐
│              PUERTO DE ENTRADA: FastAPI (main.py)              │
│                                                                │
│  POST   /api/calculate        → request validation            │
│  GET    /api/templates        → list all                      │
│  GET    /api/templates/{id}   → fetch one                     │
│  POST   /api/export           → formato (csv/excel/pdf/json)  │
│  POST   /api/simulations      → save simulation               │
│  GET    /api/simulations      → list all                      │
│  GET    /api/simulations/{id} → fetch one                     │
│  DELETE /api/simulations/{id} → delete                        │
│                                                                │
│  Responsabilidad: HTTP ↔ DTO, nada más                       │
└─────────────────────────────┬────────────────────────────────┘
                              │ DTOs
                              ↓
┌────────────────────────────────────────────────────────────────┐
│          CAPA DE APLICACIÓN: Casos de Uso (use_cases/)        │
│                                                                │
│  • CalculateStrategyUseCase                                   │
│    Input: Strategy + Market params                            │
│    Output: Payoff array, Greeks, Breakevens, Prob profit      │
│                                                                │
│  • LoadTemplateUseCase                                        │
│    Input: Template name                                       │
│    Output: List of Legs                                       │
│                                                                │
│  • ExportStrategyUseCase                                      │
│    Input: Payoff data + format (csv/excel/pdf/json)           │
│    Output: Bytes (PDF) or text (CSV/JSON)                     │
│                                                                │
│  • SaveSimulationUseCase                                      │
│    Input: Strategy + Market params + Result                   │
│    Output: Simulation ID                                      │
│                                                                │
│  • LoadSimulationUseCase                                      │
│    Input: Simulation ID                                       │
│    Output: Complete Simulation object                         │
│                                                                │
│  Responsabilidad: Orquestación pura, NINGUNA dependencia      │
│  externa (no dependen de FastAPI, SQLite, SciPy)              │
└─────────────────────────────┬────────────────────────────────┘
                              │ depends on abstractions
                              ↓
┌────────────────────────────────────────────────────────────────┐
│              PUERTOS: Interfaces Inversas (ports/)             │
│                                                                │
│  PricingPort:                                                 │
│    def price_leg(spot, leg, days, sigma, r, q) -> Greeks     │
│                                                                │
│  StrategyPort:                                                │
│    def get_template(name: str) -> list[Leg]                  │
│    def list_template_names() -> list[str]                    │
│                                                                │
│  ExporterPort:                                                │
│    def export(prices, pnl, format: str) -> bytes or str      │
│                                                                │
│  PersistencePort:  [NUEVA]                                    │
│    def save_simulation(sim: Simulation) -> str (id)           │
│    def load_simulation(id: str) -> Simulation                 │
│    def list_simulations() -> list[Simulation]                 │
│    def delete_simulation(id: str) -> bool                     │
│                                                                │
│  Responsabilidad: Solo contratos, sin implementación          │
└─────────────────────────────┬────────────────────────────────┘
                              │ implemented by
          ┌───────────────────┼───────────────────────────────┐
          ↓                   ↓                               ↓
    ┌──────────────┐    ┌──────────────┐            ┌─────────────┐
    │  DOMINIO     │    │ ADAPTADORES  │            │   DATOS     │
    │              │    │  (infra/)    │            │              │
    │ • Entities   │    │              │            │              │
    │   - Leg      │    │ • BSMPricing │────────→  │  SciPy      │
    │   - Strategy │    │   Engine     │            │  NumPy      │
    │   - Greeks   │    │              │            │  SciPy      │
    │   - Sim      │    │ • FileExport │────────→  │  Pandas     │
    │              │    │   er (Pandas)│            │  reportlab  │
    │ • Value Objs │    │              │            │              │
    │   - OptionTp │    │ • SQLitePers │────────→  │  SQLite     │
    │   - PosSnde  │    │   istence    │            │  SQLAlchemy │
    │              │    │              │            │              │
    │ • Domain Svc │    │ • StrategyRep│────────→  │  templates. │
    │   - Breakev  │    │   o (In-Mem) │            │  py (JSON)  │
    │   - ProbCalc │    │              │            │              │
    └──────────────┘    └──────────────┘            └─────────────┘
```

---

## 🔄 Flujo de Datos End-to-End

### Caso 1: Calcular Payoff de una Estrategia

```
1. Usuario abre Flet en navegador (http://localhost:8000)
                ↓
2. Usuario ingresa: Spot=1050, IV=35%, elige "Bull Call Spread"
                ↓
3. Flet envia: POST /api/calculate
   {
     "spot": 1050,
     "iv": 0.35,
     "rate": 0.05,
     "dividend": 0,
     "days": 30,
     "mult": 1,
     "legs": [
       {"type": "CALL", "side": "COMPRA", "qty": 1, "strike": 1000, "premium": 40},
       {"type": "CALL", "side": "VENTA", "qty": 1, "strike": 1100, "premium": 15}
     ]
   }
                ↓
4. FastAPI recibe (main.py:routes/strategy.py)
   - Valida JSON con Pydantic DTO ✓
   - Extrae: CalculateRequestDTO
                ↓
5. FastAPI llama: CalculateStrategyUseCase.execute(dto)
                ↓
6. UseCase (application/use_cases/calculate_strategy.py):
   a) Construye: Strategy(legs=[Leg(...), Leg(...)]) [DOMINIO PURO]
   b) Crea: prices = np.linspace(525, 1575, 401)
   c) Calcula payoff: strategy.payoff(prices) [DOMINIO]
   d) Por cada leg, llama: pricing_port.price_leg(spot=1050, leg, ...)
                ↓
7. PricingPort implementado por: BSMPricingEngine (infrastructure/adapters/bsm_pricing.py)
   - Llama: bsm(S=1050, K=1000, T=30/365, σ=0.35, r=0.05, q=0)
   - scipy.stats.norm.cdf(d1), norm.pdf(d2)
   - Retorna: Greeks(value=..., delta=..., gamma=..., vega=..., theta=..., rho=...)
                ↓
8. UseCase agrega griegos: Greeks.aggregate([greek_leg1, greek_leg2])
                ↓
9. UseCase calcula: breakevens = approximate_breakevens(prices, pnl)
                ↓
10. UseCase calcula: prob_metrics = probability_metrics(spot=1050, ...)
                ↓
11. UseCase retorna: CalculateResponseDTO
    {
      "payoff": [array of 401],
      "prices": [array of 401],
      "greeks": {"delta": 0.45, "gamma": 0.002, ...},
      "max_pnl": 100.0,
      "min_pnl": -40.0,
      "breakevens": [1025.3, 1074.7],
      "prob_profit": 0.52,
      "expected_pnl": 5.23
    }
                ↓
12. FastAPI serializa a JSON, retorna 200 OK
                ↓
13. Flet recibe JSON, dibuja:
    - Gráfico: payoff line
    - Tabla: spot → P&L → retorno %
    - Métricas: delta=0.45, gamma=0.002, etc.
```

### Caso 2: Guardar Simulación

```
1. Usuario click "Guardar simulación"
   Input: nombre="My Bull Call Sep"
                ↓
2. Flet envia: POST /api/simulations
   {
     "name": "My Bull Call Sep",
     "strategy_legs": [...],
     "market_params": {...},
     "result": {...}  ← del último /calculate
   }
                ↓
3. FastAPI recibe, valida, llama: SaveSimulationUseCase.execute(dto)
                ↓
4. UseCase crea: Simulation(id=uuid(), name=..., ...)
                ↓
5. UseCase llama: persistence_port.save_simulation(sim)
                ↓
6. Implementación: SQLitePersistenceAdapter (infrastructure/adapters/sqlite.py)
   - INSERT INTO simulations (id, name, strategy_legs, market_params, result, created_at)
   - Retorna: sim.id
                ↓
7. FastAPI retorna: {"id": "abc-123-def", "message": "Guardado"}
                ↓
8. Flet muestra: "✓ Simulación guardada"
```

### Caso 3: Cargar Simulación

```
1. Usuario click tab "Mis Simulaciones"
                ↓
2. Flet envia: GET /api/simulations
                ↓
3. FastAPI llama: ListSimulationsUseCase.execute()
                ↓
4. UseCase llama: persistence_port.list_simulations()
                ↓
5. SQLitePersistenceAdapter: SELECT * FROM simulations
                ↓
6. Retorna list[SimulationSummary]
                ↓
7. Flet muestra tabla con: nombre, fecha, botones [Cargar] [Eliminar]
                ↓
8. Usuario click [Cargar]
                ↓
9. Flet envia: GET /api/simulations/{id}
                ↓
10. UseCase llama: persistence_port.load_simulation(id)
                ↓
11. SQLitePersistenceAdapter: SELECT * FROM simulations WHERE id=...
                ↓
12. Retorna: Simulation completo (legs, params, result)
                ↓
13. Flet recibe, redibuja gráfico y tabla con esa estrategia
```

---

## 📊 Modelo de Base de Datos (SQLite)

```sql
CREATE TABLE simulations (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  strategy_legs JSON NOT NULL,     -- [{"type":"CALL","side":"COMPRA","qty":1,"strike":1000,"premium":40}, ...]
  market_params JSON NOT NULL,     -- {"spot":1050,"iv":0.35,"rate":0.05,"dividend":0,"days":30,"mult":1}
  result JSON NOT NULL             -- {"payoff":[...],"greeks":{...},"breakevens":[...]}
);
```

**Ejemplo de fila:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Bull Call Spread - Sept",
  "created_at": "2026-09-02 14:30:45",
  "strategy_legs": [
    {"type": "CALL", "side": "COMPRA", "qty": 1, "strike": 1000, "premium": 40},
    {"type": "CALL", "side": "VENTA", "qty": 1, "strike": 1100, "premium": 15}
  ],
  "market_params": {
    "spot": 1050,
    "iv": 0.35,
    "rate": 0.05,
    "dividend": 0,
    "days": 30,
    "mult": 1
  },
  "result": {
    "payoff": [array of 401 values],
    "prices": [array of 401 values],
    "greeks": {"delta": 0.45, "gamma": 0.002, "vega": 3.2, "theta": -0.05, "rho": 2.1},
    "max_pnl": 100.0,
    "min_pnl": -40.0,
    "breakevens": [1025.3, 1074.7],
    "prob_profit": 0.52,
    "expected_pnl": 5.23
  }
}
```

---

## 🧪 Testing Strategy

### Fase 0: Characterization (✓ HECHO)
- 10 tests contra models.py actual

### Fase 1-4: Domain + UseCase + Adapter Tests
- **Domain tests:** Entity/VO behavior, no mocks (puro)
- **UseCase tests:** con fakes (FakePricingEngine, FakePersistence)
- **Adapter tests:** con datos reales (SciPy, SQLite con :memory:)

### Fase 5A: API Tests
- FastAPI TestClient
- Mock casos de uso para tests de routing
- Tests de validación Pydantic DTO

### Fase 5B: Flet Component Tests
- Tests unitarios de componentes (sin Flet UI automation)
- Mock API client

### Coverage Objetivo
- Dominio: 100% (lógica es crítica)
- Casos de uso: 90%+ (orquestación)
- Adaptadores: 70%+ (implementación concreta)
- API: 80%+ (routing + validation)
- Flet: 0% formal (QA manual, no automatización)

---

## 📚 Pedagogía Cristalizada

Cada fase enseña UN concepto clave:

| Fase | Concepto | Pregunta Central |
|------|----------|-----------------|
| 1 | Entity vs Value Object | ¿Por qué Leg es Entity y OptionType es VO? |
| 2 | Puertos = Contratos | ¿Qué pasa si quiero binomial en lugar de BSM? |
| 3 | Inversión de Dependencias | ¿Por qué los casos de uso NO conocen SciPy? |
| 4 | Liskov Substitution | ¿Por qué BSMPricingEngine reemplaza PricingPort? |
| 5A | Separación UI-Lógica | ¿Por qué FastAPI no tiene lógica de negocio? |
| 5B | Progressive Enhancement | ¿Por qué puedo reemplazar Flet por React sin tocar backend? |
| 6 | Limpieza Incremental | ¿Cómo elimino Tkinter sin romper nada? |
| 7 | Adaptador de Persistencia | ¿Por qué SaveSimulation es UseCase, SQLite es Adapter? |

---

## ✅ Checklist Final

- [x] Stack decidido: FastAPI + Flet + SQLite + UV
- [x] Persistencia decidida: SQLite local
- [x] Autenticación: NO (app local)
- [x] Compartir: NO (MVP)
- [x] Exportación: CSV + Excel + PDF + JSON
- [x] Arquitectura hexagonal: clarificada con flujo completo
- [x] Modelo de base de datos: definido
- [x] Testing strategy: definida
- [x] Pedagogía: cristalizada por fase

**Estado:** LISTA PARA FASE 1 ✅

