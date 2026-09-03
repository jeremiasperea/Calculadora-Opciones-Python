"""Tests de Greeks: las sensibilidades de una posicion, y como se combinan.

Aca esta la separacion mas importante del proyecto. models.py tiene dos cosas
distintas mezcladas en strategy_greeks():

  1. COMO se calcula el delta de una pata  -> depende de Black-Scholes,
     usa scipy, es reemplazable por un arbol binomial -> INFRAESTRUCTURA

  2. COMO se combinan las patas            -> multiplicar cada griego por la
     cantidad con signo y sumar. Vale igual con BSM, binomial o Monte Carlo
     -> DOMINIO

Este archivo prueba (2). El (1) llega en la Fase 4 como adaptador.

Los numeros de estos tests son inventados a proposito — delta=0.5, gamma=0.1.
No son valores de Black-Scholes de nada. Si los tests de agregacion usaran
valores BSM reales, quedarian atados al modelo de pricing y dejarian de probar
lo unico que les toca: que la suma este bien hecha.
"""

import pytest

from domain.entities.greeks import Greeks
from domain.entities.leg import Leg
from domain.entities.strategy import Strategy


class TestGreeksComoValueObject:
    def test_arranca_en_cero(self):
        cero = Greeks.zero()
        assert cero.delta == 0 and cero.gamma == 0 and cero.vega == 0
        assert cero.theta == 0 and cero.rho == 0 and cero.value == 0

    def test_es_inmutable(self):
        g = Greeks(value=10, delta=0.5)
        with pytest.raises(Exception):
            g.delta = 0.9

    def test_igualdad_por_valor(self):
        assert Greeks(delta=0.5) == Greeks(delta=0.5)


class TestAlgebra:
    """Los griegos se comportan como vectores: se escalan y se suman.

    Darles esas dos operaciones deja que la agregacion se escriba como lo que
    es matematicamente, en vez de un doble loop sobre nombres de campos.
    """

    def test_escalar_multiplica_todos_los_campos(self):
        """Se compara campo a campo con approx, no con ==.

        Escrito como `x3 == Greeks(gamma=0.3, ...)` este test falla, porque
        0.1 * 3 da 0.30000000000000004 en punto flotante. No es un error del
        codigo: es que la igualdad exacta entre floats casi nunca es lo que
        uno quiere afirmar.
        """
        g = Greeks(value=10, delta=0.5, gamma=0.1, vega=2, theta=-0.3, rho=1)
        x3 = g.scaled_by(3)
        assert x3.value == pytest.approx(30)
        assert x3.delta == pytest.approx(1.5)
        assert x3.gamma == pytest.approx(0.3)
        assert x3.vega == pytest.approx(6)
        assert x3.theta == pytest.approx(-0.9)
        assert x3.rho == pytest.approx(3)

    def test_escalar_por_negativo_invierte_los_signos(self):
        """Es lo que convierte una compra en una venta."""
        comprado = Greeks(delta=0.5, gamma=0.1, vega=2)
        vendido = comprado.scaled_by(-1)
        assert vendido.delta == -0.5
        assert vendido.gamma == -0.1
        assert vendido.vega == -2

    def test_sumar_suma_campo_a_campo(self):
        a = Greeks(value=10, delta=0.5, gamma=0.1)
        b = Greeks(value=5, delta=0.2, gamma=0.3)
        suma = a + b
        assert suma.value == pytest.approx(15)
        assert suma.delta == pytest.approx(0.7)
        assert suma.gamma == pytest.approx(0.4)

    def test_sumar_cero_no_cambia_nada(self):
        g = Greeks(value=10, delta=0.5, gamma=0.1, vega=2, theta=-0.3, rho=1)
        assert g + Greeks.zero() == g


class TestAgregacionEnStrategy:
    """Strategy pesa cada pata: es quien conoce cantidades y multiplicador."""

    def test_una_compra_conserva_el_signo(self):
        s = Strategy([Leg("CALL", "COMPRA", 1, 1000, 40)])
        total = s.aggregate_greeks([Greeks(delta=0.5, gamma=0.1)])
        assert total.delta == pytest.approx(0.5)

    def test_una_venta_invierte_el_signo(self):
        s = Strategy([Leg("CALL", "VENTA", 1, 1000, 40)])
        total = s.aggregate_greeks([Greeks(delta=0.5, gamma=0.1)])
        assert total.delta == pytest.approx(-0.5)
        assert total.gamma == pytest.approx(-0.1)

    def test_la_cantidad_escala(self):
        s = Strategy([Leg("CALL", "COMPRA", 3, 1000, 40)])
        total = s.aggregate_greeks([Greeks(delta=0.5)])
        assert total.delta == pytest.approx(1.5)

    def test_el_multiplicador_escala(self):
        s = Strategy([Leg("CALL", "COMPRA", 1, 1000, 40)], multiplier=100)
        total = s.aggregate_greeks([Greeks(delta=0.5)])
        assert total.delta == pytest.approx(50.0)

    def test_un_spread_resta(self):
        """Comprar una y vender otra: los deltas se cancelan parcialmente."""
        s = Strategy([
            Leg("CALL", "COMPRA", 1, 1000, 40),
            Leg("CALL", "VENTA", 1, 1100, 15),
        ])
        total = s.aggregate_greeks([Greeks(delta=0.6), Greeks(delta=0.3)])
        assert total.delta == pytest.approx(0.3)

    def test_exige_un_griego_por_pata(self):
        """Si las listas no coinciden, alguna pata quedaria sin contar.

        Fallar es mejor que devolver un total incompleto que parece correcto.
        """
        s = Strategy([
            Leg("CALL", "COMPRA", 1, 1000, 40),
            Leg("CALL", "VENTA", 1, 1100, 15),
        ])
        with pytest.raises(ValueError, match="pata"):
            s.aggregate_greeks([Greeks(delta=0.6)])


class TestContraLosValoresDeReferencia:
    """La agregacion produce los griegos que producia el codigo original.

    Se alimenta con los griegos por pata que calcula el adaptador real y se
    verifica el total. Es el unico test de este archivo que usa valores de
    Black-Scholes de verdad; los demas usan numeros inventados a proposito,
    para no atar la prueba de la suma al modelo de valuacion.
    """

    def test_iron_condor_griegos_agregados(self, golden):
        from domain.value_objects.market_conditions import MarketConditions
        from infrastructure.adapters.bsm_pricing import BSMPricingEngine

        caso = golden["plantillas"]["Iron Condor|x1"]
        params = golden["parametros"]

        estrategia = Strategy([
            Leg(p["option_type"], p["side"], p["quantity"], p["strike"], p["premium"])
            for p in caso["patas"]
        ])
        mercado = MarketConditions(
            spot=params["spot"], days_to_expiry=params["days_to_expiry"],
            volatility=params["volatility"], rate=params["rate"],
            dividend_yield=params["dividend_yield"],
        )

        motor = BSMPricingEngine()
        total = estrategia.aggregate_greeks(
            [motor.price_leg(leg, mercado) for leg in estrategia.legs]
        )

        for campo in ("value", "delta", "gamma", "vega", "theta", "rho"):
            assert getattr(total, campo) == pytest.approx(
                caso["greeks"][campo], rel=1e-9
            ), campo
