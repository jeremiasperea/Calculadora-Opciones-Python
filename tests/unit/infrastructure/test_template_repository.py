"""Tests del repositorio de plantillas."""

import pytest

from application.ports.strategy_port import StrategyPort
from infrastructure.repositories.template_repository import InMemoryTemplateRepository


class TestCumpleElContrato:
    def test_es_un_strategy_port(self):
        assert isinstance(InMemoryTemplateRepository(), StrategyPort)


class TestCatalogo:
    def test_trae_las_once_plantillas(self):
        assert len(InMemoryTemplateRepository().list_names()) == 11

    def test_incluye_las_conocidas(self):
        nombres = InMemoryTemplateRepository().list_names()
        for esperada in ["Long Call", "Iron Condor", "Butterfly Call"]:
            assert esperada in nombres

    def test_devuelve_una_estrategia_armada(self):
        s = InMemoryTemplateRepository().get_template("Iron Condor")
        assert len(s.legs) == 4
        assert s.net_premium == pytest.approx(20.0)

    def test_una_plantilla_inexistente_lista_las_disponibles(self):
        """El mensaje de error dice que si existe.

        Un KeyError pelado obliga a ir a leer el codigo para saber que se
        podia pedir.
        """
        with pytest.raises(KeyError, match="Long Call"):
            InMemoryTemplateRepository().get_template("Mariposa Invertida")


class TestMultiplicador:
    def test_por_defecto_es_uno(self):
        s = InMemoryTemplateRepository().get_template("Long Call")
        assert s.multiplier == 1.0

    def test_se_aplica_a_las_plantillas(self):
        s = InMemoryTemplateRepository(multiplier=100).get_template("Iron Condor")
        assert s.multiplier == 100
        assert s.net_premium == pytest.approx(2000.0)


class TestEquivalenciaConStrategiesPy:
    def test_mismas_plantillas_que_el_catalogo_viejo(self):
        from strategies import TEMPLATES

        repo = InMemoryTemplateRepository()
        assert set(repo.list_names()) == set(TEMPLATES)

        for nombre, patas_viejas in TEMPLATES.items():
            nuevas = repo.get_template(nombre).legs
            assert len(nuevas) == len(patas_viejas), nombre
            for nueva, vieja in zip(nuevas, patas_viejas):
                assert nueva.option_type == vieja.option_type
                assert nueva.side == vieja.side
                assert nueva.quantity == vieja.quantity
                assert nueva.strike == vieja.strike
                assert nueva.premium == vieja.premium
