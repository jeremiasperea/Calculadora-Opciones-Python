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
from strategies import TEMPLATES


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
        # Spot < 1000: ambas opciones expiran fuera del dinero
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
        # GOLDEN MASTER: valores exactos del codigo actual.
        # Un assert de rango (0 <= prob <= 1) no sirve como red de seguridad:
        # seguiria pasando aunque la migracion cambiara el resultado por completo.
        assert pm["prob_profit"] == pytest.approx(0.21880040547071175, rel=1e-9)
        assert pm["expected_pnl"] == pytest.approx(-7.84051731744115, rel=1e-9)

        # Sanidad economica: un call OTM (strike 1050 sobre spot 1000) a 30 dias
        # expira sin valor la mayoria de las veces, asi que el P&L esperado bajo
        # la medida de riesgo neutral es negativo por el costo de la prima.
        assert pm["prob_profit"] < 0.5
        assert pm["expected_pnl"] < 0


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


class TestPipelineCompletoGoldenMaster:
    """Test 6: EL TEST MAS IMPORTANTE DE LA FASE 0.

    Por que: los tests anteriores prueban funciones AISLADAS. Este prueba la
    CADENA COMPLETA, replicando exactamente lo que hace app.calculate():

        prices -> payoff -> greeks -> initial -> breakevens -> probabilidades

    En las fases 3-5 esa orquestacion se muda de app.calculate() a un caso de
    uso. Podes tener las 5 funciones correctas y el pipeline roto (un signo
    invertido al agregar, un multiplicador aplicado dos veces, un orden de
    argumentos cambiado). Solo un test end-to-end detecta eso.

    Estrategia: Iron Condor (4 patas, la mas compleja del set) con los
    parametros por defecto de la app.

    Los valores no son magicos - se verifican a mano:
      credito neto  = -10 +20 +20 -10           = +20
      perdida max   = ancho del spread - credito = 50 - 20 = 30
      breakeven inf = strike put vendido - credito = 950 - 20 = 930
      breakeven sup = strike call vendido + credito = 1050 + 20 = 1070
    """

    def _pipeline(self):
        """Replica exacta de app.calculate() (app.py:61-68)."""
        S, iv, r, q, days, mult = 1000.0, 0.35, 0.05, 0.0, 30.0, 1.0
        legs = TEMPLATES["Iron Condor"]

        prices = np.linspace(S * 0.5, S * 1.5, 401)
        pnl = strategy_payoff(prices, legs, mult)
        g = strategy_greeks(S, days, iv, r, q, legs, mult)
        initial = sum(
            (-1 if x.side == "COMPRA" else 1) * x.quantity * x.premium * mult
            for x in legs
        )
        be = approximate_breakevens(prices, pnl)
        pm = probability_metrics(S, days, iv, r, q, legs, mult)
        return prices, pnl, g, initial, be, pm

    def test_iron_condor_pnl_estructura(self):
        _, pnl, _, initial, _, _ = self._pipeline()
        assert initial == pytest.approx(20.0)       # credito neto recibido
        assert pnl.max() == pytest.approx(20.0)     # ganancia max = el credito
        assert pnl.min() == pytest.approx(-30.0)    # perdida max = 50 - 20
        # Las alas: perdida maxima en ambos extremos, ganancia maxima en el centro
        assert pnl[0] == pytest.approx(-30.0)
        assert pnl[200] == pytest.approx(20.0)
        assert pnl[-1] == pytest.approx(-30.0)

    def test_iron_condor_breakevens(self):
        _, _, _, _, be, _ = self._pipeline()
        assert len(be) == 2
        assert be[0] == pytest.approx(930.0, abs=0.01)
        assert be[1] == pytest.approx(1070.0, abs=0.01)

    def test_iron_condor_greeks(self):
        _, _, g, _, _, _ = self._pipeline()
        # Valores exactos (golden master)
        assert g["delta"] == pytest.approx(-0.004556719861883218, rel=1e-9)
        assert g["gamma"] == pytest.approx(-0.002170497346895761, rel=1e-9)
        assert g["vega"] == pytest.approx(-0.6243896477371369, rel=1e-9)
        assert g["theta"] == pytest.approx(0.3617228600607449, rel=1e-9)
        assert g["rho"] == pytest.approx(0.015026606715508983, rel=1e-9)

        # Sanidad economica: un iron condor es una posicion corta en volatilidad
        assert abs(g["delta"]) < 0.05    # direccionalmente neutral
        assert g["gamma"] < 0            # pierde si el subyacente se mueve
        assert g["vega"] < 0             # pierde si sube la volatilidad
        assert g["theta"] > 0            # gana con el paso del tiempo

    def test_iron_condor_probabilidades(self):
        _, _, _, _, _, pm = self._pipeline()
        assert pm["prob_profit"] == pytest.approx(0.515239261105258, rel=1e-9)
        assert pm["expected_pnl"] == pytest.approx(-2.9331256909927075, rel=1e-9)


class TestMultiplicador:
    """Test 7: el multiplicador se aplica UNA SOLA VEZ.

    Por que existe este test: fue descubierto con una prueba de mutacion.
    Se introdujo a proposito el bug `payoff * multiplier * multiplier` y
    NINGUNO de los otros 14 tests fallo, porque todos usaban multiplier=1
    (y 1*1 = 1, el bug es invisible).

    Ese bug es exactamente el que se cuela en una migracion a capas: el
    multiplicador se aplica en la entidad Strategy Y otra vez en el caso de
    uso. Con multiplier=100 (contratos de indice) el P&L sale 100 veces mas
    grande y el operador toma una decision con un numero absurdo.

    Regla general: si un parametro tiene un valor neutro (1 para multiplicar,
    0 para sumar), NUNCA lo testees solo con ese valor.
    """

    def test_multiplicador_escala_linealmente(self):
        legs = [Leg("CALL", "COMPRA", 1, 1000, 40)]
        spots = np.array([1100.0])

        base = strategy_payoff(spots, legs, multiplier=1.0)[0]
        x100 = strategy_payoff(spots, legs, multiplier=100.0)[0]

        # intrinsic 100 - prima 40 = 60 por unidad
        assert base == pytest.approx(60.0)
        # Escala LINEAL, no cuadratica: 60 * 100 = 6000 (no 600000)
        assert x100 == pytest.approx(6000.0)
        assert x100 == pytest.approx(base * 100.0)

    def test_multiplicador_escala_greeks_linealmente(self):
        legs = [Leg("CALL", "COMPRA", 1, 1000, 40)]
        g1 = strategy_greeks(1000, 30, 0.35, 0.05, 0, legs, multiplier=1)
        g100 = strategy_greeks(1000, 30, 0.35, 0.05, 0, legs, multiplier=100)

        for greek in ("delta", "gamma", "vega", "theta", "rho"):
            assert g100[greek] == pytest.approx(g1[greek] * 100.0, rel=1e-9), greek
