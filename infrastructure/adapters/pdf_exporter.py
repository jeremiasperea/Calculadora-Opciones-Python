"""Exportador a PDF con el grafico de P&L."""

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from application.dtos.snapshot import SimulationSnapshot
from application.ports.exporter_port import ExporterPort
from infrastructure.charts.payoff_chart import render_payoff_png


class PdfExporter(ExporterPort):
    """Arma un reporte de una pagina con el grafico y las metricas.

    Es el formato para mostrarle la posicion a otro: se imprime, se manda por
    correo y se lee sin abrir ningun programa. El grafico es lo que lo hace
    util — un operador entiende la forma de un iron condor de un vistazo mucho
    antes que leyendo que la ganancia maxima es 20 y la perdida 30.

    El grafico lo dibuja infrastructure/charts/payoff_chart.py, el mismo modulo
    que usa la pantalla. Compartirlo evita que el reporte impreso y lo que ve el
    operador se vayan separando con cada retoque.
    """

    @property
    def extension(self) -> str:
        return ".pdf"

    @property
    def description(self) -> str:
        return "PDF (reporte con grafico)"

    def export(self, snapshot: SimulationSnapshot, destination: Path) -> None:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)

        estilos = getSampleStyleSheet()
        doc = SimpleDocTemplate(
            str(destination), pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        )

        contenido = [
            Paragraph("Analisis de estrategia de opciones", estilos["Title"]),
            Spacer(1, 0.4 * cm),
            Image(BytesIO(render_payoff_png(snapshot)), width=16 * cm, height=9 * cm),
            Spacer(1, 0.5 * cm),
            Paragraph("Posicion", estilos["Heading2"]),
            self._tabla_patas(snapshot),
            Spacer(1, 0.4 * cm),
            Paragraph("Supuestos y resultado", estilos["Heading2"]),
            self._tabla_resumen(snapshot),
        ]
        doc.build(contenido)

    def _tabla_patas(self, snapshot: SimulationSnapshot) -> Table:
        filas = [["Tipo", "Lado", "Cantidad", "Strike", "Prima"]]
        for leg in snapshot.strategy.legs:
            filas.append([
                leg.option_type.value, leg.side.value,
                f"{leg.quantity:g}", f"{leg.strike:,.2f}", f"{leg.premium:,.2f}",
            ])
        return self._con_estilo(filas, [3 * cm, 3 * cm, 3 * cm, 3.5 * cm, 3.5 * cm])

    def _tabla_resumen(self, snapshot: SimulationSnapshot) -> Table:
        mercado, resultado = snapshot.market, snapshot.result
        breakevens = ", ".join(f"{b:,.2f}" for b in resultado.breakevens) or "—"

        filas = [
            ["Spot", f"{mercado.spot:,.2f}", "Delta", f"{resultado.greeks.delta:,.4f}"],
            ["Volatilidad", f"{mercado.volatility:.2%}", "Gamma", f"{resultado.greeks.gamma:,.4f}"],
            ["Tasa", f"{mercado.rate:.2%}", "Vega", f"{resultado.greeks.vega:,.4f}"],
            ["Dias", f"{mercado.days_to_expiry:g}", "Theta", f"{resultado.greeks.theta:,.4f}"],
            ["Multiplicador", f"{snapshot.strategy.multiplier:g}", "Rho", f"{resultado.greeks.rho:,.4f}"],
            ["P&L inicial", f"{resultado.net_premium:,.2f}", "Ganancia max.", f"{resultado.max_pnl:,.2f}"],
            ["Break-even", breakevens, "Perdida max.", f"{resultado.min_pnl:,.2f}"],
            ["Prob. beneficio", f"{resultado.profit_probability:.2%}",
             "P&L esperado", f"{resultado.expected_pnl:,.2f}"],
        ]
        return self._con_estilo(filas, [4 * cm, 4 * cm, 4 * cm, 4 * cm],
                                con_encabezado=False)

    def _con_estilo(self, filas, anchos, con_encabezado=True) -> Table:
        tabla = Table(filas, colWidths=anchos)
        estilo = [
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bdbdbd")),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]
        if con_encabezado:
            estilo += [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eceff1")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        else:
            estilo += [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ]
        tabla.setStyle(TableStyle(estilo))
        return tabla
