"""Catalogo de estrategias predefinidas.

Migrado desde strategies.py, ahora construido con las entidades del dominio.
Las plantillas usan strikes alrededor de 1000 y primas de referencia: son
puntos de partida para que el operador ajuste, no cotizaciones reales.
"""

from domain.entities.leg import Leg
from domain.entities.strategy import Strategy

# Cada plantilla es una lista de patas. El multiplicador no se fija aca porque
# depende del contrato que opere cada uno, no de la estrategia.
PLANTILLAS: dict[str, list[Leg]] = {
    "Long Call": [
        Leg("CALL", "COMPRA", 1, 1050, 30),
    ],
    "Long Put": [
        Leg("PUT", "COMPRA", 1, 950, 25),
    ],
    "Bull Call Spread": [
        Leg("CALL", "COMPRA", 1, 1000, 40),
        Leg("CALL", "VENTA", 1, 1100, 15),
    ],
    "Bear Put Spread": [
        Leg("PUT", "COMPRA", 1, 1000, 40),
        Leg("PUT", "VENTA", 1, 900, 15),
    ],
    "Long Straddle": [
        Leg("CALL", "COMPRA", 1, 1000, 35),
        Leg("PUT", "COMPRA", 1, 1000, 35),
    ],
    "Short Straddle": [
        Leg("CALL", "VENTA", 1, 1000, 35),
        Leg("PUT", "VENTA", 1, 1000, 35),
    ],
    "Long Strangle": [
        Leg("CALL", "COMPRA", 1, 1100, 20),
        Leg("PUT", "COMPRA", 1, 900, 20),
    ],
    "Iron Condor": [
        Leg("PUT", "COMPRA", 1, 900, 10),
        Leg("PUT", "VENTA", 1, 950, 20),
        Leg("CALL", "VENTA", 1, 1050, 20),
        Leg("CALL", "COMPRA", 1, 1100, 10),
    ],
    "Butterfly Call": [
        Leg("CALL", "COMPRA", 1, 950, 70),
        Leg("CALL", "VENTA", 2, 1000, 45),
        Leg("CALL", "COMPRA", 1, 1050, 20),
    ],
    "Call Backspread": [
        Leg("CALL", "VENTA", 1, 1000, 40),
        Leg("CALL", "COMPRA", 2, 1100, 20),
    ],
    "Put Backspread": [
        Leg("PUT", "VENTA", 1, 1000, 40),
        Leg("PUT", "COMPRA", 2, 900, 20),
    ],
}
