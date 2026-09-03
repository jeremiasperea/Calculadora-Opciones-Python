"""SimulationSnapshot: una simulacion completa, lista para guardar o exportar."""

from dataclasses import dataclass

from application.dtos.calculation import CalculationResult
from domain.entities.strategy import Strategy
from domain.value_objects.market_conditions import MarketConditions


@dataclass(frozen=True)
class SimulationSnapshot:
    """Que se calculo, con que supuestos, y que dio.

    Junta las tres piezas que hacen falta para que una simulacion se entienda
    sola: la estrategia, las condiciones de mercado y el resultado. Un
    resultado sin sus supuestos no dice nada — "probabilidad de beneficio
    52%" es inutil si no se sabe con que volatilidad se calculo.

    Aparecio al disenar la exportacion, por el mismo motivo que
    MarketConditions aparecio al disenar PricingPort: las firmas empezaban a
    llevar tres parametros que siempre viajan juntos.

    Es tambien lo que la Fase 7 va a guardar en SQLite. Diseniarlo ahora evita
    tener dos objetos casi iguales, uno para exportar y otro para persistir.
    """

    strategy: Strategy
    market: MarketConditions
    result: CalculationResult
