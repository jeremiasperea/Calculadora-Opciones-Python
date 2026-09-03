"""Tests de Strategy: el conjunto de patas que forman una posicion.

Strategy es el aggregate root del dominio. Un "agregado" es un grupo de
objetos que se trata como una unidad: no tiene sentido evaluar una pata de
un iron condor por separado, porque el riesgo esta en como se combinan las
cuatro. Quien use el dominio pide el payoff de la estrategia, no de la pata.

Los numeros de los tests son los mismos del golden master de la Fase 0. Si
Strategy.payoff() da lo mismo que strategy_payoff(), la migracion no cambio
comportamiento.
"""

import numpy as np
import pytest

from domain.entities.leg import Leg
from domain.entities.strategy import Strategy


def bull_call_spread(premium_compra=0.0, premium_venta=0.0):
    return Strategy([
        Leg("CALL", "COMPRA", 1, 1000, premium_compra),
        Leg("CALL", "VENTA", 1, 1100, premium_venta),
    ])


def iron_condor():
    return Strategy([
        Leg("PUT", "COMPRA", 1, 900, 10),
        Leg("PUT", "VENTA", 1, 950, 20),
        Leg("CALL", "VENTA", 1, 1050, 20),
        Leg("CALL", "COMPRA", 1, 1100, 10),
    ])


class TestInvariantes:
    def test_necesita_al_menos_una_pata(self):
        with pytest.raises(ValueError, match="pata"):
            Strategy([])

    def test_el_multiplicador_debe_ser_positivo(self):
        for mult in [0, -1]:
            with pytest.raises(ValueError, match="multiplicador"):
                Strategy([Leg("CALL", "COMPRA", 1, 1000, 40)], multiplier=mult)

    def test_no_hay_limite_de_patas_en_el_dominio(self):
        """El maximo de 6 es de la UI, no del negocio.

        app.py dibuja 6 filas de widgets. Esa es una decision de pantalla:
        nada en la operatoria de opciones prohibe una estrategia de 10 patas.
        Meter ese limite en el dominio seria dejar que la UI le dicte reglas
        al negocio.
        """
        patas = [Leg("CALL", "COMPRA", 1, 1000 + i * 10, 5) for i in range(10)]
        assert len(Strategy(patas).legs) == 10


class TestPayoff:
    """Mismos casos que el golden master de la Fase 0."""

    def test_por_debajo_de_ambos_strikes(self):
        payoff = bull_call_spread().payoff(np.array([900.0]))
        assert payoff[0] == pytest.approx(0.0)

    def test_entre_los_strikes(self):
        payoff = bull_call_spread().payoff(np.array([1050.0]))
        assert payoff[0] == pytest.approx(50.0)

    def test_por_encima_de_ambos_strikes(self):
        """El techo de un bull call spread es la diferencia de strikes."""
        payoff = bull_call_spread().payoff(np.array([1200.0]))
        assert payoff[0] == pytest.approx(100.0)

    def test_descuenta_la_prima(self):
        """Un call ITM que costo lo que gano deja P&L cero."""
        s = Strategy([Leg("CALL", "COMPRA", 1, 1050, 30)])
        assert s.payoff(np.array([1080.0]))[0] == pytest.approx(0.0)

    def test_acepta_un_escalar(self):
        assert bull_call_spread().payoff(1050.0) == pytest.approx(50.0)

    def test_el_multiplicador_escala_linealmente(self):
        """El caso que la prueba de mutacion de la Fase 0 dejo al descubierto.

        Con multiplier=1 un bug de doble aplicacion es invisible, porque
        1*1=1. Con 100 se ve.
        """
        base = Strategy([Leg("CALL", "COMPRA", 1, 1000, 40)], multiplier=1)
        x100 = Strategy([Leg("CALL", "COMPRA", 1, 1000, 40)], multiplier=100)
        spot = np.array([1100.0])
        assert base.payoff(spot)[0] == pytest.approx(60.0)
        assert x100.payoff(spot)[0] == pytest.approx(6000.0)


class TestNetPremium:
    """El flujo de caja del dia cero: lo que se paga o se cobra al abrir.

    Esta cuenta hoy vive suelta en app.py, adentro del metodo calculate() de
    la ventana. Es una regla del negocio de opciones y le corresponde al
    dominio. La UI la muestra bajo el nombre "P&L inicial".
    """

    def test_una_compra_es_debito(self):
        """Comprar cuesta plata: el flujo inicial es negativo."""
        s = Strategy([Leg("CALL", "COMPRA", 1, 1000, 40)])
        assert s.net_premium == pytest.approx(-40.0)

    def test_una_venta_es_credito(self):
        s = Strategy([Leg("CALL", "VENTA", 1, 1000, 40)])
        assert s.net_premium == pytest.approx(40.0)

    def test_iron_condor_cobra_credito_neto(self):
        """Golden master: -10 +20 +20 -10 = +20."""
        assert iron_condor().net_premium == pytest.approx(20.0)

    def test_el_multiplicador_tambien_lo_escala(self):
        s = Strategy([Leg("CALL", "COMPRA", 1, 1000, 40)], multiplier=100)
        assert s.net_premium == pytest.approx(-4000.0)


class TestContraLosValoresDeReferencia:
    """Los numeros que producia el codigo original, ya sin el codigo original.

    Durante la migracion este bloque importaba models.py y comparaba en vivo.
    Al eliminarlo en la Fase 6 esa comparacion dejo de ser posible, asi que
    los valores quedaron congelados en tests/golden_master.json.
    """

    def test_iron_condor_forma_de_la_curva(self, golden):
        caso = golden["plantillas"]["Iron Condor|x1"]
        precios = np.linspace(500, 1500, 401)
        pnl = iron_condor().payoff(precios)

        muestra = [float(pnl[i]) for i in range(0, 401, 50)]
        assert muestra == pytest.approx(caso["curva_muestra"], rel=1e-9)

    def test_iron_condor_credito_neto(self, golden):
        caso = golden["plantillas"]["Iron Condor|x1"]
        assert iron_condor().net_premium == pytest.approx(caso["net_premium"])
