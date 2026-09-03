"""Test de integracion: la cadena completa contra los valores de referencia.

Arma todo junto —caso de uso real, adaptador real, dominio real— y compara
contra los numeros que se capturaron del codigo original antes de eliminarlo.

Es el test que autoriza a borrar la implementacion vieja: si estos valores
coinciden, la arquitectura nueva hace lo mismo que hacia app.calculate().
"""

import numpy as np
import pytest

from application.dtos.calculation import PriceRange
from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from domain.entities.leg import Leg
from domain.entities.strategy import Strategy
from domain.value_objects.market_conditions import MarketConditions
from infrastructure.adapters.bsm_pricing import BSMPricingEngine

PLANTILLAS = [
    "Long Call", "Long Put", "Bull Call Spread", "Bear Put Spread",
    "Long Straddle", "Short Straddle", "Long Strangle", "Iron Condor",
    "Butterfly Call", "Call Backspread", "Put Backspread",
]

# Butterfly Call con credito neto cero: el codigo original contaba como
# ganancia escenarios que valen exactamente cero, por residuos de redondeo.
# Ver TestDiferenciaNumericaConocida al final del archivo.
PROBABILIDAD_CORREGIDA = {
    "Butterfly Call|x1": 0.3818664792992925,
    "Butterfly Call|x100": 0.3818664792992925,
}


def calcular(caso: dict, multiplicador: float, params: dict):
    estrategia = Strategy(
        [Leg(p["option_type"], p["side"], p["quantity"], p["strike"], p["premium"])
         for p in caso["patas"]],
        multiplier=multiplicador,
    )
    mercado = MarketConditions(
        spot=params["spot"],
        days_to_expiry=params["days_to_expiry"],
        volatility=params["volatility"],
        rate=params["rate"],
        dividend_yield=params["dividend_yield"],
    )
    resultado = CalculateStrategyUseCase(BSMPricingEngine()).execute(
        estrategia, mercado, PriceRange(0.5, 1.5, 401)
    )
    return estrategia, resultado


@pytest.mark.parametrize("multiplicador", [1.0, 100.0])
@pytest.mark.parametrize("nombre", PLANTILLAS)
class TestTodasLasPlantillas:
    """Las 11 estrategias, con multiplicador 1 y 100.

    El 100 no es decorativo: un error de doble escalado es invisible con
    multiplicador 1, porque 1x1 = 1.
    """

    def _caso(self, golden, nombre, multiplicador):
        clave = f"{nombre}|x{multiplicador:g}"
        return clave, golden["plantillas"][clave]

    def test_resultado_economico(self, golden, nombre, multiplicador):
        clave, caso = self._caso(golden, nombre, multiplicador)
        _, r = calcular(caso, multiplicador, golden["parametros"])

        assert r.net_premium == pytest.approx(caso["net_premium"], rel=1e-9)
        assert r.max_pnl == pytest.approx(caso["max_pnl"], rel=1e-9)
        assert r.min_pnl == pytest.approx(caso["min_pnl"], rel=1e-9)

    def test_breakevens(self, golden, nombre, multiplicador):
        clave, caso = self._caso(golden, nombre, multiplicador)
        _, r = calcular(caso, multiplicador, golden["parametros"])

        assert len(r.breakevens) == len(caso["breakevens"])
        assert list(r.breakevens) == pytest.approx(caso["breakevens"], rel=1e-9)

    def test_griegos(self, golden, nombre, multiplicador):
        clave, caso = self._caso(golden, nombre, multiplicador)
        _, r = calcular(caso, multiplicador, golden["parametros"])

        for campo in ("value", "delta", "gamma", "vega", "theta", "rho"):
            assert getattr(r.greeks, campo) == pytest.approx(
                caso["greeks"][campo], rel=1e-9
            ), campo

    def test_probabilidades(self, golden, nombre, multiplicador):
        clave, caso = self._caso(golden, nombre, multiplicador)
        _, r = calcular(caso, multiplicador, golden["parametros"])

        esperada = PROBABILIDAD_CORREGIDA.get(clave, caso["prob_profit"])
        assert r.profit_probability == pytest.approx(esperada, rel=1e-9)
        assert r.expected_pnl == pytest.approx(caso["expected_pnl"], rel=1e-9)

    def test_forma_de_la_curva(self, golden, nombre, multiplicador):
        """Nueve puntos repartidos a lo largo de la curva.

        Comparar los 401 seria mas exhaustivo y mucho mas pesado de guardar.
        Nueve alcanzan para detectar un cambio de forma: si la curva se movio,
        alguno cae distinto.
        """
        clave, caso = self._caso(golden, nombre, multiplicador)
        _, r = calcular(caso, multiplicador, golden["parametros"])

        muestra = [float(r.pnl[i]) for i in range(0, 401, 50)]
        assert muestra == pytest.approx(caso["curva_muestra"], rel=1e-9)


class TestDiferenciaNumericaConocida:
    """La unica diferencia con el codigo original, y por que es una mejora.

    En Butterfly Call la probabilidad de beneficio da 38.2% donde el codigo
    viejo daba 41.0%. No es un error de la migracion: es la correccion de uno
    del original.

    Esa estrategia tiene credito neto exactamente cero (-70 + 90 - 20), asi
    que en las alas el P&L verdadero es 0: no se gana ni se pierde. Pero
    models.py escalaba cada pata por el multiplicador antes de sumarlas —
    (a*100) + (b*100) + (c*100) — y el redondeo dejaba residuos del orden de
    1e-13. Como el criterio de ganancia es estrictamente `pnl > 0`, 501 de los
    20.001 escenarios contaban como ganancia valiendo cero.

    Strategy.payoff() suma primero y escala una sola vez. Algebraicamente es
    lo mismo; en coma flotante acumula menos error y da el cero exacto.

    Tres puntos porcentuales son materiales para quien opera, asi que se
    conserva el numero correcto y se documenta el apartamiento en lugar de
    replicar el error para que los tests cierren.
    """

    def _butterfly(self, golden, multiplicador=100.0):
        caso = golden["plantillas"][f"Butterfly Call|x{multiplicador:g}"]
        return calcular(caso, multiplicador, golden["parametros"])

    def test_las_alas_valen_exactamente_cero(self, golden):
        estrategia, _ = self._butterfly(golden)
        assert estrategia.payoff(np.array([700.0]))[0] == 0.0
        assert estrategia.payoff(np.array([1400.0]))[0] == 0.0

    def test_la_probabilidad_excluye_las_alas(self, golden):
        _, r = self._butterfly(golden)
        assert r.profit_probability == pytest.approx(0.3818664792992925, rel=1e-9)

    def test_el_valor_del_codigo_viejo_queda_registrado(self, golden):
        """Se deja escrito cuanto daba antes, para que la diferencia sea
        rastreable si alguien compara con una version anterior."""
        viejo = golden["plantillas"]["Butterfly Call|x100"]["prob_profit"]
        assert viejo == pytest.approx(0.40995190501807055, rel=1e-9)
        assert viejo > 0.3818664792992925
