"""Caso de uso: la biblioteca de simulaciones guardadas."""

from application.dtos.simulation import SavedSimulation, SimulationSummary
from application.dtos.snapshot import SimulationSnapshot
from application.ports.persistence_port import PersistencePort


class SimulationLibraryUseCase:
    """Guardar, abrir, listar y borrar las simulaciones del operador.

    Es un caso de uso con cuatro metodos y no cuatro casos de uso porque las
    cuatro operaciones son sobre el mismo recurso, comparten la misma
    dependencia y cambian por las mismas razones. Separarlas darian cuatro
    clases de cinco lineas que se construyen siempre juntas.

    La responsabilidad unica se mide por razones para cambiar, no por cantidad
    de metodos. Si manana guardar necesitara validar contra un limite de
    espacio y borrar necesitara pedir confirmacion, ahi tendria sentido
    separarlas.
    """

    def __init__(self, persistence: PersistencePort) -> None:
        self._persistence = persistence

    def save(self, name: str, snapshot: SimulationSnapshot) -> str:
        """Guarda una simulacion con el nombre que le dio el operador.

        El nombre es obligatorio: una simulacion sin nombre es imposible de
        encontrar despues en la lista. Se recortan los espacios de los
        extremos, que sobran siempre y no aportan nada.

        Los nombres repetidos se permiten. Prohibirlos obligaria al operador a
        inventar nombres unicos, que es trasladarle a el un problema del
        programa — para eso esta el identificador.
        """
        limpio = name.strip()
        if not limpio:
            raise ValueError("La simulacion necesita un nombre para poder encontrarla.")
        return self._persistence.save(limpio, snapshot)

    def load(self, sim_id: str) -> SavedSimulation:
        return self._persistence.load(sim_id)

    def list_all(self) -> list[SimulationSummary]:
        return self._persistence.list_all()

    def delete(self, sim_id: str) -> None:
        self._persistence.delete(sim_id)
