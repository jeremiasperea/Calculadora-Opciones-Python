"""ExporterPort: contrato para escribir una simulacion a un archivo."""

from abc import ABC, abstractmethod
from pathlib import Path

from application.dtos.snapshot import SimulationSnapshot


class ExporterPort(ABC):
    """Lo que la aplicacion necesita para exportar una simulacion.

    Hay una implementacion por formato en vez de una sola con un `if formato`
    adentro. Asi agregar un formato nuevo es escribir una clase, sin tocar las
    que ya andan — el principio abierto/cerrado en concreto.

    Este puerto no se escribio en la Fase 2 junto con los otros dos, porque
    transporta un SimulationSnapshot y ese tipo todavia no existia. Un contrato
    sobre un tipo inexistente es una conjetura.
    """

    @property
    @abstractmethod
    def extension(self) -> str:
        """Extension que maneja, con punto: '.csv', '.json'.

        Sirve para que el caso de uso elija el exportador segun el archivo que
        pidio el operador, sin que la UI tenga que conocer los formatos.
        """
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Descripcion legible, para el dialogo de guardado."""
        ...

    @abstractmethod
    def export(self, snapshot: SimulationSnapshot, destination: Path) -> None:
        """Escribe la simulacion en el archivo indicado."""
        ...
