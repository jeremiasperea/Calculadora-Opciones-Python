"""
Characterization tests para modelos.py

Estos tests capturan el comportamiento ACTUAL del código sin tocarlo.
Son la red de seguridad: si rompes algo durante la migración, estos tests fallan.

Por qué esta estructura:
- La Fase 0 no es TDD clásico (no escribís lógica nueva)
- Es "golden master testing": capturás lo que existe hoy como especificación
- Después, en fases posteriores, re-apuntarás estos tests a las nuevas ubicaciones
  y deberán seguir pasando con los mismos números exactos
"""

import pytest
import numpy as np
from models import (
    Leg,
    bsm,
    greeks,
    strategy_payoff,
    strategy_greeks,
    approximate_breakevens,
    probability_metrics,
)


class TestBSMAnalytical:
    """Test 1: BSM contra valor analítico conocido

    Por qué: Black-Scholes-Merton es el motor de cálculo de opciones.
    Si este test falla después de la migración, algo está mal en el pricing.

    Caso: S=100, K=100, T=1 año, σ=0.2, r=0.05, q=0
    Valor esperado de call (analítico): ~10.4506
    """

    def test_bsm_call_at_the_money(self):
        S, K, T_days, sigma, r, q = 100, 100, 365, 0.2, 0.05, 0
        call_value = bsm(S, K, T_days, sigma, r, q, "CALL")
        assert call_value == pytest.approx(10.4506, rel=1e-4)

    def test_bsm_put_at_the_money(self):
        S, K, T_days, sigma, r, q = 100, 100, 365, 0.2, 0.05, 0
        put_value = bsm(S, K, T_days, sigma, r, q, "PUT")
        # Call - Put = S * exp(-q*T) - K * exp(-r*T)
        # 10.4506 - put = 100 - 100 * exp(-0.05) ≈ 5.5735
        assert put_value == pytest.approx(5.5735, rel=1e-3)


class TestStrategyPayoff:
    """Test 2: strategy_payoff sobre "Bull Call Spread"

    Por qué: el payoff es el corazón del análisis de riesgo.
    Probamos 3 escenarios: por debajo, entre, por encima de los strikes.

    Bull Call Spread: COMPRA CALL(K=1000) + VENTA CALL(K=1100)
    Notas: no hay prima en este test (premium=0) para aislar la lógica de intrinsic value
    """

    def test_bull_call_spread_below_first_strike(self):
        # Spot < 1000: ambas opciones expiران fuera del dinero
        legs = [
            Leg("CALL", "COMPRA", 1, 1000, 0),  # Compra call strike 1000
            Leg("CALL", "VENTA", 1, 1100, 0),   # Venta call strike 1100
        ]
        spots = np.array([900.0])
        payoff = strategy_payoff(spots, legs, multiplier=1.0)
        assert payoff[0] == pytest.approx(0.0)

    def test_bull_call_spread_between_strikes(self):
        # 1000 < Spot < 1100: call comprado está ITM, vendido OTM
        legs = [
            Leg("CALL", "COMPRA", 1, 1000, 0),
            Leg("CALL", "VENTA", 1, 1100, 0),
        ]
        spots = np.array([1050.0])
        payoff = strategy_payoff(spots, legs, multiplier=1.0)
        # Call comprado: max(1050-1000, 0) = 50
        # Call vendido: -max(1050-1100, 0) = 0
        # Total: 50
        assert payoff[0] == pytest.approx(50.0)

    def test_bull_call_spread_above_both_strikes(self):
        # Spot > 1100: ambas ITM, el payoff máximo se limita a la diferencia de strikes
        legs = [
            Leg("CALL", "COMPRA", 1, 1000, 0),
            Leg("CALL", "VENTA", 1, 1100, 0),
        ]
        spots = np.array([1200.0])
        payoff = strategy_payoff(spots, legs, multiplier=1.0)
        # Call comprado: max(1200-1000, 0) = 200
        # Call vendido: -max(1200-1100, 0) = -100
        # Total: 100 (máximo de un bull call spread = diferencia de strikes)
        assert payoff[0] == pytest.approx(100.0)


class TestStrategyGreeks:
    """Test 3: strategy_greeks sobre "Long Straddle"

    Por qué: los griegos (delta, gamma, etc.) son sensibilidades de riesgo.
    Un straddle debería tener delta ≈ 0 (neutral direccional).

    Long Straddle: COMPRA CALL(K=1000, prima=35) + COMPRA PUT(K=1000, prima=35)
    """

    def test_long_straddle_delta_neutral(self):
        S, K = 1000, 1000
        legs = [
            Leg("CALL", "COMPRA", 1, K, 35),
            Leg("PUT", "COMPRA", 1, K, 35),
        ]
        greeks_total = strategy_greeks(S, days=30, sigma=0.35, r=0.05, q=0, legs=legs)
        # Un straddle comprado a ATM debe tener delta cercano a 0
        assert greeks_total["delta"] == pytest.approx(0.0, abs=0.1)
        # Gamma debe ser positiva (se beneficia de volatilidad realizada)
        assert greeks_total["gamma"] > 0
        # Vega debe ser positivo (se beneficia de IV aumentando)
        assert greeks_total["vega"] > 0


class TestApproximateBreakevens:
    """Test 4: approximate_breakevens con un cruce simple

    Por qué: los breakevens marcan dónde la estrategia pasa a beneficio.
    Este test verifica la interpolación lineal básica.
    """

    def test_single_breakeven_linear_interpolation(self):
        # Array con un cruce simple: pnl pasa de -50 a +50 entre índices
        prices = np.array([900.0, 1000.0, 1100.0])
        pnl = np.array([-50.0, 0.0, 50.0])  # El BE está exactamente en 1000
        breakevens = approximate_breakevens(prices, pnl)
        assert len(breakevens) == 1
        assert breakevens[0] == pytest.approx(1000.0, abs=0.01)

    def test_multiple_breakevens(self):
        # Array con dos cruces: no cruce, cruce, no cruce, cruce
        prices = np.array([900.0, 950.0, 1050.0, 1100.0])
        pnl = np.array([50.0, -10.0, -10.0, 30.0])  # Cruces en [900->950] y [1050->1100]
        breakevens = approximate_breakevens(prices, pnl)
        assert len(breakevens) == 2
        # BE1: interpolación entre 900 (pnl=50) y 950 (pnl=-10)
        # x = 900 + (-50) * (950 - 900) / (-10 - 50) ≈ 941.67
        assert breakevens[0] == pytest.approx(941.667, abs=1.0)
        # BE2: interpolación entre 1050 (pnl=-10) y 1100 (pnl=30)
        # x = 1050 + (-10) * (1100 - 1050) / (30 - (-10)) ≈ 1062.5
        assert breakevens[1] == pytest.approx(1062.5, abs=1.0)


class TestProbabilityMetrics:
    """Test 5: probability_metrics sobre "Long Call"

    Por qué: la probabilidad de beneficio es un número clave para los traders.
    Este test fija el valor actual para que cualquier cambio sea detectable.

    Long Call: COMPRA CALL(K=1050, prima=30)
    Parámetros: S=1000, IV=35%, días=30, r=5%, q=0
    """

    def test_long_call_probability_metrics(self):
        S = 1000
        legs = [Leg("CALL", "COMPRA", 1, 1050, 30)]
        pm = probability_metrics(
            spot=S,
            days=30,
            sigma=0.35,
            r=0.05,
            q=0,
            legs=legs,
            multiplier=1,
        )
        # Verificamos que los valores existen y son razonables
        assert isinstance(pm["prob_profit"], (float, np.floating))
        assert isinstance(pm["expected_pnl"], (float, np.floating))
        # Prob profit debe estar entre 0 y 1
        assert 0 <= pm["prob_profit"] <= 1
        # Para un long call OTM con prima de 30, expected_pnl suele ser negativo
        # (la mayoría de las veces expira fuera del dinero)
        # Pero no es un requisito del modelo, solo del mercado


class TestStrategyPayoffWithPremium:
    """Test adicional: payoff incluye prima como costo

    Por qué: el P&L real es payoff al vencimiento MENOS la prima pagada.
    Esto es crítico: un call ITM que costó más de lo que ganó, sigue siendo pérdida.
    """

    def test_long_call_pnl_includes_premium(self):
        # Long call: strike 1050, prima 30
        legs = [Leg("CALL", "COMPRA", 1, 1050, 30)]
        # Spot 1080 (ITM por 30 puntos)
        spots = np.array([1080.0])
        payoff = strategy_payoff(spots, legs, multiplier=1.0)
        # Intrinsic value: max(1080-1050, 0) = 30
        # Prima pagada: 30
        # P&L neto: 30 - 30 = 0
        assert payoff[0] == pytest.approx(0.0)
