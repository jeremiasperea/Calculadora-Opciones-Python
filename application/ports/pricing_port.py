"""PricingPort: contrato para valuar una pata individual."""

from abc import ABC, abstractmethod

from domain.entities.greeks import Greeks
from domain.entities.leg import Leg
from domain.value_objects.market_conditions import MarketConditions


class PricingPort(ABC):
    """Lo que la aplicacion necesita de un modelo de valuacion.

    Declara la necesidad — "dada una pata y un estado de mercado, devolveme su
    precio teorico y sus sensibilidades" — sin decidir como se calcula. La
    implementacion con Black-Scholes llega en la Fase 4; podria haber despues
    una con arbol binomial o Monte Carlo, y nada de lo que dependa de este
    puerto se enteraria.

    Fijarse en lo que la firma NO menciona: ni scipy, ni arrays de numpy, ni
    una API externa. Solo tipos del dominio. Si el contrato nombrara la
    tecnologia, cambiarla obligaria a cambiar el contrato, y el puerto no
    habria servido para nada.

    Sobre ABC en lugar de typing.Protocol: Protocol funciona por forma (si
    tiene el metodo, sirve) y no requiere heredar. Es mas flexible y en
    proyectos grandes suele ser la mejor opcion. Aca se elige ABC a
    proposito, por dos razones:

    1. `class BSMPricingEngine(PricingPort)` deja la inversion de dependencia
       escrita en el codigo. Se ve de un vistazo quien implementa que.
    2. El error por un metodo faltante aparece al instanciar, no la primera
       vez que se lo llama.

    La segunda razon es la que importa en produccion. Con Protocol, olvidarse
    un metodo se descubre cuando alguien lo invoca.
    """

    @abstractmethod
    def price_leg(self, leg: Leg, market: MarketConditions) -> Greeks:
        """Precio teorico y sensibilidades de una pata, sin escalar.

        Devuelve los griegos de *una unidad comprada*: quien llama se encarga
        de aplicar cantidad, signo y multiplicador. Eso lo hace
        Strategy.aggregate_greeks(), que es quien conoce esos pesos.

        Dividirlo asi mantiene al adaptador ocupado en lo unico que le
        compete — la matematica del modelo — sin saber nada de estrategias.
        """
        ...
