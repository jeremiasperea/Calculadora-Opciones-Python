"""Test de humo de la pantalla.

No verifica que se vea bien —eso se mira— sino que se construya sin errores.
Suena poco, pero cubre el problema mas concreto de trabajar con una libreria
de interfaz: la API cambia entre versiones.

Armar esta vista con Flet 0.86 encontro cuatro incompatibilidades seguidas
con la forma anterior: TextField.suffix_text paso a suffix y ahora recibe un
control, Image.src_base64 desaparecio en favor de un data URI en src, src
paso a ser obligatorio, y ImageFit se llama BoxFit. Cada una aparecio al
correr el codigo, una por vez.

Con este test, la proxima actualizacion de Flet las muestra todas juntas en
un segundo, en vez de descubrirlas de a una abriendo la aplicacion.
"""

import flet as ft
import pytest

from ui.views.main_view import CANTIDAD_DE_PATAS, METRICAS, MainView


@pytest.fixture
def vista():
    return MainView()


class TestConstruccion:
    def test_se_construye_sin_errores(self, vista):
        assert vista is not None

    def test_tiene_los_campos_de_mercado(self, vista):
        for clave in ["spot", "volatility_pct", "rate_pct",
                      "dividend_pct", "days", "multiplier"]:
            assert clave in vista.campos_mercado

    def test_tiene_seis_filas_de_patas(self, vista):
        assert len(vista.filas_patas) == CANTIDAD_DE_PATAS
        for fila in vista.filas_patas:
            assert set(fila) == {"option_type", "side", "quantity", "strike", "premium"}

    def test_tiene_todas_las_metricas(self, vista):
        assert set(vista.metricas) == set(METRICAS)

    def test_arma_el_layout(self, vista):
        layout = vista.build()
        assert isinstance(layout, ft.Row)
        assert len(layout.controls) == 2  # panel izquierdo y derecho


class TestValoresIniciales:
    def test_los_campos_traen_los_valores_de_la_app_vieja(self, vista):
        assert vista.campos_mercado["spot"].value == "1000"
        assert vista.campos_mercado["volatility_pct"].value == "35"
        assert vista.campos_mercado["days"].value == "30"

    def test_las_patas_arrancan_en_cero(self, vista):
        """Cantidad cero significa fila sin usar.

        El mapper descarta esas filas, asi que la pantalla abre con la grilla
        entera vacia y el operador completa solo las que necesita.
        """
        for fila in vista.filas_patas:
            assert fila["quantity"].value == "0"

    def test_las_metricas_arrancan_con_guion(self, vista):
        for nombre in METRICAS:
            assert vista.metricas[nombre].value == "—"


class TestEscritura:
    def test_escribe_una_metrica(self, vista):
        vista.set_metrica("Delta", "0.4521")
        assert vista.metricas["Delta"].value == "0.4521"

    def test_escribe_el_grafico_como_data_uri(self, vista):
        vista.set_grafico("QUJD")
        assert vista.grafico.src == "data:image/png;base64,QUJD"

    def test_un_mensaje_de_error_va_en_rojo(self, vista):
        vista.set_mensaje("algo salio mal", es_error=True)
        assert vista.mensaje.color == ft.Colors.RED_700

    def test_un_mensaje_de_exito_va_en_verde(self, vista):
        vista.set_mensaje("listo", es_error=False)
        assert vista.mensaje.color == ft.Colors.GREEN_700

    def test_carga_la_tabla_de_escenarios(self, vista):
        vista.set_escenarios([("1000.00", "50.00", "5%"), ("1100.00", "150.00", "15%")])
        assert len(vista.tabla_escenarios.rows) == 2

    def test_recargar_la_tabla_reemplaza_las_filas(self, vista):
        """Sin esto, cada calculo agregaria filas a las anteriores."""
        vista.set_escenarios([("1", "2", "3")] * 5)
        vista.set_escenarios([("1", "2", "3")] * 2)
        assert len(vista.tabla_escenarios.rows) == 2
