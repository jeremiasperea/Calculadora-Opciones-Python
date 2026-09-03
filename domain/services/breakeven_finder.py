"""Busca los puntos de equilibrio de una curva de P&L."""

from typing import Sequence

import numpy as np


def find_breakevens(prices: Sequence[float], pnl: Sequence[float]) -> list[float]:
    """Precios del subyacente donde el P&L cruza el cero.

    Es la pregunta mas concreta que hace el operador: "¿de que precio para
    arriba empiezo a ganar?". Una estrategia direccional tiene un breakeven;
    una de rango, como un iron condor, tiene dos.

    Como funciona: recorre pares consecutivos de la curva y busca cambios de
    signo. Cuando el P&L pasa de negativo a positivo (o al reves) entre dos
    puntos, el cruce esta en el medio y se estima interpolando linealmente.

    La aproximacion es buena porque el payoff al vencimiento es lineal por
    tramos: entre dos strikes la curva es una recta, asi que la interpolacion
    da el valor exacto salvo que un strike caiga justo entre dos puntos de la
    grilla. Con 401 puntos el error es de centavos.

    Por que es un servicio y no un metodo de Strategy: opera sobre una curva
    ya calculada, no sobre la estructura de la estrategia. Serviria igual para
    la curva de una cartera entera o de un instrumento que no sea una opcion.

    Limitacion conocida, heredada del codigo original: un cero exacto en el
    ultimo punto de la grilla no se detecta, porque el recorrido mira pares y
    el ultimo no tiene siguiente. Se preserva a proposito — la Fase 1 migra
    sin cambiar resultados.
    """
    prices = np.asarray(prices, dtype=float)
    pnl = np.asarray(pnl, dtype=float)

    raices: list[float] = []
    for i in range(len(prices) - 1):
        y1, y2 = pnl[i], pnl[i + 1]

        if y1 == 0:
            raices.append(float(prices[i]))
        elif y1 * y2 < 0:
            # Interpolacion lineal: donde la recta entre (x1,y1) y (x2,y2)
            # corta el eje x.
            cruce = prices[i] + (-y1) * (prices[i + 1] - prices[i]) / (y2 - y1)
            raices.append(float(cruce))

    return raices
