"""Exportador a JSON."""

import json
from pathlib import Path

from application.dtos.snapshot import SimulationSnapshot
from application.ports.exporter_port import ExporterPort
from infrastructure.serialization.simulation_codec import FORMATO_VERSION, to_dict

class JsonExporter(ExporterPort):
    """Guarda la simulacion completa, en un formato que se puede releer.

    A diferencia del CSV, que solo lleva la curva a una planilla, este archivo
    es autocontenido: incluye las patas, los supuestos de mercado y el
    resultado. Con eso alcanza para reconstruir la simulacion tal cual, que es
    lo que lo hace util para guardar una idea y retomarla, o para pasarle una
    estrategia a otra persona.

    La conversion a diccionario la hace infrastructure/serialization, el
    mismo modulo que usa la persistencia en SQLite. Compartirlo mantiene un
    solo formato: un archivo exportado se puede volver a abrir, y una
    simulacion guardada en la base se puede exportar sin traducir nada.

    Se escribe indentado a proposito. Es un archivo que alguien puede querer
    abrir y revisar a mano; el ahorro de bytes de escribirlo en una linea no
    compensa volverlo ilegible.
    """

    @property
    def extension(self) -> str:
        return ".json"

    @property
    def description(self) -> str:
        return "JSON (simulacion completa, reimportable)"

    def export(self, snapshot: SimulationSnapshot, destination: Path) -> None:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(to_dict(snapshot), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
