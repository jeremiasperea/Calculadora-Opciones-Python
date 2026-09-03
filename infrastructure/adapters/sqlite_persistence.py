"""Almacenamiento de simulaciones en SQLite."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from application.dtos.simulation import SavedSimulation, SimulationSummary
from application.dtos.snapshot import SimulationSnapshot
from application.ports.persistence_port import PersistencePort
from infrastructure.serialization.simulation_codec import from_dict, to_dict

ESQUEMA = """
CREATE TABLE IF NOT EXISTS simulations (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    description TEXT NOT NULL,
    net_premium REAL NOT NULL,
    payload     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_created_at ON simulations(created_at DESC);
"""


class SqlitePersistence(PersistencePort):
    """Guarda las simulaciones en un archivo SQLite local.

    Sobre el diseno de la tabla: la simulacion completa vive serializada en la
    columna `payload`, pero `description` y `net_premium` estan repetidos como
    columnas propias. Esa duplicacion es deliberada.

    Sin ella, armar la lista obligaria a leer y parsear el JSON de cada
    simulacion —401 pares de numeros cada uno— para mostrar dos campos. Con
    cien simulaciones guardadas eso son ochenta mil valores procesados para
    dibujar una tabla. Guardar los dos campos aparte hace que listar toque
    solo columnas chicas.

    Es un caso donde desnormalizar esta bien: los datos duplicados no cambian
    nunca, porque una simulacion guardada es un registro historico y no se
    edita. La duplicacion se vuelve peligrosa cuando las dos copias pueden
    divergir, y aca no pueden.

    Se abre una conexion por operacion en lugar de mantener una viva. Para una
    aplicacion local con pocas simulaciones el costo es despreciable, y evita
    los problemas de compartir una conexion entre hilos —Flet puede llamar
    desde uno distinto al que creo el objeto.
    """

    def __init__(self, ruta: Path | str) -> None:
        self._ruta = Path(ruta)
        self._ruta.parent.mkdir(parents=True, exist_ok=True)
        with self._conectar() as conexion:
            conexion.executescript(ESQUEMA)

    def _conectar(self) -> sqlite3.Connection:
        conexion = sqlite3.connect(self._ruta)
        conexion.row_factory = sqlite3.Row
        return conexion

    def save(self, name: str, snapshot: SimulationSnapshot) -> str:
        sim_id = str(uuid.uuid4())
        # En UTC y en formato ISO: ordena bien como texto, que es lo que
        # permite que el indice sirva sin convertir nada.
        creado = datetime.now(timezone.utc).isoformat()

        with self._conectar() as conexion:
            conexion.execute(
                "INSERT INTO simulations "
                "(id, name, created_at, description, net_premium, payload) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    sim_id,
                    name,
                    creado,
                    self._describir(snapshot),
                    float(snapshot.result.net_premium),
                    json.dumps(to_dict(snapshot)),
                ),
            )
        return sim_id

    def load(self, sim_id: str) -> SavedSimulation:
        with self._conectar() as conexion:
            fila = conexion.execute(
                "SELECT id, name, created_at, payload FROM simulations WHERE id = ?",
                (sim_id,),
            ).fetchone()

        if fila is None:
            raise KeyError(f"No existe la simulacion {sim_id!r}")

        return SavedSimulation(
            id=fila["id"],
            name=fila["name"],
            created_at=datetime.fromisoformat(fila["created_at"]),
            snapshot=from_dict(json.loads(fila["payload"])),
        )

    def list_all(self) -> list[SimulationSummary]:
        with self._conectar() as conexion:
            filas = conexion.execute(
                "SELECT id, name, created_at, description, net_premium "
                "FROM simulations ORDER BY created_at DESC"
            ).fetchall()

        return [
            SimulationSummary(
                id=f["id"],
                name=f["name"],
                created_at=datetime.fromisoformat(f["created_at"]),
                description=f["description"],
                net_premium=f["net_premium"],
            )
            for f in filas
        ]

    def delete(self, sim_id: str) -> None:
        with self._conectar() as conexion:
            cursor = conexion.execute("DELETE FROM simulations WHERE id = ?", (sim_id,))
            # SQLite no protesta si el DELETE no afecta ninguna fila. Sin este
            # chequeo, borrar dos veces la misma simulacion pareceria exitoso
            # las dos veces y la interfaz no tendria como saberlo.
            if cursor.rowcount == 0:
                raise KeyError(f"No existe la simulacion {sim_id!r}")

    def _describir(self, snapshot: SimulationSnapshot) -> str:
        """Resumen corto para la lista: cuantas patas y de que tipo."""
        patas = snapshot.strategy.legs
        tipos = {leg.option_type.value for leg in patas}
        composicion = "/".join(sorted(tipos))
        return f"{len(patas)} patas · {composicion}"
