"""Tests del codec de simulaciones.

Un codec es un par de funciones inversas: una convierte el objeto a un
diccionario plano, la otra lo reconstruye. La propiedad que debe cumplir es
que aplicarlas en secuencia devuelva lo mismo que entro — lo que se llama
round-trip.

Vale la pena que exista por tres motivos que aparecieron por separado:

1. El JsonExporter ya hacia la mitad (to_dict) para escribir el archivo.
2. La Fase 7 necesita la misma serializacion para guardar en SQLite.
3. Reimportar un archivo exportado requiere la mitad que faltaba (from_dict).

Escribir la vuelta completa resuelve las tres de una vez. Si cada una hubiera
armado su propia serializacion, un cambio de formato habria que hacerlo en
tres lugares y el que se olvidara se rompe en silencio.
"""

import pytest

from application.dtos.calculation import PriceRange
from application.dtos.snapshot import SimulationSnapshot
from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from domain.entities.leg import Leg
from domain.entities.strategy import Strategy
from domain.value_objects.market_conditions import MarketConditions
from infrastructure.adapters.bsm_pricing import BSMPricingEngine
from infrastructure.serialization.simulation_codec import (
    FORMATO_VERSION, FormatoDesconocido, from_dict, to_dict,
)


@pytest.fixture
def snapshot():
    estrategia = Strategy([
        Leg("CALL", "COMPRA", 1, 1000, 40),
        Leg("PUT", "VENTA", 2, 950, 25),
    ], multiplier=100)
    mercado = MarketConditions(spot=1000, days_to_expiry=30,
                               volatility=0.35, rate=0.05, dividend_yield=0.02)
    resultado = CalculateStrategyUseCase(BSMPricingEngine()).execute(
        estrategia, mercado, PriceRange(0.8, 1.2, 51)
    )
    return SimulationSnapshot(estrategia, mercado, resultado)


class TestIdaYVuelta:
    """La propiedad central: convertir y reconstruir no pierde nada."""

    def test_la_estrategia_vuelve_igual(self, snapshot):
        vuelta = from_dict(to_dict(snapshot))

        assert len(vuelta.strategy.legs) == 2
        assert vuelta.strategy.multiplier == 100
        for original, reconstruida in zip(snapshot.strategy.legs, vuelta.strategy.legs):
            assert reconstruida.option_type == original.option_type
            assert reconstruida.side == original.side
            assert reconstruida.quantity == original.quantity
            assert reconstruida.strike == original.strike
            assert reconstruida.premium == original.premium

    def test_el_mercado_vuelve_igual(self, snapshot):
        vuelta = from_dict(to_dict(snapshot))
        assert vuelta.market == snapshot.market

    def test_el_resultado_vuelve_igual(self, snapshot):
        import numpy as np

        vuelta = from_dict(to_dict(snapshot))
        r, o = vuelta.result, snapshot.result

        assert r.net_premium == pytest.approx(o.net_premium)
        assert r.max_pnl == pytest.approx(o.max_pnl)
        assert r.min_pnl == pytest.approx(o.min_pnl)
        assert list(r.breakevens) == pytest.approx(list(o.breakevens))
        assert r.profit_probability == pytest.approx(o.profit_probability)
        assert r.greeks == o.greeks
        np.testing.assert_allclose(r.prices, o.prices)
        np.testing.assert_allclose(r.pnl, o.pnl)

    def test_dos_vueltas_dan_lo_mismo_que_una(self, snapshot):
        """Idempotencia: el formato es estable, no se degrada al reprocesarlo."""
        una = to_dict(snapshot)
        dos = to_dict(from_dict(una))
        assert una == dos


class TestFormatoPlano:
    """El diccionario resultante tiene que poder guardarse tal cual."""

    def test_es_serializable_a_json(self, snapshot):
        import json

        texto = json.dumps(to_dict(snapshot))
        assert json.loads(texto) == to_dict(snapshot)

    def test_los_enums_salen_como_texto(self, snapshot):
        """json no serializa enums, y guardar 'OptionType.CALL' romperia la lectura."""
        datos = to_dict(snapshot)
        assert datos["strategy"]["legs"][0]["option_type"] == "CALL"
        assert isinstance(datos["strategy"]["legs"][0]["option_type"], str)

    def test_los_arrays_salen_como_listas(self, snapshot):
        datos = to_dict(snapshot)
        assert isinstance(datos["result"]["curve"]["prices"], list)
        assert isinstance(datos["result"]["curve"]["prices"][0], float)


class TestVersionado:
    def test_lleva_el_numero_de_version(self, snapshot):
        assert to_dict(snapshot)["version"] == FORMATO_VERSION

    def test_rechaza_una_version_que_no_conoce(self, snapshot):
        """Mejor negarse que leer mal.

        Un archivo de una version futura puede tener campos con otro
        significado. Intentar leerlo igual produciria una simulacion
        silenciosamente equivocada, que es peor que no abrirla.
        """
        datos = to_dict(snapshot)
        datos["version"] = 99
        with pytest.raises(FormatoDesconocido, match="99"):
            from_dict(datos)

    def test_un_archivo_sin_version_falla_con_un_mensaje_claro(self, snapshot):
        datos = to_dict(snapshot)
        del datos["version"]
        with pytest.raises(FormatoDesconocido):
            from_dict(datos)


class TestArchivosCorruptos:
    def test_falta_un_campo_obligatorio(self, snapshot):
        datos = to_dict(snapshot)
        del datos["strategy"]
        with pytest.raises(FormatoDesconocido, match="strategy"):
            from_dict(datos)

    def test_una_pata_invalida_se_rechaza(self, snapshot):
        """Las invariantes del dominio siguen valiendo al leer.

        Un archivo editado a mano con strike negativo no puede convertirse en
        un Leg. Que falle aca es correcto: el dominio no acepta datos malos
        vengan de donde vengan.
        """
        datos = to_dict(snapshot)
        datos["strategy"]["legs"][0]["strike"] = -100
        with pytest.raises(ValueError):
            from_dict(datos)
