"""Tests del caso de uso de exportacion."""

from pathlib import Path

import pytest

from application.dtos.snapshot import SimulationSnapshot
from application.ports.exporter_port import ExporterPort
from application.use_cases.export_strategy import ExportStrategyUseCase


class ExportadorFalso(ExporterPort):
    def __init__(self, ext, desc="falso"):
        self._ext, self._desc = ext, desc
        self.exportados = []

    @property
    def extension(self):
        return self._ext

    @property
    def description(self):
        return self._desc

    def export(self, snapshot, destination):
        self.exportados.append(destination)


SNAPSHOT = SimulationSnapshot(strategy=None, market=None, result=None)


class TestSeleccionPorExtension:
    def test_elige_el_exportador_que_corresponde(self):
        csv_, json_ = ExportadorFalso(".csv"), ExportadorFalso(".json")
        uc = ExportStrategyUseCase([csv_, json_])

        uc.execute(SNAPSHOT, Path("/tmp/x.json"))

        assert len(json_.exportados) == 1
        assert len(csv_.exportados) == 0

    def test_la_extension_no_distingue_mayusculas(self):
        """El operador puede escribir 'REPORTE.CSV' en el dialogo."""
        csv_ = ExportadorFalso(".csv")
        ExportStrategyUseCase([csv_]).execute(SNAPSHOT, Path("/tmp/REPORTE.CSV"))
        assert len(csv_.exportados) == 1

    def test_una_extension_desconocida_dice_cuales_sirven(self):
        """El mensaje enumera lo disponible.

        'Formato no soportado' obliga a ir a leer el codigo. Decir cuales hay
        resuelve el problema en el mismo mensaje.
        """
        uc = ExportStrategyUseCase([ExportadorFalso(".csv"), ExportadorFalso(".json")])
        with pytest.raises(ValueError, match=r"\.csv"):
            uc.execute(SNAPSHOT, Path("/tmp/x.pptx"))

    def test_un_archivo_sin_extension_falla(self):
        uc = ExportStrategyUseCase([ExportadorFalso(".csv")])
        with pytest.raises(ValueError):
            uc.execute(SNAPSHOT, Path("/tmp/sin_extension"))


class TestCatalogoDeFormatos:
    def test_lista_los_formatos_disponibles(self):
        """La UI arma el dialogo de guardado con esto, sin conocer los
        formatos ni tener que actualizarse cuando se agrega uno."""
        uc = ExportStrategyUseCase([
            ExportadorFalso(".csv", "CSV (planilla)"),
            ExportadorFalso(".json", "JSON (reimportable)"),
        ])
        assert uc.available_formats() == [
            (".csv", "CSV (planilla)"),
            (".json", "JSON (reimportable)"),
        ]


class TestConstruccion:
    def test_necesita_al_menos_un_exportador(self):
        with pytest.raises(ValueError, match="exportador"):
            ExportStrategyUseCase([])

    def test_rechaza_dos_exportadores_para_la_misma_extension(self):
        """Sin esto, cual gana dependeria del orden de la lista.

        Es el tipo de ambiguedad que no rompe nada al principio y despues
        cuesta una tarde entender por que se exporta distinto.
        """
        with pytest.raises(ValueError, match="\\.csv"):
            ExportStrategyUseCase([ExportadorFalso(".csv"), ExportadorFalso(".csv")])
