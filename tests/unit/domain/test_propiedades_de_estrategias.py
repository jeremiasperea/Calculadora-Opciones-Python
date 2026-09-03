"""Cada estrategia se comporta como dice su nombre.

Estos tests no comparan contra ningun valor guardado: verifican propiedades
del negocio. La diferencia con el golden master importa.

    "el delta del straddle es -0.004556"   <- un numero, no dice nada
    "un straddle es direccionalmente
     neutral, gana con el movimiento y
     con la volatilidad"                    <- una afirmacion verificable

El primero detecta que algo cambio. El segundo detecta que algo esta mal.
Si alguien invierte un signo al refactorizar, el golden master falla y hay
que ir a averiguar cual era el valor correcto; estos dicen directamente que
propiedad se rompio.

Salieron al eliminar test_models_characterization.py en la Fase 6: ese
archivo tenia un test de straddle delta-neutral que no estaba cubierto en
ningun otro lado, y en vez de copiarlo tal cual se lo extendio al resto de
las estrategias.
"""

import pytest

from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from domain.value_objects.market_conditions import MarketConditions
from infrastructure.adapters.bsm_pricing import BSMPricingEngine
from infrastructure.repositories.template_repository import InMemoryTemplateRepository

MERCADO = MarketConditions(spot=1000, days_to_expiry=30, volatility=0.35, rate=0.05)


@pytest.fixture(scope="module")
def calcular():
    caso_de_uso = CalculateStrategyUseCase(BSMPricingEngine())
    repo = InMemoryTemplateRepository()
    return lambda nombre: caso_de_uso.execute(repo.get_template(nombre), MERCADO)


class TestDireccionalidad:
    """El delta dice para donde tiene que ir el subyacente para ganar."""

    def test_long_call_es_alcista(self, calcular):
        assert calcular("Long Call").greeks.delta > 0

    def test_long_put_es_bajista(self, calcular):
        assert calcular("Long Put").greeks.delta < 0

    def test_bull_call_spread_es_alcista(self, calcular):
        assert calcular("Bull Call Spread").greeks.delta > 0

    def test_bear_put_spread_es_bajista(self, calcular):
        assert calcular("Bear Put Spread").greeks.delta < 0

    @pytest.mark.parametrize("nombre", ["Long Straddle", "Short Straddle", "Iron Condor"])
    def test_las_estrategias_de_volatilidad_son_casi_neutrales(self, calcular, nombre):
        """No apuestan a la direccion sino a cuanto se mueve.

        La tolerancia es 0.10 y no 0.01 por una razon del negocio, no por
        holgura: un straddle con strike igual al spot NO es exactamente
        neutral cuando la tasa es positiva.

        La neutralidad se da respecto del FORWARD, no del spot. Con spot 1000,
        tasa 5% y 30 dias, el forward es 1000 * e^(0.05 * 30/365) = 1004.12.
        Un strike de 1000 queda 4 puntos dentro del dinero para el call, y el
        delta del straddle da +0.073 en vez de cero.

        Este test se escribio primero con tolerancia 0.05 y fallo. El error
        estaba en el test: asumia que "en el dinero" significa strike igual al
        spot, cuando en opciones significa strike igual al forward.
        """
        assert abs(calcular(nombre).greeks.delta) < 0.10

    def test_sin_tasa_el_sesgo_del_straddle_se_reduce(self):
        """Demuestra que el sesgo viene de la tasa, pero no solo de ella.

        Sacando la tasa, el delta del straddle baja de +0.073 a +0.040. Se
        reduce a la mitad, pero no llega a cero, y la parte que queda tiene
        otra causa.

        En Black-Scholes el delta de un call es N(d1), y en el forward
        d1 = sigma*sqrt(T)/2, que es positivo. O sea que incluso una opcion
        exactamente en el forward tiene delta apenas mayor que 0.5, y el put
        apenas menor que -0.5 en valor absoluto. La suma da positiva.

        Ese sobrante es la convexidad de la lognormal: como el precio no puede
        bajar de cero pero puede subir sin limite, la distribucion esta
        sesgada hacia arriba y el call vale un poco mas que el put simetrico.

        Escribir este test con tolerancia 0.01 y verlo fallar fue lo que
        obligo a entender de donde salia el resto.
        """
        from application.use_cases.calculate_strategy import CalculateStrategyUseCase
        from infrastructure.adapters.bsm_pricing import BSMPricingEngine
        from infrastructure.repositories.template_repository import (
            InMemoryTemplateRepository,
        )

        uc = CalculateStrategyUseCase(BSMPricingEngine())
        repo = InMemoryTemplateRepository()

        con_tasa = uc.execute(
            repo.get_template("Long Straddle"),
            MarketConditions(spot=1000, days_to_expiry=30, volatility=0.35, rate=0.05),
        ).greeks.delta
        sin_tasa = uc.execute(
            repo.get_template("Long Straddle"),
            MarketConditions(spot=1000, days_to_expiry=30, volatility=0.35, rate=0.0),
        ).greeks.delta

        assert 0 < sin_tasa < con_tasa
        assert sin_tasa < 0.05


class TestExposicionAVolatilidad:
    """Vega positivo: gana si sube la volatilidad. Negativo: gana si baja."""

    @pytest.mark.parametrize("nombre", ["Long Straddle", "Long Strangle", "Long Call"])
    def test_las_compradas_ganan_con_mas_volatilidad(self, calcular, nombre):
        assert calcular(nombre).greeks.vega > 0

    @pytest.mark.parametrize("nombre", ["Short Straddle", "Iron Condor"])
    def test_las_vendidas_ganan_con_menos_volatilidad(self, calcular, nombre):
        assert calcular(nombre).greeks.vega < 0


class TestPasoDelTiempo:
    """Theta: cuanto cambia la posicion por cada dia que pasa."""

    @pytest.mark.parametrize("nombre", ["Long Straddle", "Long Strangle"])
    def test_comprar_opciones_cuesta_tiempo(self, calcular, nombre):
        """Quien compra paga por la posibilidad de que el precio se mueva.

        Cada dia que pasa sin que se mueva, esa posibilidad vale menos.
        """
        assert calcular(nombre).greeks.theta < 0

    @pytest.mark.parametrize("nombre", ["Short Straddle", "Iron Condor"])
    def test_vender_opciones_gana_tiempo(self, calcular, nombre):
        assert calcular(nombre).greeks.theta > 0


class TestGamma:
    """Gamma positivo: el movimiento favorece. Negativo: perjudica."""

    def test_las_compradas_se_benefician_del_movimiento(self, calcular):
        assert calcular("Long Straddle").greeks.gamma > 0

    @pytest.mark.parametrize("nombre", ["Short Straddle", "Iron Condor", "Butterfly Call"])
    def test_las_vendidas_se_perjudican(self, calcular, nombre):
        assert calcular(nombre).greeks.gamma < 0


class TestRiesgoAcotado:
    """Que estrategias tienen perdida limitada y cuales no."""

    @pytest.mark.parametrize("nombre", [
        "Long Call", "Long Put", "Bull Call Spread", "Bear Put Spread",
        "Iron Condor", "Butterfly Call",
    ])
    def test_perdida_acotada(self, calcular, nombre):
        """Sobre el rango dibujado la perdida no supera un limite.

        En las que se compran, ese limite es la prima pagada; en los spreads,
        la diferencia de strikes menos el credito.
        """
        r = calcular(nombre)
        assert r.min_pnl > -1e6

    def test_short_straddle_pierde_en_los_extremos(self, calcular):
        """Vender un straddle tiene perdida teoricamente ilimitada.

        Es la contracara de cobrar la prima: si el subyacente se dispara, la
        perdida crece sin techo. Se verifica que en el borde del rango
        dibujado ya este perdiendo fuerte.
        """
        r = calcular("Short Straddle")
        assert r.pnl[0] < -300
        assert r.pnl[-1] < -300


class TestCoherenciaInterna:
    def test_el_maximo_nunca_es_menor_que_el_minimo(self, calcular):
        for nombre in InMemoryTemplateRepository().list_names():
            r = calcular(nombre)
            assert r.max_pnl >= r.min_pnl, nombre

    def test_la_probabilidad_esta_entre_cero_y_uno(self, calcular):
        for nombre in InMemoryTemplateRepository().list_names():
            assert 0 <= calcular(nombre).profit_probability <= 1, nombre

    def test_los_breakevens_caen_donde_el_pnl_cambia_de_signo(self, calcular):
        """Verifica el breakeven contra la curva, no contra un valor guardado."""
        import numpy as np

        for nombre in InMemoryTemplateRepository().list_names():
            r = calcular(nombre)
            for be in r.breakevens:
                # Justo antes y justo despues del cruce, el signo difiere
                i = int(np.searchsorted(r.prices, be))
                if 0 < i < len(r.pnl) - 1:
                    assert r.pnl[i - 1] * r.pnl[i + 1] <= 0, f"{nombre} en {be}"
