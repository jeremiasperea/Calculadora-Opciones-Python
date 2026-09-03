"""Punto de entrada: arma la aplicacion conectando todas las capas."""

from pathlib import Path

import flet as ft

from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from application.use_cases.export_strategy import ExportStrategyUseCase
from application.use_cases.load_template import LoadTemplateUseCase
from infrastructure.adapters.bsm_pricing import BSMPricingEngine
from infrastructure.adapters.csv_exporter import CsvExporter
from infrastructure.adapters.excel_exporter import ExcelExporter
from infrastructure.adapters.json_exporter import JsonExporter
from infrastructure.adapters.pdf_exporter import PdfExporter
from infrastructure.repositories.template_repository import InMemoryTemplateRepository
from ui.controllers.app_controller import AppController
from ui.views.main_view import MainView

TITULO = "Calculadora de Estrategias de Opciones"


def build_controller(view: MainView, refrescar) -> AppController:
    """Arma el controlador con todas sus dependencias.

    Este es el "composition root": el unico lugar del proyecto que menciona
    clases concretas de todas las capas juntas. Cambiar Black-Scholes por un
    arbol binomial, o las plantillas en memoria por una tabla de SQLite, se
    hace aca y en ningun otro lado.

    Separado de main() a proposito, para poder armar la aplicacion entera en
    un test sin levantar una ventana.
    """
    return AppController(
        view=view,
        calcular=CalculateStrategyUseCase(BSMPricingEngine()),
        cargar_plantilla=LoadTemplateUseCase(InMemoryTemplateRepository()),
        exportar=ExportStrategyUseCase([
            CsvExporter(), ExcelExporter(), JsonExporter(), PdfExporter(),
        ]),
        refrescar=refrescar,
    )


def main(page: ft.Page) -> None:
    page.title = TITULO
    page.padding = 0
    page.window.width = 1400
    page.window.height = 900

    view = MainView()
    controller = build_controller(view, page.update)

    # --- guardado de archivos ---
    selector_archivo = ft.FilePicker(
        on_result=lambda e: controller.exportar(Path(e.path)) if e.path else None
    )
    page.services.append(selector_archivo)

    def abrir_dialogo_guardar(_):
        extensiones = [ext.lstrip(".") for ext, _ in controller.formatos_de_exportacion()]
        selector_archivo.save_file(
            dialog_title="Exportar simulacion",
            file_name="estrategia.pdf",
            allowed_extensions=extensiones,
        )

    # --- conexion de eventos ---
    view.boton_calcular.on_click = lambda _: controller.calcular()
    view.boton_exportar.on_click = abrir_dialogo_guardar
    view.selector_plantilla.on_change = (
        lambda e: controller.cargar_plantilla(e.control.value)
    )

    page.add(
        ft.Container(
            content=ft.Row([
                ft.Text(TITULO, size=19, weight=ft.FontWeight.BOLD),
                view.selector_plantilla,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.Padding(left=14, right=14, top=10, bottom=4),
        ),
        ft.Divider(height=1),
        view.build(),
    )

    controller.inicializar()
    page.update()


if __name__ == "__main__":
    ft.run(main)
