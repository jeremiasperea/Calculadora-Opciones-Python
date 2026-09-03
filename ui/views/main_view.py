"""La pantalla: controles y disposicion, sin decisiones de negocio."""

from dataclasses import dataclass

import flet as ft

CANTIDAD_DE_PATAS = 6

# PNG de 1x1 transparente. Flet 0.86 exige que Image reciba un src al
# construirse, y el grafico recien existe despues del primer calculo.
PNG_VACIO = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)

# Etiquetas de las metricas, en el orden en que se muestran. El orden importa:
# primero lo que responde "cuanto puedo perder", que es la primera pregunta de
# quien va a tomar la posicion.
METRICAS = [
    "P&L inicial",
    "Perdida maxima",
    "Ganancia maxima",
    "Break-even",
    "Prob. de beneficio",
    "P&L esperado",
    "Delta",
    "Gamma",
    "Vega",
    "Theta",
    "Rho",
]


@dataclass
class CampoMercado:
    etiqueta: str
    clave: str
    valor_inicial: str
    sufijo: str | None = None


CAMPOS_MERCADO = [
    CampoMercado("Spot", "spot", "1000"),
    CampoMercado("Volatilidad", "volatility_pct", "35", "%"),
    CampoMercado("Tasa", "rate_pct", "5", "%"),
    CampoMercado("Dividendos", "dividend_pct", "0", "%"),
    CampoMercado("Dias al vto.", "days", "30"),
    CampoMercado("Multiplicador", "multiplier", "1"),
]


class MainView:
    """Construye los controles y los expone para que el controlador los use.

    Es un "humble object": no calcula, no valida, no decide. Solo crea
    controles, los acomoda y ofrece metodos para escribir en ellos. Toda la
    logica vive en el controlador, que si esta cubierto por los tests de los
    casos de uso.

    Esa division es lo que hace que no haga falta automatizar la interfaz. Un
    error aca es visual y se ve al abrir la aplicacion; un error de calculo
    seria invisible, y por eso vive donde hay tests.
    """

    def __init__(self) -> None:
        self.campos_mercado: dict[str, ft.TextField] = {}
        self.filas_patas: list[dict[str, ft.Control]] = []
        self.metricas: dict[str, ft.Text] = {}

        self._crear_campos_mercado()
        self._crear_filas_patas()
        self._crear_metricas()

        self.selector_plantilla = ft.Dropdown(
            label="Plantilla", width=220, dense=True,
        )
        # ft.Button y no ElevatedButton: este ultimo quedo deprecado en Flet
        # 0.80 y se elimina en la 1.0. Escribirlo ya con la API vigente evita
        # arrastrar una migracion pendiente desde el primer dia.
        self.boton_calcular = ft.Button(
            "CALCULAR", icon=ft.Icons.CALCULATE, width=150,
        )
        self.boton_exportar = ft.OutlinedButton(
            "Exportar", icon=ft.Icons.DOWNLOAD, width=150,
        )
        self.grafico = ft.Image(
            src=PNG_VACIO, fit=ft.BoxFit.CONTAIN, expand=True,
        )
        self.tabla_escenarios = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Spot")),
                ft.DataColumn(ft.Text("P&L"), numeric=True),
                ft.DataColumn(ft.Text("Retorno"), numeric=True),
            ],
            rows=[],
            heading_row_height=34,
            data_row_max_height=30,
        )
        self.mensaje = ft.Text("", color=ft.Colors.RED_700, size=12)

    # ---- construccion de controles -------------------------------------

    def _crear_campos_mercado(self) -> None:
        for campo in CAMPOS_MERCADO:
            self.campos_mercado[campo.clave] = ft.TextField(
                label=campo.etiqueta,
                value=campo.valor_inicial,
                suffix=ft.Text(campo.sufijo) if campo.sufijo else None,
                dense=True,
                width=130,
                text_size=13,
            )

    def _crear_filas_patas(self) -> None:
        for _ in range(CANTIDAD_DE_PATAS):
            self.filas_patas.append({
                "option_type": ft.Dropdown(
                    options=[ft.dropdown.Option("CALL"), ft.dropdown.Option("PUT")],
                    value="CALL", width=95, dense=True, text_size=13,
                ),
                "side": ft.Dropdown(
                    options=[ft.dropdown.Option("COMPRA"), ft.dropdown.Option("VENTA")],
                    value="COMPRA", width=110, dense=True, text_size=13,
                ),
                "quantity": ft.TextField(value="0", width=80, dense=True, text_size=13),
                "strike": ft.TextField(value="1000", width=95, dense=True, text_size=13),
                "premium": ft.TextField(value="0", width=95, dense=True, text_size=13),
            })

    def _crear_metricas(self) -> None:
        for nombre in METRICAS:
            self.metricas[nombre] = ft.Text("—", size=13, weight=ft.FontWeight.W_500)

    # ---- disposicion ----------------------------------------------------

    def build(self) -> ft.Control:
        return ft.Row(
            [self._panel_izquierdo(), self._panel_derecho()],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )

    def _panel_izquierdo(self) -> ft.Control:
        return ft.Container(
            content=ft.Column([
                self._seccion("Mercado", self._grilla_mercado()),
                self._seccion("Estrategia", self._grilla_patas()),
                ft.Row([self.boton_calcular, self.boton_exportar], spacing=8),
                self.mensaje,
                self._seccion("Resultado", self._panel_metricas()),
            ], spacing=14, scroll=ft.ScrollMode.AUTO),
            width=520,
            padding=14,
        )

    def _panel_derecho(self) -> ft.Control:
        return ft.Container(
            content=ft.Column([
                ft.Container(content=self.grafico, expand=True),
                ft.Container(
                    content=ft.Column([self.tabla_escenarios],
                                      scroll=ft.ScrollMode.AUTO),
                    height=230,
                    padding=ft.Padding(top=6),
                ),
            ], expand=True),
            expand=True,
            padding=14,
        )

    def _seccion(self, titulo: str, contenido: ft.Control) -> ft.Control:
        return ft.Column([
            ft.Text(titulo, size=15, weight=ft.FontWeight.BOLD),
            contenido,
        ], spacing=6)

    def _grilla_mercado(self) -> ft.Control:
        campos = [self.campos_mercado[c.clave] for c in CAMPOS_MERCADO]
        return ft.Column([
            ft.Row(campos[0:3], spacing=8),
            ft.Row(campos[3:6], spacing=8),
        ], spacing=8)

    def _grilla_patas(self) -> ft.Control:
        encabezado = ft.Row([
            ft.Container(ft.Text("Tipo", size=12, weight=ft.FontWeight.W_500), width=95),
            ft.Container(ft.Text("Lado", size=12, weight=ft.FontWeight.W_500), width=110),
            ft.Container(ft.Text("Cant.", size=12, weight=ft.FontWeight.W_500), width=80),
            ft.Container(ft.Text("Strike", size=12, weight=ft.FontWeight.W_500), width=95),
            ft.Container(ft.Text("Prima", size=12, weight=ft.FontWeight.W_500), width=95),
        ], spacing=6)

        filas = [
            ft.Row([f["option_type"], f["side"], f["quantity"], f["strike"], f["premium"]],
                   spacing=6)
            for f in self.filas_patas
        ]
        return ft.Column([encabezado, *filas], spacing=5)

    def _panel_metricas(self) -> ft.Control:
        def linea(nombre: str) -> ft.Control:
            return ft.Row([
                ft.Container(ft.Text(nombre, size=13), width=150),
                self.metricas[nombre],
            ], spacing=6)

        # Dos columnas: resultado economico a la izquierda, griegos a la derecha
        return ft.Row([
            ft.Column([linea(n) for n in METRICAS[:6]], spacing=3),
            ft.Column([linea(n) for n in METRICAS[6:]], spacing=3),
        ], spacing=20, vertical_alignment=ft.CrossAxisAlignment.START)

    # ---- escritura, la usa el controlador -------------------------------

    def set_metrica(self, nombre: str, texto: str, color: str | None = None) -> None:
        control = self.metricas[nombre]
        control.value = texto
        control.color = color

    def set_grafico(self, png_base64: str) -> None:
        """Recibe el PNG ya codificado y lo muestra.

        Flet 0.86 saco el atributo src_base64: ahora la imagen embebida se
        pasa como data URI en src. Este metodo es el unico lugar que conoce
        ese detalle; el controlador solo entrega el base64.
        """
        self.grafico.src = f"data:image/png;base64,{png_base64}"

    def set_mensaje(self, texto: str, es_error: bool = True) -> None:
        self.mensaje.value = texto
        self.mensaje.color = ft.Colors.RED_700 if es_error else ft.Colors.GREEN_700

    def set_escenarios(self, filas: list[tuple[str, str, str]]) -> None:
        self.tabla_escenarios.rows = [
            ft.DataRow(cells=[ft.DataCell(ft.Text(c, size=12)) for c in fila])
            for fila in filas
        ]

    def set_opciones_plantilla(self, nombres: list[str]) -> None:
        self.selector_plantilla.options = [
            ft.dropdown.Option(n) for n in nombres
        ]
        if nombres:
            self.selector_plantilla.value = nombres[0]

    def set_patas(self, patas: list[tuple[str, str, str, str, str]]) -> None:
        """Escribe las patas en la grilla y limpia las filas que sobran.

        Limpiar es tan importante como escribir: sin eso, cargar una plantilla
        de dos patas despues de una de cuatro dejaria las dos ultimas de la
        anterior, y la estrategia calculada no seria la que se ve.
        """
        for i, fila in enumerate(self.filas_patas):
            if i < len(patas):
                tipo, lado, cantidad, strike, prima = patas[i]
                fila["option_type"].value = tipo
                fila["side"].value = lado
                fila["quantity"].value = cantidad
                fila["strike"].value = strike
                fila["premium"].value = prima
            else:
                fila["option_type"].value = "CALL"
                fila["side"].value = "COMPRA"
                fila["quantity"].value = "0"
                fila["strike"].value = "1000"
                fila["premium"].value = "0"
