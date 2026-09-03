"""PersistencePort: contrato para guardar y recuperar simulaciones."""

from abc import ABC, abstractmethod

from application.dtos.simulation import SavedSimulation, SimulationSummary
from application.dtos.snapshot import SimulationSnapshot


class PersistencePort(ABC):
    """Lo que la aplicacion necesita de un almacenamiento de simulaciones.

    Este puerto no se escribio en la Fase 2 junto con los otros, porque
    transporta tipos que en ese momento no existian. Un contrato sobre un tipo
    inexistente es una conjetura sobre que datos van a hacer falta, y esa
    conjetura suele salir mal.

    La implementacion de la Fase 7 es SQLite. Nada en esta interfaz lo dice:
    no hay SQL, ni conexiones, ni transacciones. Si manana el operador quiere
    sus simulaciones en un servidor compartido, se escribe otro adaptador.
    """

    @abstractmethod
    def save(self, name: str, snapshot: SimulationSnapshot) -> str:
        """Guarda una simulacion y devuelve su identificador."""
        ...

    @abstractmethod
    def load(self, sim_id: str) -> SavedSimulation:
        """Recupera una simulacion completa. Lanza KeyError si no existe."""
        ...

    @abstractmethod
    def list_all(self) -> list[SimulationSummary]:
        """Resumenes de todas las simulaciones, de la mas reciente a la mas vieja.

        Devuelve resumenes y no simulaciones completas a proposito: la lista
        no necesita las curvas, y cargarlas seria traer miles de numeros para
        mostrar unas pocas columnas.
        """
        ...

    @abstractmethod
    def delete(self, sim_id: str) -> None:
        """Elimina una simulacion. Lanza KeyError si no existe."""
        ...
