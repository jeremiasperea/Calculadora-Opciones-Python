"""Metricas de probabilidad sobre una distribucion de escenarios."""

import numpy as np

from domain.value_objects.price_scenarios import PriceScenarios


def profit_probability(pnl: np.ndarray, scenarios: PriceScenarios) -> float:
    """Probabilidad de terminar con ganancia al vencimiento.

    Integra la densidad restringida a los escenarios donde el P&L es positivo.
    Es la respuesta a "de cada cien veces que arme esta posicion, en cuantas
    gano", bajo los supuestos del modelo que genero los escenarios.

    El criterio es estrictamente mayor que cero: quedar en el punto de
    equilibrio no cuenta como ganancia. Se preserva el criterio del codigo
    original.

    Que este calculo no dependa del modelo es lo que lo hace dominio: la
    cuenta es la misma trate la distribucion de una lognormal o de una
    simulacion con saltos.
    """
    pnl = np.asarray(pnl, dtype=float)
    return float(np.trapezoid((pnl > 0) * scenarios.densities, scenarios.grid))


def expected_pnl(pnl: np.ndarray, scenarios: PriceScenarios) -> float:
    """P&L promedio, ponderando cada escenario por su probabilidad.

    Es el valor esperado de la posicion. Sirve para comparar estrategias que
    tienen probabilidades de ganar parecidas pero magnitudes muy distintas:
    vender opciones suele ganar seguido y poco, y perder poco y mucho.

    Ojo con interpretarlo: se calcula bajo la volatilidad implicita que se
    cargo. Si la volatilidad realizada termina siendo otra, el resultado real
    difiere. El numero dice que espera el modelo, no que va a pasar.
    """
    pnl = np.asarray(pnl, dtype=float)
    return float(np.trapezoid(pnl * scenarios.densities, scenarios.grid))
