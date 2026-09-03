"""Tests del dibujo del grafico.

No verifican que se vea bien —eso se mira— sino que genere un PNG valido y
que el limite vertical se respete. El grafico lo comparten la pantalla y el
reporte PDF, asi que un error aca sale en los dos lados.
"""

import pytest

from application.dtos.calculation import PriceRange
from application.dtos.snapshot import SimulationSnapshot
from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from domain.entities.leg import Leg
from domain.entities.strategy import Strategy
from domain.value_objects.market_conditions import MarketConditions
from infrastructure.adapters.bsm_pricing import BSMPricingEngine
from infrastructure.charts.payoff_chart import render_payoff_png


@pytest.fixture
def snapshot():
    estrategia = Strategy([Leg("CALL", "COMPRA", 1, 1000, 40)])
    mercado = MarketConditions(spot=1000, days_to_expiry=30, volatility=0.35)
    resultado = CalculateStrategyUseCase(BSMPricingEngine()).execute(
        estrategia, mercado, PriceRange(0.8, 1.2, 51)
    )
    return SimulationSnapshot(estrategia, mercado, resultado)


class TestGeneracion:
    def test_devuelve_un_png(self, snapshot):
        png = render_payoff_png(snapshot)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_pesa_lo_suficiente_para_tener_contenido(self, snapshot):
        assert len(render_payoff_png(snapshot)) > 5_000

    def test_el_tamano_cambia_con_las_dimensiones(self, snapshot):
        chico = render_payoff_png(snapshot, width=4, height=2, dpi=60)
        grande = render_payoff_png(snapshot, width=12, height=7, dpi=150)
        assert len(grande) > len(chico)


class TestLimiteVertical:
    def test_acepta_un_limite(self, snapshot):
        png = render_payoff_png(snapshot, ylim=(-100, 100))
        assert png[:4] == b"\x89PNG"

    def test_cambia_el_dibujo(self, snapshot):
        """Dos limites distintos producen imagenes distintas.

        Es una verificacion indirecta —comparar bytes de un PNG no dice donde
        quedaron los ejes— pero alcanza para detectar que el parametro se
        ignore por completo, que es la forma en que este tipo de opcion suele
        romperse.
        """
        normal = render_payoff_png(snapshot)
        acotado = render_payoff_png(snapshot, ylim=(-10, 10))
        assert normal != acotado


class TestLimpieza:
    def test_no_deja_figuras_abiertas(self, snapshot):
        """Se llama en cada recalculo: una figura filtrada por vez se acumula."""
        import matplotlib.pyplot as plt

        antes = len(plt.get_fignums())
        for _ in range(5):
            render_payoff_png(snapshot)
        assert len(plt.get_fignums()) == antes
