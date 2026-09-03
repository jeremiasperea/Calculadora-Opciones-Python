"""Configuracion de los tests de la API."""

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_library
from api.main import app
from application.use_cases.simulation_library import SimulationLibraryUseCase
from infrastructure.adapters.sqlite_persistence import SqlitePersistence


@pytest.fixture
def cliente(tmp_path):
    """Un cliente HTTP con base de datos propia.

    dependency_overrides es el mecanismo de FastAPI para reemplazar una
    dependencia en los tests. Sirve para lo mismo que pasar un doble al
    constructor en las otras capas: aislar el test del almacenamiento real.

    Que se pueda sustituir asi de facil es consecuencia de que la API dependa
    del caso de uso y no de SQLite directamente.
    """
    app.dependency_overrides[get_library] = lambda: SimulationLibraryUseCase(
        SqlitePersistence(tmp_path / "api_test.db")
    )
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


@pytest.fixture
def condor():
    """Pedido de un Iron Condor con los parametros por defecto."""
    return {
        "legs": [
            {"option_type": "PUT", "side": "COMPRA", "quantity": 1,
             "strike": 900, "premium": 10},
            {"option_type": "PUT", "side": "VENTA", "quantity": 1,
             "strike": 950, "premium": 20},
            {"option_type": "CALL", "side": "VENTA", "quantity": 1,
             "strike": 1050, "premium": 20},
            {"option_type": "CALL", "side": "COMPRA", "quantity": 1,
             "strike": 1100, "premium": 10},
        ],
        "market": {"spot": 1000, "days_to_expiry": 30,
                   "volatility": 0.35, "rate": 0.05},
        "multiplier": 1,
    }
