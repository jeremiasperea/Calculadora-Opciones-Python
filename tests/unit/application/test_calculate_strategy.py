"""Tests del caso de uso de calculo.

Aca se cobra lo que costaron las fases 1 y 2. Toda la orquestacion del
calculo — la que hoy vive dentro de app.calculate(), enredada con widgets de
Tkinter — se prueba con dobles escritos a mano, sin scipy, sin matplotlib,
sin base de datos y sin abrir una ventana.

Sobre fakes y mocks: un *fake* es una implementacion de verdad, simple pero
funcional. Un *mock* graba llamadas y despues se le pregunta si ocurrieron.
Aca se usan fakes, porque lo que interesa es el resultado, no la coreografia.
Un test que afirma "se llamo a price_leg cuatro veces" se rompe con cualquier
refactor interno aunque el numero final siga estando bien; uno que afirma
"el delta total dio 0.3" solo se rompe si el resultado cambia.

Los griegos de los fakes son numeros inventados. Si fueran valores de
Black-Scholes reales, estos tests estarian probando dos cosas a la vez — la
orquestacion y la matematica — y cuando fallaran no se sabria cual de las dos
se rompio.
"""

import numpy as np
import pytest

from application.dtos.calculation import CalculationResult, PriceRange
from application.ports.pricing_port import PricingPort
from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from domain.entities.greeks import Greeks
from domain.entities.leg import Leg
from domain.entities.strategy import Strategy
from domain.value_objects.market_conditions import MarketConditions
from domain.value_objects.price_scenarios import PriceScenarios


class PricingFalso(PricingPort):
    """Devuelve siempre los mismos griegos y escenarios uniformes.

    Simple a proposito: si el doble tuviera logica, un test rojo no diria si
    se rompio el caso de uso o el doble.
    """

    def __init__(self, greeks_por_pata=None):
        self.greeks_por_pata = greeks_por_pata or Greeks(value=10, delta=0.5, gamma=0.1)
        self.llamadas = []

    def price_leg(self, leg, market):
        self.llamadas.append((leg, market))
        return self.greeks_por_pata

    def generate_scenarios(self, market, points=20_001):
        # Precios uniformes entre 0.5x y 1.5x del spot, todos igual de probables.
        n = 1001
        prices = np.linspace(market.spot * 0.5, market.spot * 1.5, n)
        return PriceScenarios(
            prices=prices,
            densities=np.ones(n),
            grid=np.linspace(0.0, 1.0, n),
        )


MERCADO = MarketConditions(spot=1000, days_to_expiry=30, volatility=0.35, rate=0.05)


def long_call():
    return Strategy([Leg("CALL", "COMPRA", 1, 1000, 40)])


def bull_call_spread():
    return Strategy([
        Leg("CALL", "COMPRA", 1, 1000, 40),
        Leg("CALL", "VENTA", 1, 1100, 15),
    ])


class TestResultado:
    def test_devuelve_un_calculation_result(self):
        uc = CalculateStrategyUseCase(PricingFalso())
        assert isinstance(uc.execute(long_call(), MERCADO), CalculationResult)

    def test_la_curva_cubre_el_rango_pedido(self):
        uc = CalculateStrategyUseCase(PricingFalso())
        res = uc.execute(long_call(), MERCADO, PriceRange(0.8, 1.2, 101))
        assert len(res.prices) == 101
        assert res.prices[0] == pytest.approx(800.0)
        assert res.prices[-1] == pytest.approx(1200.0)

    def test_el_rango_por_defecto_es_el_de_la_app(self):
        uc = CalculateStrategyUseCase(PricingFalso())
        res = uc.execute(long_call(), MERCADO)
        assert len(res.prices) == 401
        assert res.prices[0] == pytest.approx(500.0)
        assert res.prices[-1] == pytest.approx(1500.0)

    def test_el_pnl_corresponde_al_payoff_de_la_estrategia(self):
        uc = CalculateStrategyUseCase(PricingFalso())
        s = long_call()
        res = uc.execute(s, MERCADO)
        np.testing.assert_allclose(res.pnl, s.payoff(res.prices))

    def test_reporta_maximo_y_minimo(self):
        uc = CalculateStrategyUseCase(PricingFalso())
        res = uc.execute(long_call(), MERCADO)
        assert res.max_pnl == pytest.approx(res.pnl.max())
        assert res.min_pnl == pytest.approx(res.pnl.min())
        # Long call comprado a 40: la perdida maxima es la prima
        assert res.min_pnl == pytest.approx(-40.0)

    def test_reporta_el_flujo_inicial(self):
        uc = CalculateStrategyUseCase(PricingFalso())
        assert uc.execute(long_call(), MERCADO).net_premium == pytest.approx(-40.0)

    def test_encuentra_el_breakeven(self):
        """Long call strike 1000 con prima 40: equilibrio en 1040."""
        uc = CalculateStrategyUseCase(PricingFalso())
        res = uc.execute(long_call(), MERCADO)
        assert len(res.breakevens) == 1
        assert res.breakevens[0] == pytest.approx(1040.0, abs=2.0)


class TestAgregacionDeGriegos:
    def test_pide_los_griegos_de_cada_pata(self):
        pricing = PricingFalso()
        CalculateStrategyUseCase(pricing).execute(bull_call_spread(), MERCADO)
        assert len(pricing.llamadas) == 2

    def test_le_pasa_a_cada_pata_su_propio_leg(self):
        pricing = PricingFalso()
        CalculateStrategyUseCase(pricing).execute(bull_call_spread(), MERCADO)
        strikes = [leg.strike for leg, _ in pricing.llamadas]
        assert strikes == [1000, 1100]

    def test_los_agrega_con_el_signo_de_cada_lado(self):
        """Compra + venta con el mismo delta unitario se cancelan.

        Verificable a mano: el fake devuelve delta=0.5 para las dos patas,
        una comprada (+1) y otra vendida (-1). Total: 0.5 - 0.5 = 0.
        """
        uc = CalculateStrategyUseCase(PricingFalso(Greeks(delta=0.5)))
        assert uc.execute(bull_call_spread(), MERCADO).greeks.delta == pytest.approx(0.0)

    def test_aplica_el_multiplicador(self):
        s = Strategy([Leg("CALL", "COMPRA", 1, 1000, 40)], multiplier=100)
        uc = CalculateStrategyUseCase(PricingFalso(Greeks(delta=0.5)))
        assert uc.execute(s, MERCADO).greeks.delta == pytest.approx(50.0)


class TestProbabilidades:
    def test_calcula_probabilidad_y_esperado(self):
        uc = CalculateStrategyUseCase(PricingFalso())
        res = uc.execute(long_call(), MERCADO)
        assert 0 <= res.profit_probability <= 1
        assert isinstance(res.expected_pnl, float)

    def test_usa_los_escenarios_del_puerto_no_la_curva(self):
        """La curva de la pantalla y los escenarios son cosas distintas.

        La curva se dibuja sobre un rango elegido para que se vea bien. Las
        probabilidades se integran sobre la distribucion del modelo, que tiene
        otra grilla y otra densidad. Mezclarlas daria un numero sin sentido.
        """
        uc = CalculateStrategyUseCase(PricingFalso())
        res = uc.execute(long_call(), MERCADO, PriceRange(0.99, 1.01, 11))
        # El rango de la curva es angosto, pero la probabilidad sale de los
        # escenarios (0.5x a 1.5x), asi que no queda pegada a 0 ni a 1.
        assert 0 < res.profit_probability < 1


class TestIndependenciaDeLaInfraestructura:
    def test_el_caso_de_uso_no_sabe_como_se_valua(self):
        """Dos modelos distintos, misma orquestacion.

        Este test es la fase entera en cuatro lineas: se cambia el modelo de
        pricing por otro que devuelve el doble de delta, y el caso de uso
        produce el resultado correcto sin enterarse. Eso es lo que compra la
        inversion de dependencias.
        """
        modelo_a = CalculateStrategyUseCase(PricingFalso(Greeks(delta=0.5)))
        modelo_b = CalculateStrategyUseCase(PricingFalso(Greeks(delta=1.0)))

        assert modelo_a.execute(long_call(), MERCADO).greeks.delta == pytest.approx(0.5)
        assert modelo_b.execute(long_call(), MERCADO).greeks.delta == pytest.approx(1.0)

    def test_el_payoff_no_depende_del_modelo(self):
        """El P&L al vencimiento es contractual, no un modelo.

        Cambiar el motor de valuacion no puede mover la curva de payoff: al
        vencimiento la opcion vale su valor intrinseco y punto. Si este test
        fallara, algo del pricing se estaria filtrando donde no va.
        """
        a = CalculateStrategyUseCase(PricingFalso(Greeks(delta=0.5)))
        b = CalculateStrategyUseCase(PricingFalso(Greeks(delta=99.0)))
        np.testing.assert_allclose(
            a.execute(long_call(), MERCADO).pnl,
            b.execute(long_call(), MERCADO).pnl,
        )
