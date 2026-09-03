"""Exportador a PDF con el grafico de P&L."""

from io import BytesIO
from pathlib import Path

import matplotlib

# Backend sin ventana: el PDF se genera en memoria, no hay pantalla que usar.
# Hay que fijarlo antes de importar pyplot o matplotlib elige uno interactivo
# y falla en un servidor o al exportar desde un proceso sin display.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from application.dtos.snapshot import SimulationSnapshot  # noqa: E402
from application.ports.exporter_port import ExporterPort  # noqa: E402


class PdfExporter(ExporterPort):
    """Arma un reporte de una pagina con el grafico y las metricas.

    Es el formato para mostrarle la posicion a otro: se imprime, se manda por
    correo y se lee sin abrir ningun programa. El grafico es lo que lo hace
    util — un operador entiende la forma de un iron condor de un vistazo mucho
    antes que leyendo que la ganancia maxima es 20 y la perdida 30.

    El grafico se genera con matplotlib a PNG en memoria y se embebe. No queda
    ningun archivo temporal en disco.
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
            Image(self._grafico(snapshot), width=16 * cm, height=9 * cm),
            Spacer(1, 0.5 * cm),
            Paragraph("Posicion", estilos["Heading2"]),
            self._tabla_patas(snapshot),
            Spacer(1, 0.4 * cm),
            Paragraph("Supuestos y resultado", estilos["Heading2"]),
            self._tabla_resumen(snapshot),
        ]
        doc.build(contenido)

    def _grafico(self, snapshot: SimulationSnapshot) -> BytesIO:
        """Dibuja el perfil de P&L y lo devuelve como PNG en memoria."""
        resultado = snapshot.result
        figura, ejes = plt.subplots(figsize=(8, 4.5))
        try:
            precios, pnl = resultado.prices, resultado.pnl

            # Verde donde gana, rojo donde pierde: se lee antes que los numeros.
            ejes.fill_between(precios, pnl, 0, where=(pnl >= 0),
                              color="#2e7d32", alpha=0.18, interpolate=True)
            ejes.fill_between(precios, pnl, 0, where=(pnl < 0),
                              color="#c62828", alpha=0.18, interpolate=True)
            ejes.plot(precios, pnl, color="#1565c0", linewidth=1.8)

            ejes.axhline(0, color="#555555", linewidth=0.8)
            ejes.axvline(snapshot.market.spot, color="#555555",
                         linestyle="--", linewidth=0.8)

            for be in resultado.breakevens:
                ejes.axvline(be, color="#ef6c00", linestyle=":", linewidth=1.0)

            ejes.set_xlabel("Precio del subyacente al vencimiento")
            ejes.set_ylabel("P&L")
            ejes.set_title("Perfil de resultado al vencimiento")
            ejes.grid(alpha=0.25)
            figura.tight_layout()

            buffer = BytesIO()
            figura.savefig(buffer, format="png", dpi=150)
            buffer.seek(0)
            return buffer
        finally:
            # Cerrar siempre, incluso si algo falla al dibujar. Cada figura que
            # queda abierta se acumula en memoria; en una app que exporta
            # muchas veces eso es una fuga.
            plt.close(figura)

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
