"""Objetos de una simulacion guardada."""

from dataclasses import dataclass
from datetime import datetime

from application.dtos.snapshot import SimulationSnapshot


@dataclass(frozen=True)
class SavedSimulation:
    """Una simulacion recuperada del almacenamiento.

    Es un SimulationSnapshot mas los datos que aparecen al guardarlo: un
    identificador, el nombre que le puso el operador y cuando se guardo.

    Esos tres campos son de la aplicacion y no del dominio. El negocio de
    opciones no sabe nada de guardar cosas; "esta idea la evalue el martes y
    la llame condor de marzo" es una preocupacion de quien usa el programa.
    Por eso vive aca y no en domain/, y por eso agregar persistencia no obligo
    a tocar el dominio.
    """

    id: str
    name: str
    created_at: datetime
    snapshot: SimulationSnapshot


@dataclass(frozen=True)
class SimulationSummary:
    """Los datos de una simulacion que necesita una lista, y nada mas.

    Existe por una razon de tamano. Cada simulacion guarda la curva completa:
    401 precios y 401 resultados. Con cien simulaciones, armar la lista
    cargaria ochenta mil numeros para mostrar cinco columnas.

    El resumen trae lo que la lista muestra. La simulacion completa se carga
    recien cuando el operador abre una.
    """

    id: str
    name: str
    created_at: datetime
    description: str
    net_premium: float
