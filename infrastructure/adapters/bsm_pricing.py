"""Adaptador de valuacion con el modelo Black-Scholes-Merton."""

import numpy as np
from scipy.stats import norm

from application.ports.pricing_port import PricingPort
from domain.entities.greeks import Greeks
from domain.entities.leg import Leg
from domain.value_objects.market_conditions import MarketConditions
from domain.value_objects.option_type import OptionType
from domain.value_objects.price_scenarios import PriceScenarios

# Con vencimiento hoy (T=0) el modelo se indefine: d1 divide por sqrt(T).
# Se acota por abajo para que devuelva el valor intrinseco en vez de NaN.
T_MINIMO = 1e-12

# Convenciones de presentacion heredadas de la practica del mercado: vega se
# informa por cada punto porcentual de volatilidad y rho por cada punto
# porcentual de tasa, no por unidad; theta se informa por dia y no por anio.
PUNTOS_PORCENTUALES = 100.0
DIAS_POR_ANIO = 365.0


class BSMPricingEngine(PricingPort):
    """Valuacion con Black-Scholes-Merton para opciones europeas.

    Es la primera clase del proyecto que importa scipy. Todo lo anterior
    —dominio, puertos, casos de uso— se escribio y se probo sin el, que era
    justamente el objetivo.

    Los supuestos del modelo viven aca, y ninguna otra capa los conoce:

    - el precio del subyacente sigue una lognormal
    - la volatilidad es constante hasta el vencimiento
    - la tasa es constante
    - solo se ejerce al vencimiento (europeas)
    - no hay costos de transaccion

    Reemplazarlo por un arbol binomial (que si maneja ejercicio temprano) es
    escribir otra clase que implemente PricingPort. Ni el dominio ni los casos
    de uso se enterarian.
    """

    def price_leg(self, leg: Leg, market: MarketConditions) -> Greeks:
        """Precio teorico y sensibilidades de una unidad comprada.

        Devuelve los griegos sin escalar por cantidad ni signo: de eso se
        ocupa Strategy.aggregate_greeks(), que es quien conoce esos pesos.
        """
        S = market.spot
        K = leg.strike
        T = max(market.years_to_expiry, T_MINIMO)
        sigma = market.volatility
        r = market.rate
        q = market.dividend_yield

        # No se acota sigma como hacia models.py: MarketConditions ya
        # garantiza que sea positiva, asi que el caso no puede construirse.
        sqrt_T = np.sqrt(T)
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T

        descuento_tasa = np.exp(-r * T)
        descuento_div = np.exp(-q * T)
        densidad_d1 = norm.pdf(d1)

        if leg.option_type is OptionType.CALL:
            value = S * descuento_div * norm.cdf(d1) - K * descuento_tasa * norm.cdf(d2)
            delta = descuento_div * norm.cdf(d1)
            theta = (
                -(S * descuento_div * densidad_d1 * sigma) / (2 * sqrt_T)
                - r * K * descuento_tasa * norm.cdf(d2)
                + q * S * descuento_div * norm.cdf(d1)
            ) / DIAS_POR_ANIO
            rho = K * T * descuento_tasa * norm.cdf(d2) / PUNTOS_PORCENTUALES
        else:
            value = K * descuento_tasa * norm.cdf(-d2) - S * descuento_div * norm.cdf(-d1)
            delta = descuento_div * (norm.cdf(d1) - 1)
            theta = (
                -(S * descuento_div * densidad_d1 * sigma) / (2 * sqrt_T)
                + r * K * descuento_tasa * norm.cdf(-d2)
                - q * S * descuento_div * norm.cdf(-d1)
            ) / DIAS_POR_ANIO
            rho = -K * T * descuento_tasa * norm.cdf(-d2) / PUNTOS_PORCENTUALES

        # gamma y vega son iguales para call y put: la diferencia entre ambos
        # es lineal en el spot, asi que las derivadas segundas coinciden.
        return Greeks(
            value=float(value),
            delta=float(delta),
            gamma=float(descuento_div * densidad_d1 / (S * sigma * sqrt_T)),
            vega=float(S * descuento_div * densidad_d1 * sqrt_T / PUNTOS_PORCENTUALES),
            theta=float(theta),
            rho=float(rho),
        )

    def generate_scenarios(
        self, market: MarketConditions, points: int = 20_001
    ) -> PriceScenarios:
        """Distribucion lognormal de precios al vencimiento.

        Es el mismo supuesto que sostiene la formula de arriba: bajo la medida
        de riesgo neutral, el precio futuro es

            S_T = S * exp((r - q - sigma^2/2)*T + sigma*sqrt(T)*Z)

        con Z normal estandar. La grilla cubre de -5 a +5 desvios, que abarca
        practicamente toda la probabilidad (99.99994%).

        El termino -sigma^2/2 es el ajuste de Ito: sin el, el precio esperado
        no seria el forward y las probabilidades quedarian sesgadas.
        """
        T = market.years_to_expiry
        z = np.linspace(-5.0, 5.0, points)

        deriva = (market.rate - market.dividend_yield - 0.5 * market.volatility ** 2) * T
        difusion = market.volatility * np.sqrt(T) * z

        return PriceScenarios(
            prices=market.spot * np.exp(deriva + difusion),
            densities=np.exp(-0.5 * z * z) / np.sqrt(2 * np.pi),
            grid=z,
        )
