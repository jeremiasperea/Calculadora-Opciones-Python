"""Armado de dependencias para la API.

Es el composition root de esta capa, el equivalente de build_controller() en
ui/main.py. Cada adaptador de entrada arma su propio grafo de objetos: la API
no reutiliza el de Flet ni al reves, porque cada uno decide sus propias
configuraciones — por ejemplo, la API podria apuntar a otra base.

Lo que si comparten son los casos de uso y todo lo que esta debajo. Ese es el
punto: dos interfaces distintas sobre exactamente la misma logica.
"""

from functools import lru_cache
from pathlib import Path

from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from application.use_cases.load_template import LoadTemplateUseCase
from application.use_cases.simulation_library import SimulationLibraryUseCase
from infrastructure.adapters.bsm_pricing import BSMPricingEngine
from infrastructure.adapters.sqlite_persistence import SqlitePersistence
from infrastructure.repositories.template_repository import InMemoryTemplateRepository

BASE_DE_DATOS = Path(__file__).resolve().parent.parent / "simulaciones.db"


@lru_cache
def get_calculate() -> CalculateStrategyUseCase:
    """El motor de valuacion no tiene estado: una instancia alcanza."""
    return CalculateStrategyUseCase(BSMPricingEngine())


@lru_cache
def get_templates() -> LoadTemplateUseCase:
    return LoadTemplateUseCase(InMemoryTemplateRepository())


@lru_cache
def get_library() -> SimulationLibraryUseCase:
    """La biblioteca abre una conexion por operacion, asi que compartir la
    instancia entre pedidos es seguro."""
    return SimulationLibraryUseCase(SqlitePersistence(BASE_DE_DATOS))
