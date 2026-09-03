"""Repositorio de plantillas en memoria."""

from application.ports.strategy_port import StrategyPort
from domain.entities.strategy import Strategy
from infrastructure.config.templates import PLANTILLAS


class InMemoryTemplateRepository(StrategyPort):
    """Sirve las plantillas del catalogo fijo.

    Se llama "in memory" porque hoy las plantillas son un diccionario en el
    codigo. El nombre anticipa que va a haber otras implementaciones: una que
    lea un JSON editable por el operador, o una que las guarde en SQLite junto
    con las simulaciones de la Fase 7.

    El multiplicador se recibe al construir el repositorio y se aplica a todas
    las plantillas que devuelve. Es una propiedad del contrato que opera cada
    uno —100 para opciones sobre indices, 1 para acciones— y no de la
    estrategia, asi que no tiene sentido guardarlo en el catalogo.
    """

    def __init__(self, multiplier: float = 1.0) -> None:
        self._multiplier = multiplier

    def list_names(self) -> list[str]:
        return list(PLANTILLAS)

    def get_template(self, name: str) -> Strategy:
        if name not in PLANTILLAS:
            raise KeyError(
                f"No existe la plantilla {name!r}. "
                f"Disponibles: {', '.join(PLANTILLAS)}"
            )
        return Strategy(PLANTILLAS[name], multiplier=self._multiplier)
