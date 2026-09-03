"""Tests del calculo de probabilidad de beneficio.

Aca se aplica la misma division que con los griegos, y por el mismo motivo.
models.probability_metrics() hace dos cosas en once lineas:

  prices = spot * exp((r-q-sigma^2/2)*T + sigma*sqrt(T)*z)
      Genera los escenarios de precio futuro. Es el modelo lognormal — el
      mismo supuesto que Black-Scholes. Un modelo con saltos o con
      volatilidad estocastica generaria otros -> INFRAESTRUCTURA

  prob = trapezoid((pnl > 0) * pdf, z)
      Dados unos escenarios con sus probabilidades, integra. Eso no depende
      del modelo: vale para cualquier distribucion -> DOMINIO

Separar una y dejar la otra adentro seria incoherente: BSM asume lognormal,
son el mismo supuesto escrito dos veces.
"""

import numpy as np
import pytest

from domain.services.probability import expected_pnl, profit_probability
from domain.value_objects.price_scenarios import PriceScenarios


def escenarios_uniformes(prices):
    """Escenarios con todos los precios igual de probables.

    Sirve para probar la integracion sin arrastrar ningun modelo: con pesos
    uniformes, la probabilidad es simplemente la fraccion de escenarios que
    dan ganancia.
    """
    prices = np.asarray(prices, dtype=float)
    grid = np.linspace(0.0, 1.0, len(prices))
    densities = np.ones_like(prices)
    return PriceScenarios(prices=prices, densities=densities, grid=grid)


class TestProfitProbability:
    def test_todo_ganancia_da_uno(self):
        esc = escenarios_uniformes(np.linspace(900, 1100, 101))
        pnl = np.full(101, 50.0)
        assert profit_probability(pnl, esc) == pytest.approx(1.0)

    def test_todo_perdida_da_cero(self):
        esc = escenarios_uniformes(np.linspace(900, 1100, 101))
        pnl = np.full(101, -50.0)
        assert profit_probability(pnl, esc) == pytest.approx(0.0)

    def test_mitad_y_mitad_da_un_medio(self):
        esc = escenarios_uniformes(np.linspace(900, 1100, 101))
        pnl = np.where(np.linspace(900, 1100, 101) > 1000, 50.0, -50.0)
        assert profit_probability(pnl, esc) == pytest.approx(0.5, abs=0.01)

    def test_el_pnl_cero_no_cuenta_como_ganancia(self):
        """Estrictamente mayor que cero.

        Quedar en el punto de equilibrio no es ganar. Se preserva el criterio
        del codigo original, que usa (pnl > 0).
        """
        esc = escenarios_uniformes(np.linspace(900, 1100, 101))
        assert profit_probability(np.zeros(101), esc) == pytest.approx(0.0)


class TestExpectedPnl:
    def test_pnl_constante_devuelve_ese_valor(self):
        esc = escenarios_uniformes(np.linspace(900, 1100, 101))
        assert expected_pnl(np.full(101, 42.0), esc) == pytest.approx(42.0)

    def test_promedia_ponderando_por_probabilidad(self):
        """Los escenarios mas probables pesan mas.

        Con pnl = +100 en la mitad de arriba y -100 en la de abajo, pero
        densidad tres veces mayor arriba, el esperado se corre hacia +50.

        Las densidades tienen que integrar a 1 sobre la grilla, igual que
        cualquier distribucion de probabilidad. Con la forma 3:1 sobre [0,1],
        eso da 1.5 arriba y 0.5 abajo (0.5*0.5 + 1.5*0.5 = 1).

        La primera version de este test usaba 3.0 y 1.0, que integran a 2, y
        daba 100 en vez de 50. El codigo estaba bien: el test afirmaba algo
        falso.
        """
        n = 101
        grid = np.linspace(0.0, 1.0, n)
        densities = np.where(grid > 0.5, 1.5, 0.5)
        esc = PriceScenarios(prices=np.linspace(900, 1100, n),
                             densities=densities, grid=grid)
        pnl = np.where(grid > 0.5, 100.0, -100.0)
        assert expected_pnl(pnl, esc) == pytest.approx(50.0, abs=2.0)


class TestPriceScenarios:
    def test_las_tres_series_deben_medir_lo_mismo(self):
        with pytest.raises(ValueError, match="longitud"):
            PriceScenarios(prices=np.array([1.0, 2.0]),
                           densities=np.array([1.0]),
                           grid=np.array([0.0, 1.0]))

    def test_es_inmutable(self):
        esc = escenarios_uniformes(np.linspace(900, 1100, 10))
        with pytest.raises(Exception):
            esc.prices = np.zeros(10)


class TestEquivalenciaConElCodigoViejo:
    def test_iron_condor_mismos_numeros(self):
        """Golden master de la Fase 0: prob 0.515239..., esperado -2.933125...

        Se reconstruye a mano la grilla que arma models.probability_metrics()
        y se verifica que integrar por separado da identico.
        """
        from models import Leg as LegViejo, probability_metrics
        from domain.entities.leg import Leg
        from domain.entities.strategy import Strategy

        S, days, sigma, r, q, mult = 1000.0, 30.0, 0.35, 0.05, 0.0, 1.0
        crudas = [
            ("PUT", "COMPRA", 1, 900, 10),
            ("PUT", "VENTA", 1, 950, 20),
            ("CALL", "VENTA", 1, 1050, 20),
            ("CALL", "COMPRA", 1, 1100, 10),
        ]
        esperado = probability_metrics(S, days, sigma, r, q,
                                       [LegViejo(*c) for c in crudas], mult)

        # Misma grilla que genera el modelo lognormal en models.py
        T = days / 365
        z = np.linspace(-5, 5, 20001)
        esc = PriceScenarios(
            prices=S * np.exp((r - q - 0.5 * sigma ** 2) * T + sigma * np.sqrt(T) * z),
            densities=np.exp(-0.5 * z * z) / np.sqrt(2 * np.pi),
            grid=z,
        )
        pnl = Strategy([Leg(*c) for c in crudas], multiplier=mult).payoff(esc.prices)

        assert profit_probability(pnl, esc) == pytest.approx(esperado["prob_profit"], rel=1e-12)
        assert expected_pnl(pnl, esc) == pytest.approx(esperado["expected_pnl"], rel=1e-12)
