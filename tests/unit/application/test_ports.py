"""Tests de los puertos.

Un puerto es una interfaz que declara *que* necesita la aplicacion, sin
decidir *quien* se lo da. No tiene logica, asi que no hay comportamiento que
probar. Lo que si vale la pena verificar es que cumplan su unica funcion:
impedir que una implementacion incompleta pase inadvertida.

La direccion de la dependencia es lo importante. Sin puerto:

    caso de uso  ---->  BSMPricingEngine       (depende de scipy)

Con puerto:

    caso de uso  ---->  PricingPort  <----  BSMPricingEngine

La flecha de la derecha se dio vuelta. Eso es la "inversion" de la inversion
de dependencias: la implementacion pasa a depender del contrato, y no al
reves.

Por eso los puertos viven en `application/ports/` y no en `infrastructure/`.
El puerto le pertenece a quien lo usa, no a quien lo implementa. Es la
aplicacion diciendo "necesito que alguien sepa valuar una pata"; que ese
alguien sea Black-Scholes o un arbol binomial no es asunto suyo.
"""

import pytest

from application.ports.pricing_port import PricingPort
from application.ports.strategy_port import StrategyPort
from domain.entities.greeks import Greeks
from domain.entities.leg import Leg
from domain.entities.strategy import Strategy
from domain.value_objects.market_conditions import MarketConditions


class TestPricingPort:
    def test_no_se_puede_instanciar(self):
        """Es un contrato, no una implementacion."""
        with pytest.raises(TypeError):
            PricingPort()

    def test_una_implementacion_incompleta_falla_al_instanciarse(self):
        """Este es el valor concreto de usar ABC.

        Si alguien escribe un adaptador y se olvida un metodo, el error
        aparece al construirlo, no la primera vez que se llama al metodo que
        falta — que puede ser en produccion, seis meses despues.
        """

        class AdaptadorIncompleto(PricingPort):
            pass  # no implementa price_leg

        with pytest.raises(TypeError, match="price_leg"):
            AdaptadorIncompleto()

    def test_una_implementacion_completa_funciona(self):
        class PricingFalso(PricingPort):
            def price_leg(self, leg, market):
                return Greeks(delta=0.5)

        greeks = PricingFalso().price_leg(
            Leg("CALL", "COMPRA", 1, 1000, 40),
            MarketConditions(spot=1000, days_to_expiry=30, volatility=0.35),
        )
        assert greeks.delta == 0.5


class TestStrategyPort:
    def test_no_se_puede_instanciar(self):
        with pytest.raises(TypeError):
            StrategyPort()

    def test_una_implementacion_incompleta_falla(self):
        class SoloUnMetodo(StrategyPort):
            def list_names(self):
                return []

        with pytest.raises(TypeError, match="get_template"):
            SoloUnMetodo()

    def test_una_implementacion_completa_funciona(self):
        class RepoFalso(StrategyPort):
            def list_names(self):
                return ["Long Call"]

            def get_template(self, name):
                return Strategy([Leg("CALL", "COMPRA", 1, 1050, 30)])

        repo = RepoFalso()
        assert repo.list_names() == ["Long Call"]
        assert len(repo.get_template("Long Call").legs) == 1


class TestLosPuertosNoConocenInfraestructura:
    """El puerto habla el idioma del dominio, no el de la tecnologia.

    PricingPort recibe un Leg y un MarketConditions y devuelve Greeks. No
    menciona scipy, ni arrays, ni una URL. Si el contrato nombrara la
    tecnologia, cambiarla obligaria a cambiar el contrato — y entonces no
    habria servido de nada.
    """

    def test_las_firmas_solo_usan_tipos_del_dominio(self):
        import inspect

        firma = inspect.signature(PricingPort.price_leg)
        anotaciones = [p.annotation for p in firma.parameters.values()]
        assert Leg in anotaciones
        assert MarketConditions in anotaciones
        assert firma.return_annotation is Greeks
