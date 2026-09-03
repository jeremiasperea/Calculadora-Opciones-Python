"""Caso de uso: exportar una simulacion a un archivo."""

from pathlib import Path
from typing import Sequence

from application.dtos.snapshot import SimulationSnapshot
from application.ports.exporter_port import ExporterPort


class ExportStrategyUseCase:
    """Guarda una simulacion en el formato que indique la extension.

    Recibe todos los exportadores disponibles y elige segun el archivo que
    pidio el operador. Ese mapeo vive aca y no en la interfaz por una razon
    concreta: es una decision de la aplicacion, no de como se ve la pantalla.
    Si estuviera en la UI, agregar un formato obligaria a tocarla, y una
    segunda interfaz (la API de la Fase 8) tendria que repetir la misma
    tabla.

    La UI solo pregunta available_formats() para armar el dialogo de guardado.
    No conoce ningun formato por nombre.
    """

    def __init__(self, exporters: Sequence[ExporterPort]) -> None:
        if not exporters:
            raise ValueError("Se necesita al menos un exportador")

        por_extension: dict[str, ExporterPort] = {}
        for exporter in exporters:
            ext = exporter.extension.lower()
            if ext in por_extension:
                raise ValueError(
                    f"Hay dos exportadores para {ext}. Cual gana dependeria del "
                    "orden de la lista, asi que se rechaza."
                )
            por_extension[ext] = exporter

        self._por_extension = por_extension
        self._orden = list(exporters)

    def available_formats(self) -> list[tuple[str, str]]:
        """Pares (extension, descripcion) para el dialogo de guardado."""
        return [(e.extension, e.description) for e in self._orden]

    def execute(self, snapshot: SimulationSnapshot, destination: Path) -> None:
        destination = Path(destination)
        ext = destination.suffix.lower()

        if ext not in self._por_extension:
            disponibles = ", ".join(sorted(self._por_extension))
            raise ValueError(
                f"No hay exportador para {ext or '(sin extension)'}. "
                f"Formatos disponibles: {disponibles}"
            )

        self._por_extension[ext].export(snapshot, destination)
