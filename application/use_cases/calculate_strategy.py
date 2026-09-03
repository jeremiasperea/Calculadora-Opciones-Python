"""Caso de uso: calcular el perfil de riesgo de una estrategia."""

from application.dtos.calculation import CalculationResult, PriceRange
from application.ports.pricing_port import PricingPort
from domain.entities.strategy import Strategy
from domain.services.breakeven_finder import find_breakevens
from domain.services.probability import expected_pnl, profit_probability
from domain.value_objects.market_conditions import MarketConditions


class CalculateStrategyUseCase:
    """Arma el analisis completo de una estrategia bajo ciertas condiciones.

    Es la orquestacion que hoy vive dentro de app.calculate(), mezclada con
    lectura de widgets y dibujo de graficos. Aca queda sola: pide, combina y
    devuelve, sin saber de donde vienen los datos ni a donde van.

    Notar lo que no aparece en este archivo: ni scipy, ni numpy salvo por los
    tipos que pasan, ni una sola formula. Todas las cuentas estan en el
    dominio (payoff, agregacion de griegos, breakevens, integracion) o detras
    del puerto (valuacion, escenarios). Un caso de uso que empieza a hacer
    matematica es senal de que algo del dominio se filtro a la capa de arriba.
    """

    def __init__(self, pricing: PricingPort) -> None:
        self._pricing = pricing

    def execute(
        self,
        strategy: Strategy,
        market: MarketConditions,
        price_range: PriceRange | None = None,
    ) -> CalculationResult:
        price_range = price_range or PriceRange()

        # 1. La curva de P&L al vencimiento sobre el rango que se va a dibujar.
        prices = price_range.prices_around(market.spot)
        pnl = strategy.payoff(prices)

        # 2. Sensibilidades: se le pide al modelo una pata a la vez y las
        #    combina la estrategia, que es quien conoce cantidades y signos.
        per_leg = [self._pricing.price_leg(leg, market) for leg in strategy.legs]
        greeks = strategy.aggregate_greeks(per_leg)

        # 3. Donde la curva cruza el cero.
        breakevens = find_breakevens(prices, pnl)

        # 4. Probabilidades sobre la distribucion del modelo.
        #
        #    Deliberadamente NO se reusa la curva del punto 1: ese rango se
        #    eligio para que el grafico se vea bien, no porque represente la
        #    distribucion de precios. Integrar sobre el daria un numero sin
        #    sentido — la probabilidad depende de cuan probable es cada precio,
        #    no de cuanto se decidio mostrar en pantalla.
        scenarios = self._pricing.generate_scenarios(market)
        scenario_pnl = strategy.payoff(scenarios.prices)

        return CalculationResult(
            prices=prices,
            pnl=pnl,
            greeks=greeks,
            net_premium=strategy.net_premium,
            max_pnl=float(pnl.max()),
            min_pnl=float(pnl.min()),
            breakevens=breakevens,
            profit_probability=profit_probability(scenario_pnl, scenarios),
            expected_pnl=expected_pnl(scenario_pnl, scenarios),
        )
