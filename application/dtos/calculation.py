"""Objetos de entrada y salida del caso de uso de calculo."""

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from domain.entities.greeks import Greeks


@dataclass(frozen=True)
class PriceRange:
    """Sobre que rango de precios se dibuja la curva de P&L.

    Es un parametro de la consulta, no un concepto del negocio: describe
    cuanto se quiere ver a los costados del spot, no una regla de opciones.
    Por eso vive en la capa de aplicacion y no en el dominio.

    Los valores por defecto son los que trae la app hoy (app.py): de medio
    spot a spot y medio, con 401 puntos.
    """

    min_factor: float = 0.5
    max_factor: float = 1.5
    points: int = 401

    def __post_init__(self) -> None:
        if self.min_factor <= 0:
            raise ValueError(f"min_factor debe ser positivo, se recibio {self.min_factor}")
        if self.max_factor <= self.min_factor:
            raise ValueError(
                f"max_factor ({self.max_factor}) debe ser mayor que "
                f"min_factor ({self.min_factor})"
            )
        if self.points < 2:
            raise ValueError(f"Se necesitan al menos 2 puntos, se recibio {self.points}")

    def prices_around(self, spot: float) -> np.ndarray:
        return np.linspace(spot * self.min_factor, spot * self.max_factor, self.points)


@dataclass(frozen=True)
class CalculationResult:
    """Todo lo que la pantalla necesita mostrar de una estrategia.

    Es un objeto de transporte: agrupa lo que hoy app.calculate() arma en un
    diccionario suelto llamado `vals`. Sin esto, el caso de uso tendria que
    devolver una tupla de nueve elementos y quien la recibe tendria que
    acordarse del orden.
    """

    prices: np.ndarray
    pnl: np.ndarray
    greeks: Greeks
    net_premium: float
    max_pnl: float
    min_pnl: float
    breakevens: Sequence[float]
    profit_probability: float
    expected_pnl: float
