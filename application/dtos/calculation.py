"""Objetos de entrada y salida del caso de uso de calculo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

import numpy as np

from domain.entities.greeks import Greeks

# Cuanto se muestra mas alla del strike mas lejano, para que se vea que la
# curva sigue y no parezca que termina ahi.
MARGEN_POR_DEFECTO = 0.10

if TYPE_CHECKING:
    from domain.entities.strategy import Strategy


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

    @classmethod
    def auto(
        cls,
        strategy: "Strategy",
        spot: float,
        margen: float = MARGEN_POR_DEFECTO,
        points: int = 401,
    ) -> "PriceRange":
        """Rango que cubre todos los strikes y el spot, con un margen.

        El rango fijo de 0.5x a 1.5x alcanza mientras los strikes esten cerca
        del precio actual. Deja de alcanzar apenas alguien carga uno lejano:
        con spot 1000 y un strike en 1500, la curva se corta justo en el punto
        donde la estrategia cambia de forma.

        El spot entra en la cuenta ademas de los strikes. Sin eso, una
        estrategia con todos los strikes muy por encima del precio actual
        dibujaria una curva que no incluye donde esta el subyacente hoy, que
        es la referencia principal de quien mira el grafico.

        El margen se aplica a cada extremo, para que se vea que pasa mas alla
        del ultimo strike y no quede la impresion de que la curva termina ahi.
        """
        strikes = [leg.strike for leg in strategy.legs]
        minimo = min(min(strikes), spot) * (1.0 - margen)
        maximo = max(max(strikes), spot) * (1.0 + margen)

        # Con margen cero y un unico strike igual al spot, los dos extremos
        # coincidirian y el grafico tendria ancho nulo.
        if maximo <= minimo:
            minimo, maximo = spot * 0.99, spot * 1.01

        return cls(minimo / spot, maximo / spot, points)

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
