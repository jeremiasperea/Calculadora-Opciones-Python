"""Tests de MarketConditions: el estado del mercado al momento de valuar.

Este value object no estaba en el plan de la Fase 1. Aparecio al disenar
PricingPort en la Fase 2, y vale la pena contar por que.

La firma que habia que copiar era:

    greeks(S, K, T_days, sigma, r=0, q=0, option_type="CALL")

Seis parametros sueltos, cinco de ellos floats sin nombre en el punto de
llamada. Intercambiar r con q compila, corre y devuelve un numero distinto
sin avisar. Fowler lo llamo "Data Clump": un grupo de parametros que siempre
viaja junto es un objeto que todavia no se escribio.

Diseniar una interfaz obliga a nombrar el contrato, y nombrarlo saca a la luz
conceptos que faltaban. No es un desvio de la fase: es la fase haciendo su
trabajo.
"""

import pytest

from domain.value_objects.market_conditions import MarketConditions


class TestConstruccion:
    def test_se_construye_con_valores_validos(self):
        m = MarketConditions(spot=1000, days_to_expiry=30, volatility=0.35,
                             rate=0.05, dividend_yield=0.0)
        assert m.spot == 1000
        assert m.days_to_expiry == 30
        assert m.volatility == 0.35

    def test_tasa_y_dividendo_tienen_default_cero(self):
        m = MarketConditions(spot=1000, days_to_expiry=30, volatility=0.35)
        assert m.rate == 0.0
        assert m.dividend_yield == 0.0

    def test_years_to_expiry_convierte_dias_a_anios(self):
        """Black-Scholes trabaja en anios; el operador piensa en dias.

        La conversion vive aca y no en el adaptador de pricing porque la
        convencion (365 dias corridos) es una decision del negocio, no del
        modelo. Un binomial usaria la misma.
        """
        m = MarketConditions(spot=1000, days_to_expiry=365, volatility=0.35)
        assert m.years_to_expiry == pytest.approx(1.0)

        m30 = MarketConditions(spot=1000, days_to_expiry=30, volatility=0.35)
        assert m30.years_to_expiry == pytest.approx(30 / 365)


class TestInvariantes:
    def test_el_spot_debe_ser_positivo(self):
        for spot in [0, -1]:
            with pytest.raises(ValueError, match="spot"):
                MarketConditions(spot=spot, days_to_expiry=30, volatility=0.35)

    def test_la_volatilidad_debe_ser_positiva(self):
        """Volatilidad cero es un caso degenerado, no un mercado.

        Significaria que el precio futuro se conoce con certeza. BSM divide
        por sigma y probability_metrics devuelve NaN. Mejor rechazarlo en el
        borde que arrastrar un NaN hasta la pantalla del operador.
        """
        for vol in [0, -0.1]:
            with pytest.raises(ValueError, match="[Vv]olatilidad"):
                MarketConditions(spot=1000, days_to_expiry=30, volatility=vol)

    def test_los_dias_no_pueden_ser_negativos(self):
        with pytest.raises(ValueError, match="[Dd]ias"):
            MarketConditions(spot=1000, days_to_expiry=-1, volatility=0.35)

    def test_cero_dias_es_valido(self):
        """Vence hoy. El payoff al vencimiento sigue teniendo sentido."""
        m = MarketConditions(spot=1000, days_to_expiry=0, volatility=0.35)
        assert m.years_to_expiry == 0

    def test_la_tasa_puede_ser_negativa(self):
        """A proposito: las tasas negativas existen.

        Europa y Japon operaron anios con tasas por debajo de cero. Validar
        rate > 0 seria meter en el dominio un supuesto que el mundo real ya
        desmintio. Una invariante debe describir el negocio, no lo que a uno
        le parece normal.
        """
        m = MarketConditions(spot=1000, days_to_expiry=30, volatility=0.35, rate=-0.005)
        assert m.rate == -0.005

    def test_el_dividendo_no_puede_ser_negativo(self):
        """A diferencia de la tasa: un rendimiento por dividendos negativo
        significaria que tener la accion cuesta plata, que no es un dividendo.
        """
        with pytest.raises(ValueError, match="[Dd]ividendo"):
            MarketConditions(spot=1000, days_to_expiry=30, volatility=0.35,
                             dividend_yield=-0.01)


class TestInmutabilidad:
    def test_no_se_puede_modificar(self):
        m = MarketConditions(spot=1000, days_to_expiry=30, volatility=0.35)
        with pytest.raises(Exception):
            m.spot = 2000
