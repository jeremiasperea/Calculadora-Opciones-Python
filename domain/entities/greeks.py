"""Greeks: las sensibilidades de una posicion de opciones."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Greeks:
    """Cuanto se mueve el valor de una posicion ante cada factor de riesgo.

    - delta: por cada punto que se mueve el subyacente
    - gamma: cuanto cambia el delta (la curvatura)
    - vega:  por cada punto porcentual de volatilidad
    - theta: por cada dia que pasa
    - rho:   por cada punto porcentual de tasa
    - value: el precio teorico de la posicion

    Lo que esta clase NO hace: calcularlos. Ese calculo depende del modelo de
    pricing (Black-Scholes hoy, quiza un arbol binomial manana) y vive en
    infrastructure/ detras del PricingPort. Aca solo se guardan y se combinan.

    Esa division es la razon de ser de la Fase 1. `delta = e^(-qT) * N(d1)` es
    una formula de un modelo particular. "El delta de una posicion vendida es
    el opuesto de la comprada" es una verdad del negocio, valga el modelo que
    valga. Solo la segunda pertenece al dominio.
    """

    value: float = 0.0
    delta: float = 0.0
    gamma: float = 0.0
    vega: float = 0.0
    theta: float = 0.0
    rho: float = 0.0

    @classmethod
    def zero(cls) -> Greeks:
        """El elemento neutro: punto de partida para acumular."""
        return cls()

    def scaled_by(self, factor: float) -> Greeks:
        """Todos los griegos multiplicados por el mismo factor.

        Con factor negativo se invierten los signos, que es justo lo que
        convierte una posicion comprada en una vendida.
        """
        return Greeks(
            value=self.value * factor,
            delta=self.delta * factor,
            gamma=self.gamma * factor,
            vega=self.vega * factor,
            theta=self.theta * factor,
            rho=self.rho * factor,
        )

    def __add__(self, other: Greeks) -> Greeks:
        """Suma campo a campo.

        Los griegos de una cartera son la suma de los de sus posiciones: son
        derivadas, y la derivada de una suma es la suma de las derivadas. Por
        eso escalar y sumar alcanzan para agregar cualquier estrategia.
        """
        if not isinstance(other, Greeks):
            return NotImplemented
        return Greeks(
            value=self.value + other.value,
            delta=self.delta + other.delta,
            gamma=self.gamma + other.gamma,
            vega=self.vega + other.vega,
            theta=self.theta + other.theta,
            rho=self.rho + other.rho,
        )
