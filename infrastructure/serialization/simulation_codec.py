"""Conversion de simulaciones a diccionario plano y de vuelta."""

import numpy as np

from application.dtos.calculation import CalculationResult
from application.dtos.snapshot import SimulationSnapshot
from domain.entities.greeks import Greeks
from domain.entities.leg import Leg
from domain.entities.strategy import Strategy
from domain.value_objects.market_conditions import MarketConditions

# Se incrementa cuando cambia la forma del diccionario. Un archivo sin version,
# o de una version que este codigo no conoce, se rechaza en vez de leerse mal:
# una simulacion silenciosamente equivocada es peor que una que no abre.
FORMATO_VERSION = 1


class FormatoDesconocido(Exception):
    """El diccionario no tiene la forma que este codec sabe leer."""


def to_dict(snapshot: SimulationSnapshot) -> dict:
    """Convierte una simulacion en un diccionario listo para guardar.

    El resultado solo contiene tipos que json y sqlite entienden: numeros,
    strings, listas y diccionarios. Los enums salen como texto y los arrays de
    numpy como listas.
    """
    estrategia, mercado, resultado = (
        snapshot.strategy, snapshot.market, snapshot.result
    )
    return {
        "version": FORMATO_VERSION,
        "strategy": {
            "multiplier": float(estrategia.multiplier),
            "legs": [
                {
                    "option_type": leg.option_type.value,
                    "side": leg.side.value,
                    "quantity": float(leg.quantity),
                    "strike": float(leg.strike),
                    "premium": float(leg.premium),
                }
                for leg in estrategia.legs
            ],
        },
        "market": {
            "spot": float(mercado.spot),
            "days_to_expiry": float(mercado.days_to_expiry),
            "volatility": float(mercado.volatility),
            "rate": float(mercado.rate),
            "dividend_yield": float(mercado.dividend_yield),
        },
        "result": {
            "net_premium": float(resultado.net_premium),
            "max_pnl": float(resultado.max_pnl),
            "min_pnl": float(resultado.min_pnl),
            "breakevens": [float(b) for b in resultado.breakevens],
            "profit_probability": float(resultado.profit_probability),
            "expected_pnl": float(resultado.expected_pnl),
            "greeks": {
                "value": resultado.greeks.value,
                "delta": resultado.greeks.delta,
                "gamma": resultado.greeks.gamma,
                "vega": resultado.greeks.vega,
                "theta": resultado.greeks.theta,
                "rho": resultado.greeks.rho,
            },
            "curve": {
                "prices": [float(p) for p in resultado.prices],
                "pnl": [float(v) for v in resultado.pnl],
            },
        },
    }


def from_dict(datos: dict) -> SimulationSnapshot:
    """Reconstruye una simulacion desde un diccionario guardado.

    Es la mitad que faltaba: con ella, un archivo exportado se puede volver a
    abrir y una fila de la base se puede convertir en una simulacion.

    No recalcula nada: devuelve exactamente lo que se guardo. Si hiciera falta
    recalcular con otros parametros, eso le corresponde al caso de uso, no al
    codec — que solo traduce entre dos representaciones de lo mismo.

    Las invariantes del dominio siguen valiendo: un archivo editado a mano con
    un strike negativo falla al construir el Leg, que es lo correcto. Los datos
    malos no dejan de serlo por venir de un archivo.
    """
    version = datos.get("version")
    if version != FORMATO_VERSION:
        raise FormatoDesconocido(
            f"Version de formato {version!r}; este programa lee la {FORMATO_VERSION}. "
            "El archivo puede ser de una version mas nueva."
        )

    for clave in ("strategy", "market", "result"):
        if clave not in datos:
            raise FormatoDesconocido(f"Falta la seccion {clave!r} en el archivo.")

    estrategia = _leer_estrategia(datos["strategy"])
    mercado = MarketConditions(**datos["market"])
    resultado = _leer_resultado(datos["result"])

    return SimulationSnapshot(strategy=estrategia, market=mercado, result=resultado)


def _leer_estrategia(datos: dict) -> Strategy:
    return Strategy(
        [
            Leg(p["option_type"], p["side"], p["quantity"], p["strike"], p["premium"])
            for p in datos["legs"]
        ],
        multiplier=datos["multiplier"],
    )


def _leer_resultado(datos: dict) -> CalculationResult:
    return CalculationResult(
        prices=np.asarray(datos["curve"]["prices"], dtype=float),
        pnl=np.asarray(datos["curve"]["pnl"], dtype=float),
        greeks=Greeks(**datos["greeks"]),
        net_premium=datos["net_premium"],
        max_pnl=datos["max_pnl"],
        min_pnl=datos["min_pnl"],
        breakevens=list(datos["breakevens"]),
        profit_probability=datos["profit_probability"],
        expected_pnl=datos["expected_pnl"],
    )
