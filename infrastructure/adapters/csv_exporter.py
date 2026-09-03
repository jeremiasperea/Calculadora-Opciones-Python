"""Exportador a CSV."""

import csv
from pathlib import Path

from application.dtos.snapshot import SimulationSnapshot
from application.ports.exporter_port import ExporterPort


class CsvExporter(ExporterPort):
    """Escribe la curva de P&L como dos columnas.

    Usa el modulo csv de la biblioteca estandar. El codigo viejo armaba un
    DataFrame de pandas para esto — una dependencia de decenas de megabytes
    para escribir dos columnas que csv.writer resuelve en cuatro lineas.

    El formato es deliberadamente pobre: solo spot y P&L, sin metricas ni
    parametros. Un CSV es para llevar los numeros a una planilla y hacer otra
    cuenta; para guardar la simulacion completa esta el JSON.
    """

    @property
    def extension(self) -> str:
        return ".csv"

    @property
    def description(self) -> str:
        return "CSV (valores separados por comas)"

    def export(self, snapshot: SimulationSnapshot, destination: Path) -> None:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)

        # newline="" es lo que pide el modulo csv: sin eso, en Windows escribe
        # un salto de linea de mas entre filas.
        with destination.open("w", encoding="utf-8", newline="") as f:
            escritor = csv.writer(f)
            escritor.writerow(["Spot", "P&L"])
            for spot, pnl in zip(snapshot.result.prices, snapshot.result.pnl):
                escritor.writerow([f"{spot:.6f}", f"{pnl:.6f}"])
