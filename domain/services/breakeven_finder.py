"""Busca los puntos de equilibrio de una curva de P&L."""

from typing import Sequence

import numpy as np

# Dos break-evens mas cercanos que esto se consideran el mismo punto. La
# grilla tipica va de 500 a 1500 en 401 puntos, o sea 2.5 de separacion, asi
# que este umbral solo junta lo que es realmente el mismo cruce visto dos
# veces.
TOLERANCIA_DUPLICADOS = 1e-6


def find_breakevens(prices: Sequence[float], pnl: Sequence[float]) -> list[float]:
    """Precios del subyacente donde la estrategia cambia entre ganar y no ganar.

    Es la pregunta mas concreta que hace el operador: "¿de que precio para
    arriba empiezo a ganar?". Una estrategia direccional tiene un punto asi;
    una de rango, como un iron condor, tiene dos.

    Hay tres situaciones distintas y cada una se resuelve diferente:

    1. La curva cruza el cero entre dos puntos de la grilla. Es el caso comun:
       se estima el cruce interpolando linealmente. La aproximacion es exacta
       salvo redondeo, porque el payoff al vencimiento es lineal por tramos.

    2. La curva toca el cero en un punto suelto de la grilla. Se reporta ese
       punto una sola vez, aunque el cambio de signo se detecte dos veces
       (al entrar y al salir).

    3. La curva se apoya en cero a lo largo de un tramo entero. Pasa cuando el
       credito neto es cero: en las alas no se gana ni se pierde nada. Se
       reportan los DOS BORDES de esa meseta, no cada punto que la compone.

    El tercer caso es el que motivo reescribir esta funcion. La version
    anterior agregaba un break-even por cada punto en cero, y con el Butterfly
    Call sobre una grilla de 401 puntos devolvia 361 valores: la pantalla
    mostraba una lista ilegible en lugar de dos numeros.

    Un break-even marca un cambio de estado, no un contacto con el eje.
    """
    prices = np.asarray(prices, dtype=float)
    pnl = np.asarray(pnl, dtype=float)

    if len(prices) < 2:
        return []

    # -1 pierde, 0 ni gana ni pierde, +1 gana
    signos = np.sign(pnl)

    raices: list[float] = []
    for i in range(len(prices) - 1):
        s1, s2 = signos[i], signos[i + 1]
        if s1 == s2:
            continue

        if s1 != 0 and s2 != 0:
            # Cruce entre dos puntos: el cero esta en el medio
            y1, y2 = pnl[i], pnl[i + 1]
            raices.append(
                float(prices[i] + (-y1) * (prices[i + 1] - prices[i]) / (y2 - y1))
            )
        elif s1 == 0:
            # Termina una zona en cero: el borde es el ultimo punto que vale cero
            raices.append(float(prices[i]))
        else:
            # Empieza una zona en cero: el borde es el primer punto que vale cero
            raices.append(float(prices[i + 1]))

    return _sin_duplicados(raices)


def _sin_duplicados(raices: list[float]) -> list[float]:
    """Junta valores que son el mismo punto detectado dos veces.

    Un cero aislado en la grilla dispara dos transiciones —al entrar y al
    salir— y las dos apuntan al mismo precio.
    """
    unicos: list[float] = []
    for raiz in raices:
        if not unicos or abs(raiz - unicos[-1]) > TOLERANCIA_DUPLICADOS:
            unicos.append(raiz)
    return unicos
