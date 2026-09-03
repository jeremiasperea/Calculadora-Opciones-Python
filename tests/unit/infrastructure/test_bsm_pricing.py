"""Tests del adaptador de valuacion Black-Scholes-Merton.

Este es el archivo donde por fin aparece scipy. Todo lo anterior — dominio,
puertos, casos de uso — se escribio y se probo sin el.

Que se prueba aca es distinto de lo que se probaba antes. En el dominio se
verificaban reglas de negocio; en los casos de uso, orquestacion. Aca se
verifica que la matematica de un modelo concreto sea correcta, con tres
estrategias:

1. Contra un valor analitico publicado (el caso de manual, ~10.4506).
2. Contra propiedades matematicas que deben cumplirse siempre, como la
   paridad put-call. Estas son mejores que un golden master: no dependen de
   que el codigo viejo estuviera bien.
3. Contra models.py, para probar que la migracion no movio ningun numero.
"""

import numpy as np
import pytest

from application.ports.pricing_port import PricingPort
from domain.entities.leg import Leg
from domain.value_objects.market_conditions import MarketConditions
from infrastructure.adapters.bsm_pricing import BSMPricingEngine


MERCADO = MarketConditions(spot=1000, days_to_expiry=30, volatility=0.35, rate=0.05)


class TestCumpleElContrato:
    def test_es_un_pricing_port(self):
        assert isinstance(BSMPricingEngine(), PricingPort)

    def test_se_puede_instanciar(self):
        """Implementa los dos metodos abstractos. Si faltara uno, ABC lo
        impediria aca mismo."""
        BSMPricingEngine()


class TestValoresConocidos:
    def test_call_del_caso_de_manual(self):
        """S=100, K=100, T=1 anio, sigma=20%, r=5%, q=0 -> 10.4506.

        Es el ejemplo que aparece en practicamente todos los libros de
        opciones. Sirve como referencia externa: si esto da bien, la formula
        esta bien implementada, sin importar que dijera el codigo anterior.
        """
        m = MarketConditions(spot=100, days_to_expiry=365, volatility=0.20, rate=0.05)
        g = BSMPricingEngine().price_leg(Leg("CALL", "COMPRA", 1, 100, 0), m)
        assert g.value == pytest.approx(10.4506, rel=1e-4)

    def test_put_del_caso_de_manual(self):
        m = MarketConditions(spot=100, days_to_expiry=365, volatility=0.20, rate=0.05)
        g = BSMPricingEngine().price_leg(Leg("PUT", "COMPRA", 1, 100, 0), m)
        assert g.value == pytest.approx(5.5735, rel=1e-3)


class TestPropiedadesMatematicas:
    """Verdades que deben cumplirse siempre, independientes del codigo viejo.

    Un golden master dice "esto da lo mismo que antes". Estas propiedades
    dicen "esto esta bien". Si el codigo original hubiera tenido un error, el
    golden master lo habria conservado; estos tests lo habrian encontrado.
    """

    def test_paridad_put_call(self):
        """C - P = S*e^(-qT) - K*e^(-rT).

        Es una relacion de no arbitraje: si no se cumpliera, se podria armar
        una posicion con ganancia garantizada. No depende de Black-Scholes ni
        de ningun modelo — vale por la estructura del contrato.
        """
        motor = BSMPricingEngine()
        for spot, strike, dias, vol, tasa in [
            (1000, 1000, 30, 0.35, 0.05),
            (1000, 900, 90, 0.20, 0.03),
            (1000, 1200, 365, 0.50, 0.00),
            (50, 55, 7, 0.80, 0.10),
        ]:
            m = MarketConditions(spot=spot, days_to_expiry=dias,
                                 volatility=vol, rate=tasa)
            c = motor.price_leg(Leg("CALL", "COMPRA", 1, strike, 0), m).value
            p = motor.price_leg(Leg("PUT", "COMPRA", 1, strike, 0), m).value
            T = m.years_to_expiry
            assert c - p == pytest.approx(spot - strike * np.exp(-tasa * T), rel=1e-9)

    def test_el_delta_de_un_call_esta_entre_cero_y_uno(self):
        motor = BSMPricingEngine()
        for strike in [500, 900, 1000, 1100, 1500]:
            g = motor.price_leg(Leg("CALL", "COMPRA", 1, strike, 0), MERCADO)
            assert 0 <= g.delta <= 1, strike

    def test_el_delta_de_un_put_esta_entre_menos_uno_y_cero(self):
        motor = BSMPricingEngine()
        for strike in [500, 900, 1000, 1100, 1500]:
            g = motor.price_leg(Leg("PUT", "COMPRA", 1, strike, 0), MERCADO)
            assert -1 <= g.delta <= 0, strike

    def test_gamma_y_vega_son_iguales_para_call_y_put(self):
        """Consecuencia de la paridad put-call: la diferencia entre ambos es
        lineal en el spot, asi que las derivadas segundas coinciden."""
        motor = BSMPricingEngine()
        c = motor.price_leg(Leg("CALL", "COMPRA", 1, 1000, 0), MERCADO)
        p = motor.price_leg(Leg("PUT", "COMPRA", 1, 1000, 0), MERCADO)
        assert c.gamma == pytest.approx(p.gamma, rel=1e-9)
        assert c.vega == pytest.approx(p.vega, rel=1e-9)

    def test_gamma_y_vega_son_positivos_para_una_compra(self):
        g = BSMPricingEngine().price_leg(Leg("CALL", "COMPRA", 1, 1000, 0), MERCADO)
        assert g.gamma > 0
        assert g.vega > 0

    def test_un_call_muy_dentro_del_dinero_tiene_delta_cercano_a_uno(self):
        g = BSMPricingEngine().price_leg(Leg("CALL", "COMPRA", 1, 100, 0), MERCADO)
        assert g.delta == pytest.approx(1.0, abs=0.01)

    def test_un_call_muy_fuera_del_dinero_tiene_delta_cercano_a_cero(self):
        g = BSMPricingEngine().price_leg(Leg("CALL", "COMPRA", 1, 5000, 0), MERCADO)
        assert g.delta == pytest.approx(0.0, abs=0.01)


class TestContraLosValoresDeReferencia:
    """Los griegos que producia el codigo original, en 18 combinaciones."""

    @pytest.mark.parametrize("tipo", ["CALL", "PUT"])
    @pytest.mark.parametrize("strike", [900, 1000, 1100])
    @pytest.mark.parametrize("dias", [7, 30, 365])
    def test_griegos(self, golden, tipo, strike, dias):
        caso = golden["bsm_casos"][f"{tipo}|K{strike}|{dias}d"]
        m = MarketConditions(spot=1000, days_to_expiry=dias,
                             volatility=0.35, rate=0.05, dividend_yield=0.02)
        obtenido = BSMPricingEngine().price_leg(Leg(tipo, "COMPRA", 1, strike, 0), m)

        for campo in ("value", "delta", "gamma", "vega", "theta", "rho"):
            assert getattr(obtenido, campo) == pytest.approx(
                caso[campo], rel=1e-9
            ), f"{campo} para {tipo} K={strike} {dias}d"

    def test_escenarios_lognormales(self, golden):
        """La grilla reproduce la que generaba probability_metrics."""
        params = golden["parametros"]
        m = MarketConditions(spot=params["spot"],
                             days_to_expiry=params["days_to_expiry"],
                             volatility=params["volatility"],
                             rate=params["rate"],
                             dividend_yield=params["dividend_yield"])
        esc = BSMPricingEngine().generate_scenarios(m)

        T = params["days_to_expiry"] / 365
        z = np.linspace(-5, 5, 20001)
        esperados = params["spot"] * np.exp(
            (params["rate"] - params["dividend_yield"]
             - 0.5 * params["volatility"] ** 2) * T
            + params["volatility"] * np.sqrt(T) * z
        )
        np.testing.assert_allclose(esc.prices, esperados, rtol=1e-12)
        np.testing.assert_allclose(esc.grid, z, rtol=1e-12)


class TestCasosBorde:
    def test_vencimiento_hoy_no_explota(self):
        """days=0 es valido segun MarketConditions: la opcion vence hoy.

        Con T=0 el modelo se indefine (division por cero en d1). Se acota T
        por abajo, igual que el codigo original, para que devuelva el valor
        intrinseco en vez de NaN.
        """
        m = MarketConditions(spot=1100, days_to_expiry=0, volatility=0.35)
        g = BSMPricingEngine().price_leg(Leg("CALL", "COMPRA", 1, 1000, 0), m)
        assert g.value == pytest.approx(100.0, abs=0.01)
        assert not np.isnan(g.delta)

    def test_no_hace_falta_acotar_la_volatilidad(self):
        """models.py hacia max(sigma, 1e-12) por si llegaba cero.

        Ya no hace falta: MarketConditions garantiza volatilidad > 0, asi que
        ese caso no puede construirse. Otra invariante que borra codigo
        defensivo rio abajo.
        """
        with pytest.raises(ValueError):
            MarketConditions(spot=1000, days_to_expiry=30, volatility=0)
