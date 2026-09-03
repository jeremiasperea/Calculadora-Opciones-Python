"""Exportador a JSON."""

import json
from pathlib import Path

from application.dtos.snapshot import SimulationSnapshot
from application.ports.exporter_port import ExporterPort

# Se incrementa cuando cambia la forma del archivo. Sin esto, un archivo
# guardado hoy es indistinguible de uno guardado despues de un cambio de
# formato, y no hay forma de migrarlo ni de rechazarlo con un mensaje claro.
FORMATO_VERSION = 1


class JsonExporter(ExporterPort):
    """Guarda la simulacion completa, en un formato que se puede releer.

    A diferencia del CSV, que solo lleva la curva a una planilla, este archivo
    es autocontenido: incluye las patas, los supuestos de mercado y el
    resultado. Con eso alcanza para reconstruir la simulacion tal cual, que es
    lo que lo hace util para guardar una idea y retomarla, o para pasarle una
    estrategia a otra persona.

    Se escribe indentado a proposito. Es un archivo que alguien puede querer
    abrir y revisar a mano; el ahorro de bytes de escribirlo en una linea no
    compensa volverlo ilegible.
    """

    @property
    def extension(self) -> str:
        return ".json"

    @property
    def description(self) -> str:
        return "JSON (simulacion completa, reimportable)"

    def export(self, snapshot: SimulationSnapshot, destination: Path) -> None:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self._a_diccionario(snapshot), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _a_diccionario(self, snapshot: SimulationSnapshot) -> dict:
        estrategia, mercado, resultado = (
            snapshot.strategy, snapshot.market, snapshot.result
        )
        return {
            "version": FORMATO_VERSION,
            "strategy": {
                "multiplier": estrategia.multiplier,
                "legs": [
                    {
                        # .value convierte el enum a string plano: json no
                        # serializa enums, y guardar "OptionType.CALL" haria
                        # que releerlo falle.
                        "option_type": leg.option_type.value,
                        "side": leg.side.value,
                        "quantity": leg.quantity,
                        "strike": leg.strike,
                        "premium": leg.premium,
                    }
                    for leg in estrategia.legs
                ],
            },
            "market": {
                "spot": mercado.spot,
                "days_to_expiry": mercado.days_to_expiry,
                "volatility": mercado.volatility,
                "rate": mercado.rate,
                "dividend_yield": mercado.dividend_yield,
            },
            "result": {
                "net_premium": resultado.net_premium,
                "max_pnl": resultado.max_pnl,
                "min_pnl": resultado.min_pnl,
                "breakevens": [float(b) for b in resultado.breakevens],
                "profit_probability": resultado.profit_probability,
                "expected_pnl": resultado.expected_pnl,
                "greeks": {
                    "value": resultado.greeks.value,
                    "delta": resultado.greeks.delta,
                    "gamma": resultado.greeks.gamma,
                    "vega": resultado.greeks.vega,
                    "theta": resultado.greeks.theta,
                    "rho": resultado.greeks.rho,
                },
                # La curva se guarda aunque sea reconstruible, para que el
                # archivo sirva tambien fuera de esta aplicacion. Son unos
                # 400 pares de numeros: pesa poco y evita depender de que el
                # lector tenga el mismo motor de valuacion.
                "curve": {
                    "prices": [float(p) for p in resultado.prices],
                    "pnl": [float(v) for v in resultado.pnl],
                },
            },
        }
