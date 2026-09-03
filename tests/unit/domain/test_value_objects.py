"""Tests de los value objects del dominio: OptionType y PositionSide.

Un Value Object no tiene identidad: se define por su valor. Dos OptionType.CALL
son la misma cosa, igual que dos billetes de $100 son intercambiables. Eso lo
distingue de una Entity como Leg, donde dos patas con los mismos datos siguen
siendo dos posiciones distintas en la cartera.

Por que existen estos dos: hoy el tipo y el lado son strings sueltos, y un typo
("CAL" en vez de "CALL") no falla — el codigo lo trata como PUT y devuelve un
numero equivocado sin avisar. Estos VOs mueven ese error al momento de la
construccion, que es donde se puede ver.
"""

import pytest

from domain.value_objects.option_type import OptionType
from domain.value_objects.position_side import PositionSide


class TestOptionType:
    def test_valores_validos(self):
        assert OptionType.CALL.value == "CALL"
        assert OptionType.PUT.value == "PUT"

    def test_construir_desde_string(self):
        assert OptionType("CALL") is OptionType.CALL
        assert OptionType("PUT") is OptionType.PUT

    def test_un_valor_invalido_falla_al_construir(self):
        """LA razon de ser de este value object.

        Hoy Leg("CAL", ...) se construye sin protestar y el payoff sale mal.
        Aca el error aparece en el momento de crear el dato, no tres capas
        mas abajo disfrazado de resultado.
        """
        for invalido in ["CAL", "call", "Call", "", "CALLS", "OPTION"]:
            with pytest.raises(ValueError):
                OptionType(invalido)

    def test_compatible_con_string(self):
        """Hereda de str a proposito.

        Durante la migracion queda codigo que compara con strings crudos
        (models.py hace `leg.option_type == "CALL"`). Heredar de str deja que
        ese codigo siga funcionando mientras se mueve por fases, en vez de
        obligar a cambiar todo de una.
        """
        assert OptionType.CALL == "CALL"
        assert OptionType.CALL != "PUT"

    def test_igualdad_por_valor(self):
        """Es un Value Object: se compara por valor, no por identidad."""
        assert OptionType("CALL") == OptionType.CALL

    def test_es_inmutable(self):
        with pytest.raises(AttributeError):
            OptionType.CALL.value = "PUT"


class TestPositionSide:
    def test_valores_validos(self):
        assert PositionSide.COMPRA.value == "COMPRA"
        assert PositionSide.VENTA.value == "VENTA"

    def test_construir_desde_string(self):
        assert PositionSide("COMPRA") is PositionSide.COMPRA
        assert PositionSide("VENTA") is PositionSide.VENTA

    def test_un_valor_invalido_falla_al_construir(self):
        """Este es el mas peligroso de los dos.

        Un lado mal escrito no cambia un poco el resultado: le da vuelta el
        signo. Una posicion comprada pasa a contarse como vendida y el P&L
        sale con el signo invertido.
        """
        for invalido in ["compra", "Compra", "COMPRAR", "BUY", "", "VENDA"]:
            with pytest.raises(ValueError):
                PositionSide(invalido)

    def test_compatible_con_string(self):
        assert PositionSide.COMPRA == "COMPRA"
        assert PositionSide.COMPRA != "VENTA"

    def test_es_inmutable(self):
        with pytest.raises(AttributeError):
            PositionSide.COMPRA.value = "VENTA"

    def test_sign_devuelve_el_signo_de_la_posicion(self):
        """Comprar suma, vender resta.

        Este signo vive en PositionSide y no en Leg porque es propiedad del
        lado en si mismo: vale igual para una opcion, un futuro o una accion.
        Leg lo consume para calcular su cantidad con signo.
        """
        assert PositionSide.COMPRA.sign == 1
        assert PositionSide.VENTA.sign == -1
