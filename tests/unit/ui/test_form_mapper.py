"""Tests del traductor entre el formulario y el dominio.

Es la unica parte de la interfaz con logica que valga la pena probar. Todo lo
demas —crear controles, acomodarlos, pintar— es codigo mecanico: si esta mal,
se ve al abrir la aplicacion.

Su trabajo tiene dos mitades:

1. Convertir texto a numeros. Todo lo que llega de un formulario es texto,
   incluso lo que parece un numero.

2. Traducir errores. El operador no programa: 'could not convert string to
   float: abc' no le dice nada. 'El strike de la pata 2 no es un numero
   valido' le dice exactamente que arreglar.

La segunda mitad es la razon de que esta capa exista. Sin ella, las
excepciones del dominio llegarian crudas a la pantalla.
"""

import pytest

from domain.value_objects.option_type import OptionType
from domain.value_objects.position_side import PositionSide
from ui.mappers.form_mapper import FormError, LegForm, MarketForm, to_market, to_strategy


def pata(tipo="CALL", lado="COMPRA", cantidad="1", strike="1000", prima="40"):
    return LegForm(option_type=tipo, side=lado, quantity=cantidad,
                   strike=strike, premium=prima)


def mercado(spot="1000", vol="35", tasa="5", div="0", dias="30", mult="1"):
    return MarketForm(spot=spot, volatility_pct=vol, rate_pct=tasa,
                      dividend_pct=div, days="30" if dias is None else dias,
                      multiplier=mult)


class TestMercado:
    def test_convierte_los_porcentajes(self):
        """El operador escribe 35, no 0.35.

        Pensar la volatilidad en porcentaje es como se habla en la mesa. Pedir
        0.35 traslada a la pantalla una convencion que solo existe adentro de
        las formulas.
        """
        m = to_market(mercado(vol="35", tasa="5", div="2"))
        assert m.volatility == pytest.approx(0.35)
        assert m.rate == pytest.approx(0.05)
        assert m.dividend_yield == pytest.approx(0.02)

    def test_acepta_coma_decimal(self):
        """En la region se escribe 1.234,50 y no 1,234.50."""
        m = to_market(mercado(spot="1234,50", vol="35,5"))
        assert m.spot == pytest.approx(1234.50)
        assert m.volatility == pytest.approx(0.355)

    def test_acepta_el_simbolo_de_porcentaje(self):
        assert to_market(mercado(vol="35%")).volatility == pytest.approx(0.35)

    def test_admite_tasa_negativa(self):
        assert to_market(mercado(tasa="-0,5")).rate == pytest.approx(-0.005)

    def test_un_campo_vacio_avisa_cual(self):
        with pytest.raises(FormError, match="[Ss]pot"):
            to_market(mercado(spot=""))

    def test_texto_donde_va_un_numero_avisa_cual(self):
        with pytest.raises(FormError, match="[Vv]olatilidad"):
            to_market(mercado(vol="mucha"))

    def test_traduce_los_errores_del_dominio(self):
        """Una invariante del dominio llega como mensaje entendible.

        MarketConditions rechaza spot <= 0 con un ValueError. Que ese texto
        llegue crudo a la pantalla seria filtrar la implementacion a la cara
        del operador.
        """
        with pytest.raises(FormError, match="mayor que cero"):
            to_market(mercado(spot="-100"))


class TestPatas:
    def test_arma_la_estrategia(self):
        s = to_strategy([pata(strike="1000"), pata(lado="VENTA", strike="1100")],
                        multiplier=1.0)
        assert len(s.legs) == 2
        assert s.legs[0].option_type is OptionType.CALL
        assert s.legs[1].side is PositionSide.VENTA

    def test_descarta_las_filas_vacias(self):
        """La pantalla tiene seis filas y casi nunca se usan todas.

        Filtrar es responsabilidad de esta capa: el dominio rechaza una pata
        con cantidad cero porque no es una posicion. La grilla de seis es una
        decision de pantalla y no tiene por que ensuciar el modelo.
        """
        s = to_strategy([pata(), pata(cantidad="0"), pata(cantidad="")],
                        multiplier=1.0)
        assert len(s.legs) == 1

    def test_todas_las_filas_vacias_avisa(self):
        with pytest.raises(FormError, match="al menos una pata"):
            to_strategy([pata(cantidad="0"), pata(cantidad="")], multiplier=1.0)

    def test_un_error_dice_en_que_fila_esta(self):
        """Con seis filas iguales, 'strike invalido' obliga a revisarlas todas."""
        with pytest.raises(FormError, match="[Pp]ata 2"):
            to_strategy([pata(), pata(strike="mil")], multiplier=1.0)

    def test_traduce_las_invariantes_del_dominio(self):
        with pytest.raises(FormError, match="[Pp]ata 1"):
            to_strategy([pata(strike="-1000")], multiplier=1.0)

    def test_aplica_el_multiplicador(self):
        assert to_strategy([pata()], multiplier=100).multiplier == 100


class TestNumeracionParaElOperador:
    def test_las_filas_se_cuentan_desde_uno(self):
        """La primera fila de la pantalla es la 1, no la 0.

        El indice base cero es una convencion de programacion. Mostrarselo a
        quien opera es filtrar un detalle de implementacion.
        """
        with pytest.raises(FormError, match="[Pp]ata 1"):
            to_strategy([pata(strike="x")], multiplier=1.0)

    def test_cuenta_las_filas_visibles_no_las_validas(self):
        """Si la fila 2 esta vacia y la 3 tiene un error, dice 'pata 3'.

        Numerar solo las filas con datos diria 'pata 2' y mandaria al operador
        a mirar la fila equivocada.
        """
        with pytest.raises(FormError, match="[Pp]ata 3"):
            to_strategy([pata(), pata(cantidad="0"), pata(strike="x")],
                        multiplier=1.0)


class TestRedaccionDeLosMensajes:
    """Detalles que hacen que el mensaje se lea como una frase.

    Son cosas chicas, pero es lo unico que el operador ve cuando algo sale
    mal. Un dialogo que dice 'la volatilidad: alta no es un numero valido'
    parece un volcado de log; 'La volatilidad: ...' parece que alguien lo
    escribio para el.
    """

    def test_empiezan_en_mayuscula(self):
        for construir in [
            lambda: to_market(mercado(vol="alta")),
            lambda: to_strategy([pata(), pata(strike="x")], 1.0),
            lambda: to_market(mercado(spot="")),
        ]:
            with pytest.raises(FormError) as e:
                construir()
            assert str(e.value)[0].isupper(), str(e.value)

    def test_terminan_con_punto(self):
        with pytest.raises(FormError) as e:
            to_market(mercado(spot=""))
        assert str(e.value).endswith(".")
