"""Strategy: el conjunto de patas que forman una posicion de opciones."""

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from domain.entities.greeks import Greeks
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

    def aggregate_greeks(self, per_leg: Sequence[Greeks]) -> Greeks:
        """Combina los griegos de cada pata en el total de la estrategia.

        Recibe una lista con un Greeks por pata, en el mismo orden que
        `self.legs`, y los pesa por cantidad con signo y multiplicador.

        Strategy hace este paso, y no Greeks, porque es quien conoce los pesos.
        Greeks solo sabe escalarse y sumarse; ignora que existen las patas.

        De donde salgan esos griegos no es asunto de este metodo: pueden venir
        de Black-Scholes, de un arbol binomial o de una simulacion. Esa
        indiferencia es el punto — la agregacion es del negocio, el calculo es
        del modelo.
        """
        if len(per_leg) != len(self.legs):
            raise ValueError(
                f"Se esperaba un Greeks por pata: hay {len(self.legs)} patas "
                f"y llegaron {len(per_leg)} griegos"
            )

        total = Greeks.zero()
        for leg, greeks in zip(self.legs, per_leg):
            total = total + greeks.scaled_by(leg.signed_quantity * self.multiplier)
        return total
