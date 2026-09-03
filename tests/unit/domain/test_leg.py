"""Tests de Leg: una pata individual de una estrategia.

Sobre como se llama esta capa: Leg vive en `entities/` siguiendo el plan,
pero en este dominio se comporta como un Value Object — es inmutable y dos
patas con los mismos datos son equivalentes. La distincion Entity/VO no es
dogma: depende del dominio. En un sistema de trading real, cada pata tendria
un ID de orden, un estado (abierta/cerrada) y fills parciales, y ahi seria
una Entity de verdad. En una calculadora, es un descriptor inmutable.

Lo que si aporta de "Entity" es la idea central de esta fase: **invariantes**.
Una entidad se valida a si misma en el momento de construirse, asi que nunca
existe en estado invalido. No hace falta que quien la use se acuerde de
chequear nada.
"""

import pytest

from domain.entities.leg import Leg
from domain.value_objects.option_type import OptionType
from domain.value_objects.position_side import PositionSide


class TestConstruccion:
    def test_se_construye_con_value_objects(self):
        leg = Leg(OptionType.CALL, PositionSide.COMPRA, 1, 1000, 40)
        assert leg.option_type is OptionType.CALL
        assert leg.side is PositionSide.COMPRA

    def test_acepta_strings_y_los_convierte(self):
        """Compatibilidad hacia atras.

        strategies.py y app.py construyen patas con strings posicionales.
        Leg los convierte a value objects al construirse, asi que ese codigo
        sigue andando mientras se migra por fases — pero ahora un typo falla.
        """
        leg = Leg("CALL", "COMPRA", 1, 1000, 40)
        assert leg.option_type is OptionType.CALL
        assert leg.side is PositionSide.COMPRA

    def test_un_tipo_invalido_falla(self):
        with pytest.raises(ValueError):
            Leg("CAL", "COMPRA", 1, 1000, 40)

    def test_un_lado_invalido_falla(self):
        with pytest.raises(ValueError):
            Leg("CALL", "compra", 1, 1000, 40)


class TestInvariantes:
    """Reglas que Leg garantiza siempre, por el solo hecho de existir."""

    def test_el_strike_debe_ser_positivo(self):
        for strike in [0, -1, -1000]:
            with pytest.raises(ValueError, match="strike"):
                Leg("CALL", "COMPRA", 1, strike, 40)

    def test_la_cantidad_debe_ser_positiva(self):
        """La cantidad es una magnitud: el signo lo pone el lado.

        Permitir quantity=-5 con side=COMPRA daria dos formas de escribir la
        misma posicion (esa, y quantity=5 con side=VENTA). Dos representaciones
        del mismo estado es una fuente de bugs de signo, asi que se elige una.

        Ojo con la Fase 5: la UI tiene 6 slots y los vacios valen 0. Filtrarlos
        es responsabilidad del mapper de la UI, no del dominio. Una pata con
        cantidad cero no es una posicion.
        """
        for cantidad in [0, -1, -5]:
            with pytest.raises(ValueError, match="cantidad"):
                Leg("CALL", "COMPRA", cantidad, 1000, 40)

    def test_la_prima_no_puede_ser_negativa(self):
        with pytest.raises(ValueError, match="prima"):
            Leg("CALL", "COMPRA", 1, 1000, -40)

    def test_la_prima_puede_ser_cero(self):
        """Cero es valido: sirve para aislar el payoff del costo en un test."""
        assert Leg("CALL", "COMPRA", 1, 1000, 0).premium == 0


class TestSignedQuantity:
    """El unico comportamiento de Leg: cuanto suma o resta a la posicion."""

    def test_compra_es_positiva(self):
        assert Leg("CALL", "COMPRA", 3, 1000, 40).signed_quantity == 3

    def test_venta_es_negativa(self):
        assert Leg("CALL", "VENTA", 3, 1000, 40).signed_quantity == -3

    def test_usa_el_signo_del_lado(self):
        """Delega en PositionSide.sign en vez de repetir el if.

        Si manana se agrega un lado nuevo, se toca un solo lugar.
        """
        for side in PositionSide:
            leg = Leg("CALL", side, 2, 1000, 40)
            assert leg.signed_quantity == 2 * side.sign


class TestInmutabilidad:
    def test_no_se_puede_modificar(self):
        """Inmutable a proposito.

        Las invariantes se chequean al construir. Si despues se pudiera hacer
        `leg.strike = -1`, esa validacion seria un chequeo inicial y no una
        garantia. Frozen convierte "estaba bien cuando la cree" en "esta bien
        siempre". Una pata no se modifica: se reemplaza.
        """
        leg = Leg("CALL", "COMPRA", 1, 1000, 40)
        with pytest.raises(Exception):
            leg.strike = 2000

    def test_dos_patas_iguales_son_equivalentes(self):
        a = Leg("CALL", "COMPRA", 1, 1000, 40)
        b = Leg("CALL", "COMPRA", 1, 1000, 40)
        assert a == b
