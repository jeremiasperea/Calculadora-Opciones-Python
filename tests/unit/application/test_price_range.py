"""Tests del rango de precios que se dibuja.

El rango fijo de 0.5x a 1.5x del spot alcanza mientras los strikes esten
cerca del precio actual, que es lo habitual. Deja de alcanzar apenas alguien
carga un strike lejano: con spot 1000 y un strike en 1500, la curva se corta
justo en el punto donde la estrategia cambia de forma.

El rango automatico se calcula a partir de los strikes ademas del spot, con
un margen para que se vea que pasa mas alla del ultimo.
"""

import numpy as np
import pytest

from application.dtos.calculation import PriceRange
from domain.entities.leg import Leg
from domain.entities.strategy import Strategy


class TestRangoManual:
    def test_genera_los_precios_alrededor_del_spot(self):
        precios = PriceRange(0.5, 1.5, 401).prices_around(1000)
        assert precios[0] == pytest.approx(500)
        assert precios[-1] == pytest.approx(1500)
        assert len(precios) == 401

    def test_rechaza_un_rango_invertido(self):
        with pytest.raises(ValueError, match="max_factor"):
            PriceRange(1.5, 0.5)


class TestRangoAutomatico:
    def test_cubre_los_strikes_con_margen(self):
        """Un strike lejano arrastra el rango.

        Con spot 1000 y strikes en 900 y 1500, el rango fijo cortaria en 1500
        justo donde el payoff se aplana. Con margen del 10% llega a 1650 y se
        ve la forma completa.
        """
        estrategia = Strategy([
            Leg("CALL", "COMPRA", 1, 900, 40),
            Leg("CALL", "VENTA", 1, 1500, 10),
        ])
        rango = PriceRange.auto(estrategia, spot=1000, margen=0.10)
        precios = rango.prices_around(1000)

        assert precios[0] == pytest.approx(810.0)    # 900 * 0.9
        assert precios[-1] == pytest.approx(1650.0)  # 1500 * 1.1

    def test_el_spot_tambien_cuenta(self):
        """Si el spot queda fuera del rango de strikes, se incluye igual.

        Sin esto, una estrategia con todos los strikes muy por encima del
        precio actual dibujaria una curva que no incluye donde esta el
        subyacente hoy, que es la referencia principal del operador.
        """
        estrategia = Strategy([
            Leg("CALL", "COMPRA", 1, 1400, 10),
            Leg("CALL", "VENTA", 1, 1500, 5),
        ])
        precios = PriceRange.auto(estrategia, spot=1000).prices_around(1000)

        assert precios[0] == pytest.approx(900.0)     # el spot manda el minimo
        assert precios[-1] == pytest.approx(1650.0)

    def test_una_sola_pata(self):
        estrategia = Strategy([Leg("CALL", "COMPRA", 1, 1050, 30)])
        precios = PriceRange.auto(estrategia, spot=1000).prices_around(1000)

        assert precios[0] == pytest.approx(900.0)
        assert precios[-1] == pytest.approx(1155.0)

    def test_respeta_un_margen_distinto(self):
        estrategia = Strategy([Leg("CALL", "COMPRA", 1, 1000, 40)])
        precios = PriceRange.auto(estrategia, spot=1000, margen=0.5).prices_around(1000)

        assert precios[0] == pytest.approx(500.0)
        assert precios[-1] == pytest.approx(1500.0)

    def test_conserva_la_cantidad_de_puntos(self):
        estrategia = Strategy([Leg("CALL", "COMPRA", 1, 1000, 40)])
        assert len(PriceRange.auto(estrategia, 1000, points=201).prices_around(1000)) == 201

    def test_el_rango_nunca_queda_degenerado(self):
        """Con todos los strikes iguales al spot y margen cero, seguiria
        habiendo un rango minimo: un grafico de ancho cero no se puede dibujar.
        """
        estrategia = Strategy([Leg("CALL", "COMPRA", 1, 1000, 40)])
        rango = PriceRange.auto(estrategia, spot=1000, margen=0.0)
        precios = rango.prices_around(1000)
        assert precios[-1] > precios[0]


class TestComparacionConElRangoFijo:
    def test_el_caso_habitual_da_algo_parecido(self):
        """Con strikes cerca del spot, el automatico no se aleja mucho del fijo."""
        estrategia = Strategy([
            Leg("PUT", "COMPRA", 1, 900, 10),
            Leg("CALL", "COMPRA", 1, 1100, 10),
        ])
        auto = PriceRange.auto(estrategia, spot=1000).prices_around(1000)

        assert auto[0] == pytest.approx(810.0)
        assert auto[-1] == pytest.approx(1210.0)

    def test_el_caso_problematico_es_el_que_cambia(self):
        estrategia = Strategy([Leg("CALL", "COMPRA", 1, 1500, 5)])

        fijo = PriceRange(0.5, 1.5, 401).prices_around(1000)
        auto = PriceRange.auto(estrategia, spot=1000).prices_around(1000)

        assert fijo[-1] == pytest.approx(1500.0)   # corta justo en el strike
        assert auto[-1] == pytest.approx(1650.0)   # deja ver que pasa despues
