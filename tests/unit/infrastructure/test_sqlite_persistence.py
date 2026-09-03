"""Tests del almacenamiento en SQLite.

Los tests de la biblioteca (tests/unit/application/) ya cubren el
comportamiento usando un diccionario en memoria. Aca se verifica lo que solo
puede fallar en la implementacion real: que la tabla se cree, que los datos
sobrevivan a cerrar el programa, que el JSON se guarde y se lea bien.

Se usa un archivo temporal y no :memory: en la mayoria de los tests, porque
lo que importa verificar es justamente la persistencia entre conexiones.
"""

from datetime import datetime

import pytest

from application.dtos.calculation import PriceRange
from application.dtos.snapshot import SimulationSnapshot
from application.ports.persistence_port import PersistencePort
from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from domain.entities.leg import Leg
from domain.entities.strategy import Strategy
from domain.value_objects.market_conditions import MarketConditions
from infrastructure.adapters.bsm_pricing import BSMPricingEngine
from infrastructure.adapters.sqlite_persistence import SqlitePersistence


@pytest.fixture
def snapshot():
    estrategia = Strategy([
        Leg("PUT", "COMPRA", 1, 900, 10),
        Leg("PUT", "VENTA", 1, 950, 20),
        Leg("CALL", "VENTA", 1, 1050, 20),
        Leg("CALL", "COMPRA", 1, 1100, 10),
    ], multiplier=100)
    mercado = MarketConditions(spot=1000, days_to_expiry=30,
                               volatility=0.35, rate=0.05)
    resultado = CalculateStrategyUseCase(BSMPricingEngine()).execute(
        estrategia, mercado, PriceRange(0.5, 1.5, 401)
    )
    return SimulationSnapshot(estrategia, mercado, resultado)


@pytest.fixture
def base(tmp_path):
    return SqlitePersistence(tmp_path / "simulaciones.db")


class TestCumpleElContrato:
    def test_es_un_persistence_port(self, base):
        assert isinstance(base, PersistencePort)

    def test_crea_la_base_al_construirse(self, tmp_path):
        """No hace falta un paso de instalacion aparte."""
        ruta = tmp_path / "sub" / "nueva.db"
        SqlitePersistence(ruta)
        assert ruta.exists()

    def test_abrir_una_base_existente_no_la_borra(self, tmp_path, snapshot):
        ruta = tmp_path / "x.db"
        sim_id = SqlitePersistence(ruta).save("Antes", snapshot)

        otra = SqlitePersistence(ruta)
        assert otra.load(sim_id).name == "Antes"


class TestPersistencia:
    def test_los_datos_sobreviven_a_cerrar_el_programa(self, tmp_path, snapshot):
        """Lo unico que esta implementacion agrega sobre un diccionario.

        Se guarda con una instancia y se lee con otra, que es lo que pasa
        cuando el operador cierra la aplicacion y la vuelve a abrir.
        """
        ruta = tmp_path / "x.db"
        sim_id = SqlitePersistence(ruta).save("Condor de marzo", snapshot)

        recuperada = SqlitePersistence(ruta).load(sim_id)
        assert recuperada.name == "Condor de marzo"
        assert recuperada.snapshot.result.net_premium == pytest.approx(2000.0)

    def test_la_simulacion_vuelve_completa(self, base, snapshot):
        import numpy as np

        sim_id = base.save("Completa", snapshot)
        vuelta = base.load(sim_id).snapshot

        assert len(vuelta.strategy.legs) == 4
        assert vuelta.strategy.multiplier == 100
        assert vuelta.market == snapshot.market
        np.testing.assert_allclose(vuelta.result.pnl, snapshot.result.pnl)
        assert vuelta.result.greeks == snapshot.result.greeks


class TestListado:
    def test_vacio_al_principio(self, base):
        assert base.list_all() == []

    def test_trae_los_datos_del_resumen(self, base, snapshot):
        base.save("Mi condor", snapshot)
        resumen = base.list_all()[0]

        assert resumen.name == "Mi condor"
        assert resumen.net_premium == pytest.approx(2000.0)
        assert "4 patas" in resumen.description
        assert isinstance(resumen.created_at, datetime)

    def test_las_mas_recientes_primero(self, base, snapshot):
        for nombre in ["Primera", "Segunda", "Tercera"]:
            base.save(nombre, snapshot)
        assert [s.name for s in base.list_all()] == ["Tercera", "Segunda", "Primera"]

    def test_listar_no_carga_las_curvas(self, base, snapshot):
        """El resumen no tiene el snapshot: por eso listar es barato."""
        base.save("Uno", snapshot)
        assert not hasattr(base.list_all()[0], "snapshot")


class TestBorrado:
    def test_saca_la_simulacion(self, base, snapshot):
        sim_id = base.save("Descartable", snapshot)
        base.delete(sim_id)

        assert base.list_all() == []
        with pytest.raises(KeyError):
            base.load(sim_id)

    def test_borrar_algo_inexistente_avisa(self, base):
        """SQLite no protesta si el DELETE no afecta filas.

        Sin este chequeo, borrar dos veces la misma simulacion pareceria
        exitoso las dos veces y la interfaz no tendria como saber que la
        segunda no hizo nada.
        """
        with pytest.raises(KeyError):
            base.delete("id-inexistente")

    def test_borrar_una_no_afecta_a_las_otras(self, base, snapshot):
        a = base.save("A", snapshot)
        base.save("B", snapshot)
        base.delete(a)

        assert [s.name for s in base.list_all()] == ["B"]


class TestIdentificadores:
    def test_cada_simulacion_tiene_uno_distinto(self, base, snapshot):
        ids = {base.save(f"Sim {i}", snapshot) for i in range(10)}
        assert len(ids) == 10

    def test_admite_nombres_repetidos(self, base, snapshot):
        a = base.save("Prueba", snapshot)
        b = base.save("Prueba", snapshot)

        assert a != b
        assert len(base.list_all()) == 2


class TestErrores:
    def test_abrir_una_simulacion_inexistente_avisa(self, base):
        with pytest.raises(KeyError, match="inexistente"):
            base.load("inexistente")
