"""Tests del armado de la pantalla.

Este archivo existe por un error que llego al usuario final.

La aplicacion fallaba al abrir con "FilePicker.__init__() got an unexpected
keyword argument 'on_result'": otro cambio de API de Flet 0.86, donde el
selector de archivos dejo de avisar por callback y save_file paso a ser una
corrutina que devuelve la ruta.

Los 508 tests estaban en verde. El problema es que ninguno ejecutaba main().
Se habia separado build_controller() de main() justamente para poder testear
el cableado de dependencias, y esa separacion se aprovecho a medias: quedo
cubierto lo que se extrajo y sin cubrir lo que quedo.

La leccion no es "hay que testear la UI". Es que separar algo para poder
testearlo no sirve de nada si despues no se testea lo que quedo del otro
lado. La parte sin cubrir era chica, mecanica y aburrida — y ahi estaba el
unico error que llego al usuario.

Estos tests usan un doble de Page en lugar de una ventana real. No verifican
que se vea bien; verifican que main() corra de principio a fin sin explotar,
que es exactamente lo que fallaba.
"""

import flet as ft
import pytest

from ui.main import TITULO, main


class VentanaFalsa:
    def __init__(self):
        self.width = None
        self.height = None


class PageFalsa:
    """Lo minimo que main() necesita de una Page de Flet.

    Registra lo que se le hace para poder verificarlo despues.
    """

    def __init__(self):
        self.title = None
        self.padding = None
        self.window = VentanaFalsa()
        self.services = []
        self.controles = []
        self.dialogos_abiertos = []
        self.veces_actualizada = 0

    def add(self, *controles):
        self.controles.extend(controles)

    def update(self):
        self.veces_actualizada += 1

    def show_dialog(self, dialogo):
        self.dialogos_abiertos.append(dialogo)

    def pop_dialog(self):
        if self.dialogos_abiertos:
            self.dialogos_abiertos.pop()


@pytest.fixture
def page(tmp_path, monkeypatch):
    """Ejecuta main() completo contra una base temporal."""
    import ui.main

    monkeypatch.setattr(ui.main, "BASE_DE_DATOS", tmp_path / "test.db")
    p = PageFalsa()
    main(p)
    return p


class TestArranque:
    def test_main_corre_de_principio_a_fin(self, page):
        """El test que faltaba.

        Con el FilePicker mal construido, esto fallaba con TypeError antes de
        llegar a la primera linea util.
        """
        assert page.title == TITULO

    def test_configura_la_ventana(self, page):
        assert page.window.width == 1400
        assert page.window.height == 900

    def test_agrega_el_contenido(self, page):
        assert len(page.controles) == 3  # encabezado, separador, cuerpo

    def test_registra_el_selector_de_archivos(self, page):
        assert len(page.services) == 1
        assert isinstance(page.services[0], ft.FilePicker)

    def test_calcula_al_arrancar(self, page):
        """Abre con una plantilla ya cargada, no con la pantalla en blanco."""
        assert page.veces_actualizada >= 1


class TestEventosConectados:
    """Todo boton tiene que hacer algo.

    Un on_click en None no rompe nada visible: el boton simplemente no
    responde, y eso se descubre usando la aplicacion.
    """

    def _vista(self, page):
        # El cuerpo es el tercer control agregado; la vista quedo dentro
        from ui.views.main_view import MainView
        return next(
            v for v in [getattr(page, "_vista", None)] if v is not None
        ) if hasattr(page, "_vista") else None

    def test_los_botones_tienen_manejador(self, tmp_path, monkeypatch):
        import ui.main
        from ui.views.main_view import MainView

        monkeypatch.setattr(ui.main, "BASE_DE_DATOS", tmp_path / "t.db")

        # Se intercepta la vista que arma main() para poder inspeccionarla
        vistas = []
        original = ui.main.MainView

        def capturar():
            v = original()
            vistas.append(v)
            return v

        monkeypatch.setattr(ui.main, "MainView", capturar)
        ui.main.main(PageFalsa())

        vista = vistas[0]
        for nombre in ["boton_calcular", "boton_exportar",
                       "boton_guardar", "boton_biblioteca"]:
            assert getattr(vista, nombre).on_click is not None, nombre

    def test_el_selector_de_plantillas_responde(self, tmp_path, monkeypatch):
        import ui.main

        monkeypatch.setattr(ui.main, "BASE_DE_DATOS", tmp_path / "t.db")
        vistas = []
        original = ui.main.MainView
        monkeypatch.setattr(ui.main, "MainView",
                            lambda: vistas.append(original()) or vistas[-1])
        ui.main.main(PageFalsa())

        assert vistas[0].selector_plantilla.on_select is not None

    def test_los_dialogos_tienen_botones(self, tmp_path, monkeypatch):
        """AlertDialog sin actions es un dialogo del que no se puede salir."""
        import ui.main

        monkeypatch.setattr(ui.main, "BASE_DE_DATOS", tmp_path / "t.db")
        vistas = []
        original = ui.main.MainView
        monkeypatch.setattr(ui.main, "MainView",
                            lambda: vistas.append(original()) or vistas[-1])
        ui.main.main(PageFalsa())

        vista = vistas[0]
        assert len(vista.dialogo_guardar.actions) == 2   # cancelar y guardar
        assert len(vista.dialogo_biblioteca.actions) == 1  # cerrar


class TestFilePicker:
    """El control que causo el error.

    En Flet 0.86 FilePicker no acepta on_result: save_file es una corrutina
    que devuelve la ruta elegida.
    """

    def test_se_construye_sin_callbacks(self, page):
        assert isinstance(page.services[0], ft.FilePicker)

    def test_el_manejador_de_exportar_es_async(self, tmp_path, monkeypatch):
        """Tiene que serlo para poder esperar a save_file."""
        import inspect
        import ui.main

        monkeypatch.setattr(ui.main, "BASE_DE_DATOS", tmp_path / "t.db")
        vistas = []
        original = ui.main.MainView
        monkeypatch.setattr(ui.main, "MainView",
                            lambda: vistas.append(original()) or vistas[-1])
        ui.main.main(PageFalsa())

        assert inspect.iscoroutinefunction(vistas[0].boton_exportar.on_click)


class TestLosEventosExISTEN:
    """Cada manejador asignado corresponde a un evento real del control.

    Este test existe por un segundo error que llego al usuario: el selector de
    plantillas no hacia nada. La causa era que se le asignaba `on_change`, y en
    Flet 0.86 el Dropdown avisa por `on_select`.

    Python no protesta al asignar un atributo que la clase no declara, asi que
    la linea corria sin error y el evento nunca se disparaba. El test anterior
    verificaba `on_change is not None`, que era verdadero justamente porque
    acababa de asignarlo — comprobaba su propia accion, no que sirviera.

    La forma correcta es preguntarle a la clase que eventos acepta. Eso
    detecta el problema entero: cualquier manejador conectado a un evento que
    no existe.
    """

    def _vista_armada(self, tmp_path, monkeypatch):
        import ui.main

        monkeypatch.setattr(ui.main, "BASE_DE_DATOS", tmp_path / "t.db")
        vistas = []
        original = ui.main.MainView
        monkeypatch.setattr(ui.main, "MainView",
                            lambda: vistas.append(original()) or vistas[-1])
        ui.main.main(PageFalsa())
        return vistas[0]

    def test_todo_manejador_corresponde_a_un_evento_del_control(
        self, tmp_path, monkeypatch
    ):
        import inspect

        vista = self._vista_armada(tmp_path, monkeypatch)

        controles = {
            "boton_calcular": vista.boton_calcular,
            "boton_exportar": vista.boton_exportar,
            "boton_guardar": vista.boton_guardar,
            "boton_biblioteca": vista.boton_biblioteca,
            "selector_plantilla": vista.selector_plantilla,
        }

        for nombre, control in controles.items():
            eventos_reales = {
                p for p in inspect.signature(type(control).__init__).parameters
                if p.startswith("on_")
            }
            asignados = {
                atributo for atributo in vars(control)
                if atributo.startswith("on_") and getattr(control, atributo) is not None
            }
            inventados = asignados - eventos_reales
            assert not inventados, (
                f"{nombre} ({type(control).__name__}) tiene manejadores en "
                f"{sorted(inventados)}, que no son eventos de ese control. "
                f"Los que acepta son: {sorted(eventos_reales)}"
            )

    def test_el_selector_usa_on_select(self, tmp_path, monkeypatch):
        """Explicito, porque es el que fallo."""
        import inspect

        vista = self._vista_armada(tmp_path, monkeypatch)
        eventos = {p for p in inspect.signature(ft.Dropdown.__init__).parameters
                   if p.startswith("on_")}

        assert "on_select" in eventos
        assert "on_change" not in eventos
        assert vista.selector_plantilla.on_select is not None
