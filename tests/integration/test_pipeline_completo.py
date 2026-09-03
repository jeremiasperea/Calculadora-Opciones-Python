"""Test de integracion: la cadena nueva completa contra el golden master.

Los tests unitarios verificaron cada pieza por separado, cada uno con dobles
donde hacia falta. Este arma todo junto —caso de uso real, adaptador real,
dominio real— y compara contra los numeros que la Fase 0 capturo de
app.calculate().

Es la prueba de sustitucion de Liskov aplicada al proyecto entero: en la
Fase 3 el caso de uso corria con un PricingFalso; aca corre con
BSMPricingEngine sin cambiar una sola linea, y da los numeros correctos.

Si este test pasa, la arquitectura nueva puede reemplazar a la vieja.
"""

import numpy as np
import pytest

from application.dtos.calculation import PriceRange
from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from domain.entities.leg import Leg
from domain.entities.strategy import Strategy
from domain.value_objects.market_conditions import MarketConditions
from infrastructure.adapters.bsm_pricing import BSMPricingEngine


# Mismos parametros que usa la app por defecto
IRON_CONDOR = [
    ("PUT", "COMPRA", 1, 900, 10),
    ("PUT", "VENTA", 1, 950, 20),
    ("CALL", "VENTA", 1, 1050, 20),
    ("CALL", "COMPRA", 1, 1100, 10),
]


@pytest.fixture
def resultado():
    """Calcula el Iron Condor con la cadena nueva completa."""
    estrategia = Strategy([Leg(*c) for c in IRON_CONDOR], multiplier=1.0)
    mercado = MarketConditions(
        spot=1000.0, days_to_expiry=30.0, volatility=0.35,
        rate=0.05, dividend_yield=0.0,
    )
    caso_de_uso = CalculateStrategyUseCase(BSMPricingEngine())
    return caso_de_uso.execute(estrategia, mercado, PriceRange(0.5, 1.5, 401))


class TestContraElGoldenMaster:
    """Valores capturados en la Fase 0 de models.py + app.calculate()."""

    def test_flujo_inicial(self, resultado):
        assert resultado.net_premium == pytest.approx(20.0)

    def test_maximo_y_minimo(self, resultado):
        assert resultado.max_pnl == pytest.approx(20.0)
        assert resultado.min_pnl == pytest.approx(-30.0)

    def test_breakevens(self, resultado):
        assert len(resultado.breakevens) == 2
        assert resultado.breakevens[0] == pytest.approx(930.0, abs=0.01)
        assert resultado.breakevens[1] == pytest.approx(1070.0, abs=0.01)

    def test_griegos(self, resultado):
        g = resultado.greeks
        assert g.delta == pytest.approx(-0.004556719861883218, rel=1e-9)
        assert g.gamma == pytest.approx(-0.002170497346895761, rel=1e-9)
        assert g.vega == pytest.approx(-0.6243896477371369, rel=1e-9)
        assert g.theta == pytest.approx(0.3617228600607449, rel=1e-9)
        assert g.rho == pytest.approx(0.015026606715508983, rel=1e-9)

    def test_probabilidades(self, resultado):
        assert resultado.profit_probability == pytest.approx(0.515239261105258, rel=1e-9)
        assert resultado.expected_pnl == pytest.approx(-2.9331256909927075, rel=1e-9)

    def test_la_curva_completa(self, resultado):
        """Los 401 puntos, no solo el maximo y el minimo."""
        from models import Leg as LegViejo, strategy_payoff

        precios = np.linspace(500, 1500, 401)
        esperado = strategy_payoff(precios, [LegViejo(*c) for c in IRON_CONDOR], 1.0)
        np.testing.assert_allclose(resultado.pnl, esperado, rtol=1e-12)


class TestTodasLasPlantillas:
    """La equivalencia no vale solo para el condor."""

    @pytest.mark.parametrize("nombre", [
        "Long Call", "Long Put", "Bull Call Spread", "Bear Put Spread",
        "Long Straddle", "Short Straddle", "Long Strangle", "Iron Condor",
        "Butterfly Call", "Call Backspread", "Put Backspread",
    ])
    def test_coincide_con_la_app_vieja(self, nombre):
        """Replica app.calculate() y compara todo el resultado.

        Cubre las 11 plantillas con multiplicador 100, que es donde un bug de
        doble escalado se veria — con multiplicador 1 es invisible.
        """
        from models import (
            strategy_payoff, strategy_greeks, approximate_breakevens,
            probability_metrics,
        )
        from strategies import TEMPLATES

        S, iv, r, q, dias, mult = 1000.0, 0.35, 0.05, 0.0, 30.0, 100.0
        patas_viejas = TEMPLATES[nombre]

        # --- Cadena vieja ---
        precios = np.linspace(S * 0.5, S * 1.5, 401)
        pnl_viejo = strategy_payoff(precios, patas_viejas, mult)
        g_viejo = strategy_greeks(S, dias, iv, r, q, patas_viejas, mult)
        inicial_viejo = sum(
            (-1 if p.side == "COMPRA" else 1) * p.quantity * p.premium * mult
            for p in patas_viejas
        )
        be_viejo = approximate_breakevens(precios, pnl_viejo)
        pm_viejo = probability_metrics(S, dias, iv, r, q, patas_viejas, mult)

        # --- Cadena nueva ---
        estrategia = Strategy(
            [Leg(p.option_type, p.side, p.quantity, p.strike, p.premium)
             for p in patas_viejas],
            multiplier=mult,
        )
        mercado = MarketConditions(spot=S, days_to_expiry=dias,
                                   volatility=iv, rate=r, dividend_yield=q)
        nuevo = CalculateStrategyUseCase(BSMPricingEngine()).execute(
            estrategia, mercado, PriceRange(0.5, 1.5, 401)
        )

        # --- Comparacion ---
        np.testing.assert_allclose(nuevo.pnl, pnl_viejo, rtol=1e-12)
        assert nuevo.net_premium == pytest.approx(inicial_viejo, rel=1e-12)
        assert list(nuevo.breakevens) == pytest.approx(be_viejo, rel=1e-12)
        assert nuevo.expected_pnl == pytest.approx(pm_viejo["expected_pnl"], rel=1e-9)

        # profit_probability: ver TestDiferenciaNumericaConocida mas abajo.
        # La implementacion nueva es mas estable y en Butterfly Call corrige
        # un error de redondeo del codigo original.
        if nombre != "Butterfly Call":
            assert nuevo.profit_probability == pytest.approx(
                pm_viejo["prob_profit"], rel=1e-9
            )
        for campo in ("value", "delta", "gamma", "vega", "theta", "rho"):
            assert getattr(nuevo.greeks, campo) == pytest.approx(
                g_viejo[campo], rel=1e-12
            ), campo


class TestDiferenciaNumericaConocida:
    """La unica diferencia con el codigo viejo, y por que es una mejora.

    En Butterfly Call la probabilidad de beneficio pasa de 41.0% a 38.2%. No
    es un error de la migracion: es la correccion de uno del codigo original.

    Esa estrategia tiene credito neto exactamente cero (-70 + 90 - 20 = 0), asi
    que en las alas el P&L verdadero es 0: no se gana ni se pierde nada. Pero
    models.py escala cada pata por el multiplicador antes de sumarlas —
    (a*100) + (b*100) + (c*100) — y el redondeo deja residuos del orden de
    1e-13. Como el criterio de ganancia es estrictamente `pnl > 0`, 501 de los
    20.001 escenarios cuentan como ganancia siendo que valen cero.

    Strategy.payoff() suma primero y escala una sola vez, (a + b + c) * 100.
    Algebraicamente es lo mismo; en coma flotante acumula menos error y en este
    caso da el cero exacto.

    Tres puntos porcentuales de diferencia en la probabilidad de beneficio son
    materiales para quien opera, asi que se conserva el numero correcto y se
    documenta el apartamiento en vez de replicar el error para que los tests
    cierren.
    """

    def test_las_alas_del_butterfly_valen_exactamente_cero(self):
        from strategies import TEMPLATES

        patas = TEMPLATES["Butterfly Call"]
        s = Strategy(
            [Leg(p.option_type, p.side, p.quantity, p.strike, p.premium) for p in patas],
            multiplier=100.0,
        )
        # spot muy por debajo del strike mas bajo: las tres expiran sin valor
        assert s.payoff(np.array([700.0]))[0] == 0.0
        # spot muy por encima del mas alto: el payoff se cancela entre patas
        assert s.payoff(np.array([1400.0]))[0] == 0.0

    def test_el_codigo_viejo_deja_residuo_de_redondeo(self):
        """Se documenta el error original para que quede registro de por que
        los numeros no coinciden.

        El residuo no aparece con precios redondos como 1400.0, donde la
        cuenta cierra exacta en binario. Aparece con los precios de la grilla
        de escenarios, que salen de S*exp(...) y traen muchos decimales. Por
        eso el error se manifiesta justo en el calculo de probabilidades y no
        en la curva que se dibuja.
        """
        from models import strategy_payoff
        from strategies import TEMPLATES

        # La misma grilla que usa probability_metrics
        T = 30 / 365
        z = np.linspace(-5, 5, 20001)
        precios = 1000 * np.exp((0.05 - 0.5 * 0.35 ** 2) * T + 0.35 * np.sqrt(T) * z)

        viejo = strategy_payoff(precios, TEMPLATES["Butterfly Call"], 100.0)
        nuevo = Strategy(
            [Leg(p.option_type, p.side, p.quantity, p.strike, p.premium)
             for p in TEMPLATES["Butterfly Call"]],
            multiplier=100.0,
        ).payoff(precios)

        # En el ala derecha el P&L verdadero es cero
        ala = precios > 1100
        assert np.all(nuevo[ala] == 0.0)

        # models.py deja residuos positivos del orden de 1e-13
        residuos = viejo[ala]
        assert np.any(residuos > 0)
        assert residuos.max() < 1e-11

        # Y por eso los contaba como ganancia
        assert (viejo[ala] > 0).sum() > 100
        assert (nuevo[ala] > 0).sum() == 0

    def test_la_probabilidad_nueva_excluye_las_alas(self):
        """38.2% es el numero correcto: las alas no son ganancia."""
        from strategies import TEMPLATES

        patas = TEMPLATES["Butterfly Call"]
        estrategia = Strategy(
            [Leg(p.option_type, p.side, p.quantity, p.strike, p.premium) for p in patas],
            multiplier=100.0,
        )
        mercado = MarketConditions(spot=1000.0, days_to_expiry=30.0,
                                   volatility=0.35, rate=0.05)
        res = CalculateStrategyUseCase(BSMPricingEngine()).execute(estrategia, mercado)
        assert res.profit_probability == pytest.approx(0.3818664792992925, rel=1e-9)
