"""Strategy: el conjunto de patas que forman una posicion de opciones."""

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from domain.entities.leg import Leg
from domain.value_objects.option_type import OptionType


@dataclass(frozen=True)
class Strategy:
    """Un conjunto de patas evaluadas como una sola posicion.

    Es el aggregate root del dominio: un "agregado" es un grupo de objetos que
    se trata como unidad. No tiene sentido mirar una pata de un iron condor por
    separado — el riesgo esta en como se combinan las cuatro. Por eso el resto
    del sistema le pide el payoff a la estrategia, nunca a la pata.

    Sobre numpy en el dominio: el dominio no depende de infraestructura, pero
    numpy no es infraestructura. No hace I/O, no habla con la red ni con una
    base: es una estructura de datos con operaciones vectorizadas, tan neutral
    como `list`. La regla real es "sin frameworks, sin I/O, sin base de datos",
    no "solo la biblioteca estandar". Calcular 401 puntos con loops de Python
    seria dos ordenes de magnitud mas lento sin ganar nada a cambio.

    El multiplicador vive aca y en ningun otro lado. Es una propiedad del
    contrato (100 para opciones sobre indices) y tenerlo en un solo lugar
    evita el bug que la prueba de mutacion de la Fase 0 dejo al descubierto:
    si tambien lo tomara el caso de uso, se aplicaria dos veces y el P&L
    saldria 100 veces mas grande.
    """

    legs: Sequence[Leg]
    multiplier: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "legs", tuple(self.legs))

        if not self.legs:
            raise ValueError("Una estrategia necesita al menos una pata")
        if self.multiplier <= 0:
            raise ValueError(
                f"El multiplicador debe ser positivo, se recibio {self.multiplier}"
            )

    def payoff(self, spot):
        """P&L al vencimiento para cada precio del subyacente.

        Acepta un escalar o un array y devuelve la misma forma.

        Al vencimiento la opcion vale solo su valor intrinseco: un call vale
        `max(spot - strike, 0)`, un put `max(strike - spot, 0)`. El P&L de la
        pata es ese valor menos la prima, por la cantidad con signo.

        Notar que no hace falta el `if leg.quantity:` que tenia el codigo
        viejo para saltear patas vacias: Leg garantiza quantity > 0, asi que
        una pata en cero no puede existir. Las invariantes borran chequeos
        defensivos rio abajo.
        """
        spot = np.asarray(spot, dtype=float)
        total = np.zeros_like(spot)

        for leg in self.legs:
            if leg.option_type is OptionType.CALL:
                intrinsic = np.maximum(spot - leg.strike, 0.0)
            else:
                intrinsic = np.maximum(leg.strike - spot, 0.0)
            total = total + leg.signed_quantity * (intrinsic - leg.premium)

        return total * self.multiplier

    @property
    def net_premium(self) -> float:
        """Flujo de caja al abrir la posicion: credito (+) o debito (-).

        Comprar cuesta plata, vender la cobra — o sea el signo opuesto al de
        signed_quantity, que mide exposicion y no caja.

        Esta cuenta estaba suelta dentro de app.calculate(), en la ventana de
        Tkinter. Es una regla del negocio de opciones y su lugar es el dominio.
        La UI la muestra con el nombre "P&L inicial".
        """
        return -sum(leg.signed_quantity * leg.premium for leg in self.legs) * self.multiplier
