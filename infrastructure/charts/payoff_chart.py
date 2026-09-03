"""Dibujo del perfil de P&L, compartido entre el PDF y la pantalla."""

from io import BytesIO

import matplotlib

# Backend sin ventana. Hay que fijarlo antes de importar pyplot, o matplotlib
# elige uno interactivo y falla en un proceso sin display.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from application.dtos.snapshot import SimulationSnapshot  # noqa: E402

COLOR_GANANCIA = "#2e7d32"
COLOR_PERDIDA = "#c62828"
COLOR_CURVA = "#1565c0"
COLOR_EJES = "#555555"
COLOR_BREAKEVEN = "#ef6c00"


def render_payoff_png(
    snapshot: SimulationSnapshot,
    width: float = 8.0,
    height: float = 4.5,
    dpi: int = 150,
) -> bytes:
    """Dibuja el perfil de resultado al vencimiento y lo devuelve como PNG.

    Vive en infrastructure/ y no en ui/ porque lo usan dos adaptadores
    distintos: el exportador de PDF y la pantalla. Duplicar el dibujo llevaria
    a que el reporte impreso y lo que se ve en la aplicacion se fueran
    separando con cada retoque, que es peor que la dependencia compartida.

    Las decisiones de color no son decorativas. Verde donde gana y rojo donde
    pierde se lee antes que cualquier numero: quien opera reconoce la forma de
    un iron condor de un vistazo. El punteado naranja marca los breakevens,
    que es el dato mas concreto de la pantalla — de ese precio para alla, gana.
    """
    resultado = snapshot.result
    precios, pnl = resultado.prices, resultado.pnl

    figura, ejes = plt.subplots(figsize=(width, height))
    try:
        ejes.fill_between(precios, pnl, 0, where=(pnl >= 0),
                          color=COLOR_GANANCIA, alpha=0.18, interpolate=True)
        ejes.fill_between(precios, pnl, 0, where=(pnl < 0),
                          color=COLOR_PERDIDA, alpha=0.18, interpolate=True)
        ejes.plot(precios, pnl, color=COLOR_CURVA, linewidth=1.8)

        ejes.axhline(0, color=COLOR_EJES, linewidth=0.8)
        ejes.axvline(snapshot.market.spot, color=COLOR_EJES,
                     linestyle="--", linewidth=0.8)

        for be in resultado.breakevens:
            ejes.axvline(be, color=COLOR_BREAKEVEN, linestyle=":", linewidth=1.0)

        ejes.set_xlabel("Precio del subyacente al vencimiento")
        ejes.set_ylabel("P&L")
        ejes.set_title("Perfil de resultado al vencimiento")
        ejes.grid(alpha=0.25)
        figura.tight_layout()

        buffer = BytesIO()
        figura.savefig(buffer, format="png", dpi=dpi)
        return buffer.getvalue()
    finally:
        # Siempre, incluso si falla el dibujo. Cada figura que queda abierta
        # es memoria que no vuelve, y esto se llama en cada recalculo.
        plt.close(figura)
