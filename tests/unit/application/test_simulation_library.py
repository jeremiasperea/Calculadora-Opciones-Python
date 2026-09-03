"""Tests de la biblioteca de simulaciones.

Sobre por que es un caso de uso con cuatro metodos y no cuatro casos de uso:
guardar, abrir, listar y borrar son operaciones sobre el mismo recurso y
comparten la misma dependencia. Separarlas darian cuatro clases de cinco
lineas que se construyen siempre juntas y cambian siempre juntas. El
principio de responsabilidad unica habla de razones para cambiar, no de
cantidad de metodos.

Se prueba con un doble en memoria que implementa PersistencePort. Igual que
en la Fase 3: la logica de la biblioteca se verifica sin SQLite.
"""

from datetime import datetime

import pytest

from application.dtos.calculation import PriceRange
from application.dtos.simulation import SavedSimulation, SimulationSummary
from application.ports.persistence_port import PersistencePort
from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from application.dtos.snapshot import SimulationSnapshot
from application.use_cases.simulation_library import SimulationLibraryUseCase
from domain.entities.leg import Leg
from domain.entities.strategy import Strategy
from domain.value_objects.market_conditions import MarketConditions
from infrastructure.adapters.bsm_pricing import BSMPricingEngine


class PersistenciaFalsa(PersistencePort):
    """Guarda en un diccionario. Sin base, sin archivos, sin serializar."""

    def __init__(self):
        self._datos: dict[str, SavedSimulation] = {}
        self._contador = 0

    def save(self, name, snapshot):
        self._contador += 1
        sim_id = f"id-{self._contador}"
        self._datos[sim_id] = SavedSimulation(
            id=sim_id, name=name,
            created_at=datetime(2026, 9, 3, 10, self._contador),
            snapshot=snapshot,
        )
        return sim_id

    def load(self, sim_id):
        if sim_id not in self._datos:
            raise KeyError(sim_id)
        return self._datos[sim_id]

    def list_all(self):
        return [
            SimulationSummary(
                id=s.id, name=s.name, created_at=s.created_at,
                description=f"{len(s.snapshot.strategy.legs)} patas",
                net_premium=s.snapshot.result.net_premium,
            )
            for s in sorted(self._datos.values(),
                            key=lambda x: x.created_at, reverse=True)
        ]

    def delete(self, sim_id):
        if sim_id not in self._datos:
            raise KeyError(sim_id)
        del self._datos[sim_id]


@pytest.fixture
def snapshot():
    estrategia = Strategy([Leg("CALL", "COMPRA", 1, 1000, 40)])
    mercado = MarketConditions(spot=1000, days_to_expiry=30, volatility=0.35)
    resultado = CalculateStrategyUseCase(BSMPricingEngine()).execute(
        estrategia, mercado, PriceRange(0.9, 1.1, 21)
    )
    return SimulationSnapshot(estrategia, mercado, resultado)


@pytest.fixture
def biblioteca():
    return SimulationLibraryUseCase(PersistenciaFalsa())


class TestGuardar:
    def test_devuelve_un_identificador(self, biblioteca, snapshot):
        assert biblioteca.save("Mi condor", snapshot) == "id-1"

    def test_exige_un_nombre(self, biblioteca, snapshot):
        """Una simulacion sin nombre es imposible de encontrar despues."""
        for vacio in ["", "   ", "\t"]:
            with pytest.raises(ValueError, match="nombre"):
                biblioteca.save(vacio, snapshot)

    def test_recorta_los_espacios_del_nombre(self, biblioteca, snapshot):
        sim_id = biblioteca.save("  Condor de marzo  ", snapshot)
        assert biblioteca.load(sim_id).name == "Condor de marzo"

    def test_admite_nombres_repetidos(self, biblioteca, snapshot):
        """Dos simulaciones pueden llamarse igual: se distinguen por el id.

        Prohibirlo obligaria al operador a inventar nombres unicos, que es
        trabajo suyo para resolver un problema del programa.
        """
        primero = biblioteca.save("Prueba", snapshot)
        segundo = biblioteca.save("Prueba", snapshot)
        assert primero != segundo


class TestAbrir:
    def test_devuelve_lo_que_se_guardo(self, biblioteca, snapshot):
        sim_id = biblioteca.save("Mi condor", snapshot)
        recuperada = biblioteca.load(sim_id)

        assert recuperada.name == "Mi condor"
        assert recuperada.snapshot.result.net_premium == pytest.approx(
            snapshot.result.net_premium
        )

    def test_una_simulacion_inexistente_avisa(self, biblioteca):
        with pytest.raises(KeyError):
            biblioteca.load("id-inexistente")


class TestListar:
    def test_una_lista_vacia_al_principio(self, biblioteca):
        assert biblioteca.list_all() == []

    def test_devuelve_resumenes_no_simulaciones_completas(self, biblioteca, snapshot):
        """Listar no carga las curvas.

        Cada simulacion guarda 401 pares de numeros. Con cien simulaciones,
        armar la lista cargaria 80.000 valores para mostrar cinco columnas.
        El resumen trae solo lo que la lista necesita.
        """
        biblioteca.save("Uno", snapshot)
        resumen = biblioteca.list_all()[0]

        assert isinstance(resumen, SimulationSummary)
        assert not hasattr(resumen, "snapshot")

    def test_las_mas_recientes_primero(self, biblioteca, snapshot):
        biblioteca.save("Vieja", snapshot)
        biblioteca.save("Nueva", snapshot)
        assert [s.name for s in biblioteca.list_all()] == ["Nueva", "Vieja"]


class TestBorrar:
    def test_saca_la_simulacion_de_la_lista(self, biblioteca, snapshot):
        sim_id = biblioteca.save("Descartable", snapshot)
        biblioteca.delete(sim_id)
        assert biblioteca.list_all() == []

    def test_borrar_algo_inexistente_avisa(self, biblioteca):
        with pytest.raises(KeyError):
            biblioteca.delete("id-inexistente")


class TestIndependenciaDelAlmacenamiento:
    def test_la_biblioteca_no_sabe_donde_se_guarda(self, biblioteca, snapshot):
        """Todo este archivo corre sobre un diccionario en memoria.

        Ninguna de las pruebas de arriba toco SQLite, y sin embargo cubren el
        comportamiento completo de la biblioteca. Cambiar el almacenamiento
        por Postgres o por archivos sueltos no cambiaria una linea de estos
        tests ni del caso de uso.
        """
        sim_id = biblioteca.save("Prueba", snapshot)
        assert biblioteca.load(sim_id).name == "Prueba"
        assert len(biblioteca.list_all()) == 1
