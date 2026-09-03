"""Esquemas de la frontera HTTP.

Cumplen para la API el mismo papel que ui/mappers/form_mapper.py para Flet:
traducen entre el formato del cliente y los objetos del dominio. Que existan
dos traductores distintos no es duplicacion — cada frontera tiene su propio
formato. Flet recibe texto de un formulario; la API recibe JSON tipado.

Lo que ninguno de los dos hace es calcular. Ambos entregan objetos del
dominio a los mismos casos de uso.

Sobre validar dos veces: estos esquemas repiten invariantes que el dominio ya
garantiza (strike positivo, cantidad positiva). Es deliberado y no es lo
mismo. Pydantic valida en el borde para devolver un 422 que dice exactamente
que campo esta mal; el dominio valida siempre, porque es su garantia y no
puede depender de que alguien haya chequeado antes. Si un dato pasa Pydantic
y el dominio lo rechaza, la API lo convierte igual en un 422.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from application.dtos.calculation import PriceRange
from domain.entities.leg import Leg
from domain.entities.strategy import Strategy
from domain.value_objects.market_conditions import MarketConditions


class LegIn(BaseModel):
    """Una pata, como la manda el cliente."""

    model_config = ConfigDict(extra="forbid")

    option_type: Literal["CALL", "PUT"]
    side: Literal["COMPRA", "VENTA"]
    quantity: float = Field(gt=0, description="Cantidad de contratos")
    strike: float = Field(gt=0, description="Precio de ejercicio")
    premium: float = Field(ge=0, description="Prima por contrato")

    def to_domain(self) -> Leg:
        return Leg(self.option_type, self.side, self.quantity,
                   self.strike, self.premium)


class MarketIn(BaseModel):
    """Condiciones de mercado.

    Los porcentajes van en decimal (0.35 = 35%), a diferencia de la pantalla,
    donde el operador escribe 35. Una API tiene como cliente a otro programa,
    y la forma canonica es la que usan las formulas; la escala de operador es
    una comodidad de la interfaz y se traduce ahi.
    """

    model_config = ConfigDict(extra="forbid")

    spot: float = Field(gt=0)
    days_to_expiry: float = Field(ge=0)
    volatility: float = Field(gt=0, description="Anualizada, en decimal: 0.35 = 35%")
    rate: float = Field(default=0.0, description="Puede ser negativa")
    dividend_yield: float = Field(default=0.0, ge=0)

    def to_domain(self) -> MarketConditions:
        return MarketConditions(
            spot=self.spot,
            days_to_expiry=self.days_to_expiry,
            volatility=self.volatility,
            rate=self.rate,
            dividend_yield=self.dividend_yield,
        )


class PriceRangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_factor: float = Field(default=0.5, gt=0)
    max_factor: float = Field(default=1.5, gt=0)
    points: int = Field(default=401, ge=2, le=10_000)

    def to_domain(self) -> PriceRange:
        return PriceRange(self.min_factor, self.max_factor, self.points)


class CalculateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legs: list[LegIn] = Field(min_length=1)
    market: MarketIn
    multiplier: float = Field(default=1.0, gt=0)
    price_range: PriceRangeIn | None = None

    def strategy(self) -> Strategy:
        return Strategy([p.to_domain() for p in self.legs], multiplier=self.multiplier)


class GreeksOut(BaseModel):
    value: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


class CalculationOut(BaseModel):
    """El resultado, como lo devuelve la API.

    La curva se manda como dos listas paralelas y no como lista de pares,
    porque asi es como la consumen las librerias de graficos y se evita que el
    cliente tenga que desarmarla.
    """

    net_premium: float
    max_pnl: float
    min_pnl: float
    breakevens: list[float]
    profit_probability: float
    expected_pnl: float
    greeks: GreeksOut
    prices: list[float]
    pnl: list[float]

    @classmethod
    def from_domain(cls, resultado) -> "CalculationOut":
        return cls(
            net_premium=resultado.net_premium,
            max_pnl=resultado.max_pnl,
            min_pnl=resultado.min_pnl,
            breakevens=[float(b) for b in resultado.breakevens],
            profit_probability=resultado.profit_probability,
            expected_pnl=resultado.expected_pnl,
            greeks=GreeksOut(**vars(resultado.greeks)),
            prices=[float(p) for p in resultado.prices],
            pnl=[float(v) for v in resultado.pnl],
        )


class TemplateOut(BaseModel):
    name: str
    legs: list[LegIn]


class SaveSimulationRequest(CalculateRequest):
    """Guardar recibe lo mismo que calcular, mas el nombre.

    El resultado no se manda: se recalcula en el servidor. Aceptarlo del
    cliente permitiria guardar una simulacion cuyos numeros no correspondan a
    sus parametros, y esa inconsistencia despues es imposible de detectar.
    """

    name: str = Field(min_length=1, max_length=200)


class SimulationSummaryOut(BaseModel):
    id: str
    name: str
    created_at: str
    description: str
    net_premium: float


class SavedSimulationOut(BaseModel):
    id: str
    name: str
    created_at: str
    legs: list[LegIn]
    market: MarketIn
    multiplier: float
    result: CalculationOut
