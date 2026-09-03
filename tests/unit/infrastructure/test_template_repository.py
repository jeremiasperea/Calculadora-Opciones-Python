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


class TestContraElCatalogoOriginal:
    """Las plantillas son las mismas que traia strategies.py."""

    def test_estan_todas(self, golden):
        esperadas = {clave.split("|")[0] for clave in golden["plantillas"]}
        assert set(InMemoryTemplateRepository().list_names()) == esperadas

    def test_las_patas_coinciden(self, golden):
        repo = InMemoryTemplateRepository()
        for clave, caso in golden["plantillas"].items():
            if not clave.endswith("|x1"):
                continue
            nombre = clave.split("|")[0]
            patas = repo.get_template(nombre).legs

            assert len(patas) == len(caso["patas"]), nombre
            for pata, esperada in zip(patas, caso["patas"]):
                assert pata.option_type.value == esperada["option_type"]
                assert pata.side.value == esperada["side"]
                assert pata.quantity == esperada["quantity"]
                assert pata.strike == esperada["strike"]
                assert pata.premium == esperada["premium"]
