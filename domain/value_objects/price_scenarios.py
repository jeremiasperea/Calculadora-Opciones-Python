"""PriceScenarios: precios futuros posibles, con su probabilidad."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PriceScenarios:
    """Una distribucion de precios futuros del subyacente.

    - prices:    los precios que podria tener el subyacente al vencimiento
    - densities: cuan probable es cada uno
    - grid:      la variable sobre la que se integra

    El tercer campo es el menos obvio. Estas densidades no estan definidas
    sobre el precio sino sobre otra variable — en el modelo lognormal, sobre
    la normal estandar z. Integrar sobre la grilla correcta es lo que hace que
    las probabilidades sumen uno; hacerlo sobre `prices` daria otro numero,
    porque el mapeo de z a precio no es lineal.

    Las densidades deben integrar a 1 sobre la grilla, como cualquier
    distribucion de probabilidad. No se valida — con 20.001 puntos la
    integral numerica nunca da exactamente 1, y elegir una tolerancia
    seria arbitrario. Es responsabilidad de quien construye los escenarios.

    Quien construye estos escenarios es el adaptador de pricing: la forma de
    la distribucion es un supuesto del modelo. El dominio los recibe armados y
    solo integra, sin saber si salieron de una lognormal, de un arbol o de una
    simulacion con saltos.
    """

    prices: np.ndarray
    densities: np.ndarray
    grid: np.ndarray

    def __post_init__(self) -> None:
        object.__setattr__(self, "prices", np.asarray(self.prices, dtype=float))
        object.__setattr__(self, "densities", np.asarray(self.densities, dtype=float))
        object.__setattr__(self, "grid", np.asarray(self.grid, dtype=float))

        n = len(self.prices)
        if len(self.densities) != n or len(self.grid) != n:
            raise ValueError(
                "prices, densities y grid deben tener la misma longitud: "
                f"{n}, {len(self.densities)}, {len(self.grid)}"
            )
