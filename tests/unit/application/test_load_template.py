"""Tests del caso de uso de carga de plantillas."""

import pytest

from application.ports.strategy_port import StrategyPort
from application.use_cases.load_template import LoadTemplateUseCase
from domain.entities.leg import Leg
from domain.entities.strategy import Strategy


class RepoFalso(StrategyPort):
    """Catalogo en memoria con dos plantillas."""

    def __init__(self):
        self._data = {
            "Long Call": Strategy([Leg("CALL", "COMPRA", 1, 1050, 30)]),
            "Bull Call Spread": Strategy([
                Leg("CALL", "COMPRA", 1, 1000, 40),
                Leg("CALL", "VENTA", 1, 1100, 15),
            ]),
        }

    def list_names(self):
        return list(self._data)

    def get_template(self, name):
        return self._data[name]


class TestLoadTemplate:
    def test_lista_las_plantillas_disponibles(self):
        uc = LoadTemplateUseCase(RepoFalso())
        assert uc.list_available() == ["Long Call", "Bull Call Spread"]

    def test_devuelve_la_plantilla_pedida(self):
        uc = LoadTemplateUseCase(RepoFalso())
        s = uc.execute("Bull Call Spread")
        assert len(s.legs) == 2
        assert s.legs[0].strike == 1000
        assert s.legs[1].strike == 1100

    def test_una_plantilla_inexistente_lanza_error(self):
        """Se propaga el KeyError en lugar de devolver None.

        Un None se arrastra hasta que alguien lo desreferencia, tres capas mas
        abajo, con un mensaje que no dice nada del nombre que se pidio.
        """
        uc = LoadTemplateUseCase(RepoFalso())
        with pytest.raises(KeyError):
            uc.execute("Estrategia Inexistente")

    def test_el_caso_de_uso_no_conoce_el_origen(self):
        """El mismo caso de uso sirve con cualquier repositorio.

        Hoy las plantillas son un diccionario. Manana pueden ser un JSON que
        edita el operador o una tabla de SQLite: cambia el adaptador, no esto.
        """

        class RepoVacio(StrategyPort):
            def list_names(self):
                return []

            def get_template(self, name):
                raise KeyError(name)

        assert LoadTemplateUseCase(RepoVacio()).list_available() == []
