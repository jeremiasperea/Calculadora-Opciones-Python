"""Tests del controlador.

Se prueba con la vista real (construir controles de Flet no necesita una
ventana) y con casos de uso reales. Lo unico que se reemplaza es `refrescar`,
que en produccion es page.update() y aca es una funcion que cuenta llamadas.

Que se verifica: que lea bien el formulario, que llame a quien corresponde y
que escriba el resultado donde va. No se verifica que los numeros esten bien
—eso ya lo cubren las fases 1 a 4— sino que lleguen a la pantalla.
"""

from pathlib import Path

import pytest

from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from application.use_cases.export_strategy import ExportStrategyUseCase
from application.use_cases.load_template import LoadTemplateUseCase
from application.use_cases.simulation_library import SimulationLibraryUseCase
from infrastructure.adapters.bsm_pricing import BSMPricingEngine
from infrastructure.adapters.csv_exporter import CsvExporter
from infrastructure.adapters.json_exporter import JsonExporter
from infrastructure.adapters.sqlite_persistence import SqlitePersistence
from infrastructure.repositories.template_repository import InMemoryTemplateRepository
from ui.controllers.app_controller import AppController
from ui.views.main_view import MainView


class Refresco:
    """Reemplaza a page.update(): cuenta cuantas veces se pidio repintar."""

    def __init__(self):
        self.veces = 0

    def __call__(self):
        self.veces += 1


@pytest.fixture
def entorno(tmp_path):
    """Cada test recibe una base vacia propia.

    Sin tmp_path los tests compartirian la base real de la aplicacion: se
    ensuciaria con datos de prueba y el orden de ejecucion cambiaria los
    resultados.
    """
    vista = MainView()
    refresco = Refresco()
    controlador = AppController(
        view=vista,
        calcular=CalculateStrategyUseCase(BSMPricingEngine()),
        cargar_plantilla=LoadTemplateUseCase(InMemoryTemplateRepository()),
        exportar=ExportStrategyUseCase([CsvExporter(), JsonExporter()]),
        biblioteca=SimulationLibraryUseCase(SqlitePersistence(tmp_path / "test.db")),
        refrescar=refresco,
    )
    return vista, controlador, refresco


class TestInicializacion:
    def test_carga_el_catalogo_y_muestra_la_primera(self, entorno):
        vista, controlador, _ = entorno
        controlador.inicializar()

        assert len(vista.selector_plantilla.options) == 11
        assert vista.selector_plantilla.value == "Long Call"
        # Y ya calculo: las metricas no estan en su valor inicial
        assert vista.metricas["Delta"].value != "—"


class TestCargarPlantilla:
    def test_escribe_las_patas_en_la_grilla(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Iron Condor")

        assert vista.filas_patas[0]["option_type"].value == "PUT"
        assert vista.filas_patas[0]["strike"].value == "900"
        assert vista.filas_patas[3]["option_type"].value == "CALL"
        assert vista.filas_patas[3]["strike"].value == "1100"

    def test_limpia_las_filas_que_sobran(self, entorno):
        """De una plantilla de cuatro patas a una de una.

        Sin limpiar, quedarian las tres de la anterior y la estrategia
        calculada no seria la que se ve en pantalla.
        """
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Iron Condor")
        controlador.cargar_plantilla("Long Call")

        assert vista.filas_patas[0]["quantity"].value == "1"
        for fila in vista.filas_patas[1:]:
            assert fila["quantity"].value == "0"

    def test_una_plantilla_inexistente_avisa(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Mariposa Invertida")
        assert "no se encontro" in vista.mensaje.value.lower()


class TestCalcular:
    def test_pinta_las_metricas(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Iron Condor")

        assert vista.metricas["P&L inicial"].value == "20.00"
        assert vista.metricas["Ganancia maxima"].value == "20.00"
        assert vista.metricas["Perdida maxima"].value == "-30.00"
        assert vista.metricas["Break-even"].value == "930.00, 1,070.00"

    def test_la_probabilidad_va_en_porcentaje(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Iron Condor")
        assert vista.metricas["Prob. de beneficio"].value.endswith("%")

    def test_pinta_el_grafico(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Long Call")
        assert vista.grafico.src.startswith("data:image/png;base64,")
        assert len(vista.grafico.src) > 5000  # hay una imagen de verdad

    def test_carga_la_tabla_de_escenarios(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Long Call")
        assert 50 < len(vista.tabla_escenarios.rows) <= 70

    def test_la_perdida_va_en_rojo_y_la_ganancia_en_verde(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Iron Condor")
        assert vista.metricas["Perdida maxima"].color == "#c62828"
        assert vista.metricas["Ganancia maxima"].color == "#2e7d32"

    def test_un_dato_mal_cargado_muestra_el_mensaje(self, entorno):
        vista, controlador, _ = entorno
        vista.campos_mercado["spot"].value = "mil"
        controlador.calcular()

        assert "spot" in vista.mensaje.value.lower()
        assert "no es un numero" in vista.mensaje.value.lower()

    def test_sin_ninguna_pata_avisa(self, entorno):
        vista, controlador, _ = entorno
        controlador.calcular()  # la grilla arranca toda en cero
        assert "al menos una pata" in vista.mensaje.value.lower()

    def test_un_calculo_bueno_limpia_el_mensaje_anterior(self, entorno):
        vista, controlador, _ = entorno
        controlador.calcular()
        assert vista.mensaje.value != ""

        controlador.cargar_plantilla("Long Call")
        assert vista.mensaje.value == ""


class TestExportar:
    def test_exportar_sin_calcular_avisa(self, entorno, tmp_path):
        vista, controlador, _ = entorno
        controlador.exportar(tmp_path / "x.csv")
        assert "calcule antes" in vista.mensaje.value.lower()

    def test_escribe_el_archivo(self, entorno, tmp_path):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Iron Condor")

        destino = tmp_path / "condor.json"
        controlador.exportar(destino)

        assert destino.exists()
        assert "exportado" in vista.mensaje.value.lower()

    def test_un_formato_desconocido_avisa(self, entorno, tmp_path):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Long Call")
        controlador.exportar(tmp_path / "x.pptx")
        assert "no hay exportador" in vista.mensaje.value.lower()

    def test_ofrece_los_formatos_disponibles(self, entorno):
        _, controlador, _ = entorno
        assert [e for e, _ in controlador.formatos_de_exportacion()] == [".csv", ".json"]


class TestRepintado:
    def test_pide_repintar_despues_de_calcular(self, entorno):
        _, controlador, refresco = entorno
        controlador.cargar_plantilla("Long Call")
        assert refresco.veces >= 1

    def test_pide_repintar_tambien_cuando_hay_error(self, entorno):
        """Si no, el mensaje de error queda escrito pero no se ve."""
        _, controlador, refresco = entorno
        antes = refresco.veces
        controlador.calcular()  # falla: no hay patas
        assert refresco.veces > antes


class TestCompositionRoot:
    """La aplicacion se arma entera sin levantar una ventana.

    Que esto se pueda testear es consecuencia de haber separado build_controller
    de main(): el cableado de dependencias queda verificable, y solo lo que
    necesita una ventana de verdad —eventos, layout— queda fuera de los tests.
    """

    def test_arma_el_controlador_completo(self, tmp_path):
        from ui.main import build_controller

        vista = MainView()
        controlador = build_controller(vista, lambda: None, tmp_path / "t.db")
        controlador.inicializar()

        assert len(vista.selector_plantilla.options) == 11
        assert vista.metricas["Delta"].value != "—"

    def test_ofrece_los_cuatro_formatos(self, tmp_path):
        from ui.main import build_controller

        formatos = build_controller(
            MainView(), lambda: None, tmp_path / "t.db"
        ).formatos_de_exportacion()
        assert [e for e, _ in formatos] == [".csv", ".xlsx", ".json", ".pdf"]

    def test_calcula_el_iron_condor_de_punta_a_punta(self, tmp_path):
        """Del formulario al archivo exportado, con todo real."""
        from ui.main import build_controller

        vista = MainView()
        controlador = build_controller(vista, lambda: None, tmp_path / "t.db")
        controlador.inicializar()
        controlador.cargar_plantilla("Iron Condor")

        assert vista.metricas["P&L inicial"].value == "20.00"

        destino = tmp_path / "condor.pdf"
        controlador.exportar(destino)
        assert destino.read_bytes()[:5] == b"%PDF-"


class TestSimulacionesGuardadas:
    def test_guardar_sin_calcular_avisa(self, entorno):
        vista, controlador, _ = entorno
        assert controlador.guardar_simulacion("Prueba") is False
        assert "calcule antes" in vista.mensaje.value.lower()

    def test_guardar_sin_nombre_avisa(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Long Call")
        assert controlador.guardar_simulacion("   ") is False
        assert "nombre" in vista.mensaje.value.lower()

    def test_guarda_y_aparece_en_la_lista(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Iron Condor")

        assert controlador.guardar_simulacion("Condor de marzo") is True
        assert "guardado" in vista.mensaje.value.lower()

        lista = controlador.listar_simulaciones()
        assert len(lista) == 1
        assert lista[0].name == "Condor de marzo"
        assert lista[0].net_premium == pytest.approx(20.0)

    def test_abrir_restaura_el_formulario(self, entorno):
        """Guardar con unos parametros, cambiarlos, abrir y ver que vuelven."""
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Iron Condor")
        vista.campos_mercado["volatility_pct"].value = "42"
        controlador.calcular()
        controlador.guardar_simulacion("Con volatilidad 42")

        # Se cambia todo
        controlador.cargar_plantilla("Long Call")
        vista.campos_mercado["volatility_pct"].value = "20"
        controlador.calcular()

        # Y se abre la guardada
        sim_id = controlador.listar_simulaciones()[0].id
        controlador.abrir_simulacion(sim_id)

        assert vista.campos_mercado["volatility_pct"].value == "42"
        assert vista.filas_patas[0]["strike"].value == "900"
        assert len([f for f in vista.filas_patas if f["quantity"].value != "0"]) == 4

    def test_abrir_recalcula(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Iron Condor")
        controlador.guardar_simulacion("Condor")

        sim_id = controlador.listar_simulaciones()[0].id
        controlador.abrir_simulacion(sim_id)

        assert vista.metricas["P&L inicial"].value == "20.00"
        assert "abierta" in vista.mensaje.value.lower()

    def test_borrar_la_saca_de_la_lista(self, entorno):
        _, controlador, _ = entorno
        controlador.cargar_plantilla("Long Call")
        controlador.guardar_simulacion("Descartable")

        sim_id = controlador.listar_simulaciones()[0].id
        controlador.borrar_simulacion(sim_id)

        assert controlador.listar_simulaciones() == []

    def test_abrir_algo_borrado_avisa(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Long Call")
        controlador.guardar_simulacion("Efimera")
        sim_id = controlador.listar_simulaciones()[0].id
        controlador.borrar_simulacion(sim_id)

        controlador.abrir_simulacion(sim_id)
        assert "ya no existe" in vista.mensaje.value.lower()

    def test_los_nombres_repetidos_conviven(self, entorno):
        _, controlador, _ = entorno
        controlador.cargar_plantilla("Long Call")
        controlador.guardar_simulacion("Prueba")
        controlador.guardar_simulacion("Prueba")

        lista = controlador.listar_simulaciones()
        assert len(lista) == 2
        assert lista[0].id != lista[1].id


class TestEscalaDelGrafico:
    """El rango que se dibuja, automatico o cargado a mano."""

    def _cargar_strike_lejano(self, vista, controlador):
        """Un call comprado con strike 1500 sobre un spot de 1000."""
        fila = vista.filas_patas[0]
        fila["option_type"].value = "CALL"
        fila["side"].value = "COMPRA"
        fila["quantity"].value = "1"
        fila["strike"].value = "1500"
        fila["premium"].value = "5"
        for otra in vista.filas_patas[1:]:
            otra["quantity"].value = "0"
        controlador.calcular()

    def test_el_automatico_cubre_los_strikes_lejanos(self, entorno):
        """El caso que motivo esto.

        Con el rango fijo de 0.5x a 1.5x, un strike en 1500 sobre spot 1000
        quedaba justo en el borde: la curva se cortaba donde la estrategia
        recien empieza a cambiar de forma.
        """
        vista, controlador, _ = entorno
        self._cargar_strike_lejano(vista, controlador)

        assert vista.campo_x_max.value == "1,650.00"   # 1500 + 10%
        assert vista.mensaje.value == ""

    def test_muestra_el_rango_usado_aunque_sea_automatico(self, entorno):
        """Un campo deshabilitado y vacio no explica nada."""
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Iron Condor")

        assert vista.campo_x_min.value
        assert vista.campo_x_max.value
        assert vista.campo_x_min.disabled is True

    def test_en_manual_se_respeta_lo_cargado(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Long Call")

        vista.escala_automatica.value = False
        vista.campo_x_min.value = "980"
        vista.campo_x_max.value = "1020"
        controlador.aplicar_escala()

        assert vista.campo_x_min.value == "980.00"
        assert vista.campo_x_max.value == "1,020.00"
        assert vista.campo_x_min.disabled is False

    def test_el_rango_manual_afecta_las_metricas(self, entorno):
        """Cambiar el eje X no es solo mirar: cambia sobre que se calcula.

        Un rango angosto puede dejar afuera la zona donde la estrategia pierde
        mas, y entonces la perdida maxima informada es la del tramo visible.
        """
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Long Call")
        amplio = vista.metricas["Perdida maxima"].value

        vista.escala_automatica.value = False
        vista.campo_x_min.value = "1100"
        vista.campo_x_max.value = "1200"
        controlador.aplicar_escala()

        assert vista.metricas["Perdida maxima"].value != amplio

    def test_un_rango_invertido_avisa(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Long Call")

        vista.escala_automatica.value = False
        vista.campo_x_min.value = "1200"
        vista.campo_x_max.value = "800"
        controlador.aplicar_escala()

        assert "mayor que el inicio" in vista.mensaje.value.lower()

    def test_texto_en_el_rango_avisa(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Long Call")

        vista.escala_automatica.value = False
        vista.campo_x_min.value = "ochocientos"
        vista.campo_x_max.value = "1200"
        controlador.aplicar_escala()

        assert "no es un numero" in vista.mensaje.value.lower()


class TestZoomVertical:
    """El eje Y es solo la ventana por la que se mira: no cambia los numeros."""

    def test_vacio_significa_automatico(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Iron Condor")
        assert vista.mensaje.value == ""

    def test_no_cambia_las_metricas(self, entorno):
        """Acotar el eje Y recorta el dibujo, no el calculo."""
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Iron Condor")
        antes = vista.metricas["Perdida maxima"].value

        vista.campo_y_min.value = "-5"
        vista.campo_y_max.value = "5"
        controlador.aplicar_escala()

        assert vista.metricas["Perdida maxima"].value == antes

    def test_cambia_el_grafico(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Iron Condor")
        sin_zoom = vista.grafico.src

        vista.campo_y_min.value = "-5"
        vista.campo_y_max.value = "5"
        controlador.aplicar_escala()

        assert vista.grafico.src != sin_zoom

    def test_un_solo_extremo_avisa(self, entorno):
        """Medio limite no define una ventana; se pregunta en vez de adivinar."""
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Long Call")

        vista.campo_y_min.value = "-100"
        vista.campo_y_max.value = ""
        controlador.aplicar_escala()

        assert "los dos extremos" in vista.mensaje.value.lower()

    def test_invertido_avisa(self, entorno):
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Long Call")

        vista.campo_y_min.value = "100"
        vista.campo_y_max.value = "-100"
        controlador.aplicar_escala()

        assert "eje y" in vista.mensaje.value.lower()

    def test_los_dos_ejes_son_independientes(self, entorno):
        """Se puede acotar el Y sin tocar el X y al reves."""
        vista, controlador, _ = entorno
        controlador.cargar_plantilla("Iron Condor")

        vista.escala_automatica.value = False
        vista.campo_x_min.value = "900"
        vista.campo_x_max.value = "1100"
        vista.campo_y_min.value = "-10"
        vista.campo_y_max.value = "25"
        controlador.aplicar_escala()

        assert vista.mensaje.value == ""
        assert vista.campo_x_min.value == "900.00"
        assert vista.campo_y_min.value == "-10"
