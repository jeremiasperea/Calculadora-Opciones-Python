"""Punto de entrada: arma la aplicacion conectando todas las capas."""

from pathlib import Path

import flet as ft

from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from application.use_cases.export_strategy import ExportStrategyUseCase
from application.use_cases.load_template import LoadTemplateUseCase
from application.use_cases.simulation_library import SimulationLibraryUseCase
from infrastructure.adapters.bsm_pricing import BSMPricingEngine
from infrastructure.adapters.csv_exporter import CsvExporter
from infrastructure.adapters.excel_exporter import ExcelExporter
from infrastructure.adapters.json_exporter import JsonExporter
from infrastructure.adapters.pdf_exporter import PdfExporter
from infrastructure.adapters.sqlite_persistence import SqlitePersistence
from infrastructure.repositories.template_repository import InMemoryTemplateRepository
from ui.controllers.app_controller import AppController
from ui.views.main_view import MainView

TITULO = "Calculadora de Estrategias de Opciones"

# La base vive junto al codigo. Para una aplicacion local de un solo
# operador alcanza; si manana hiciera falta compartirla, cambia esta ruta
# o el adaptador entero, sin tocar nada mas.
BASE_DE_DATOS = Path(__file__).resolve().parent.parent / "simulaciones.db"


def build_controller(view: MainView, refrescar, base_de_datos=None) -> AppController:
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
        biblioteca=SimulationLibraryUseCase(
            SqlitePersistence(base_de_datos or BASE_DE_DATOS)
        ),
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

    # --- guardar una simulacion ---
    def abrir_dialogo_guardar(_):
        view.campo_nombre.value = ""
        view.campo_nombre.error_text = None
        page.show_dialog(view.dialogo_guardar)

    def confirmar_guardado(_):
        if controller.guardar_simulacion(view.campo_nombre.value or ""):
            page.pop_dialog()
        page.update()

    view.dialogo_guardar.actions = [
        ft.TextButton("Cancelar", on_click=lambda _: (page.pop_dialog(), page.update())),
        ft.Button("Guardar", on_click=confirmar_guardado),
    ]

    # --- biblioteca de simulaciones ---
    def refrescar_lista():
        view.set_simulaciones(
            controller.listar_simulaciones(),
            al_abrir=abrir_guardada,
            al_borrar=borrar_guardada,
        )

    def abrir_biblioteca(_):
        refrescar_lista()
        page.show_dialog(view.dialogo_biblioteca)

    def abrir_guardada(sim_id):
        controller.abrir_simulacion(sim_id)
        page.pop_dialog()
        page.update()

    def borrar_guardada(sim_id):
        controller.borrar_simulacion(sim_id)
        refrescar_lista()
        page.update()

    view.dialogo_biblioteca.actions = [
        ft.TextButton("Cerrar", on_click=lambda _: (page.pop_dialog(), page.update())),
    ]

    # --- conexion de eventos ---
    view.boton_calcular.on_click = lambda _: controller.calcular()
    view.boton_guardar.on_click = abrir_dialogo_guardar
    view.boton_biblioteca.on_click = abrir_biblioteca
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
