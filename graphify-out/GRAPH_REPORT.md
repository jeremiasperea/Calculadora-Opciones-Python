# Graph Report - Calculadora_Opciones_Python  (2026-09-02)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 48 nodes · 98 edges · 9 communities (7 shown, 2 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 5 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6a3da1a8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Leg
- test_models_characterization.py
- app.py
- OptionApp
- approximate_breakevens
- TestStrategyGreeks

## God Nodes (most connected - your core abstractions)
1. `Leg` - 17 edges
2. `strategy_payoff()` - 11 edges
3. `OptionApp` - 9 edges
4. `TestStrategyPayoff` - 6 edges
5. `bsm()` - 6 edges
6. `strategy_greeks()` - 6 edges
7. `probability_metrics()` - 6 edges
8. `approximate_breakevens()` - 6 edges
9. `greeks()` - 5 edges
10. `TestStrategyPayoffWithPremium` - 4 edges

## Surprising Connections (you probably didn't know these)
- `OptionApp` --uses--> `Leg`  [INFERRED]
  app.py → models.py
- `TestProbabilityMetrics` --uses--> `Leg`  [INFERRED]
  tests/unit/test_models_characterization.py → models.py
- `TestStrategyGreeks` --uses--> `Leg`  [INFERRED]
  tests/unit/test_models_characterization.py → models.py
- `TestStrategyPayoff` --uses--> `Leg`  [INFERRED]
  tests/unit/test_models_characterization.py → models.py
- `TestStrategyPayoffWithPremium` --uses--> `Leg`  [INFERRED]
  tests/unit/test_models_characterization.py → models.py

## Import Cycles
- None detected.

## Communities (9 total, 2 thin omitted)

### Community 0 - "Leg"
Cohesion: 0.27
Nodes (7): Leg, payoff_leg(), strategy_payoff(), Test adicional: payoff incluye prima como costo Por qué: el P&L real es payoff…, Test 2: strategy_payoff sobre "Bull Call Spread" Por qué: el payoff es el…, TestStrategyPayoff, TestStrategyPayoffWithPremium

### Community 1 - "test_models_characterization.py"
Cohesion: 0.35
Nodes (7): bsm(), _d1d2(), greeks(), strategy_greeks(), Characterization tests para modelos.py Estos tests capturan el comportamiento…, Test 1: BSM contra valor analítico conocido Por qué: Black-Scholes-Merton es el…, TestBSMAnalytical

### Community 2 - "app.py"
Cohesion: 0.29
Nodes (3): probability_metrics(), Test 5: probability_metrics sobre "Long Call" Por qué: la probabilidad de…, TestProbabilityMetrics

### Community 4 - "approximate_breakevens"
Cohesion: 0.50
Nodes (3): approximate_breakevens(), Test 4: approximate_breakevens con un cruce simple Por qué: los breakevens…, TestApproximateBreakevens

## Knowledge Gaps
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Leg` connect `Leg` to `test_models_characterization.py`, `app.py`, `OptionApp`, `TestStrategyGreeks`?**
  _High betweenness centrality (0.289) - this node is a cross-community bridge._
- **Why does `OptionApp` connect `OptionApp` to `Leg`, `app.py`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **Why does `strategy_payoff()` connect `Leg` to `test_models_characterization.py`, `app.py`, `OptionApp`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Leg` (e.g. with `OptionApp` and `TestProbabilityMetrics`) actually correct?**
  _`Leg` has 5 INFERRED edges - model-reasoned connections that need verification._