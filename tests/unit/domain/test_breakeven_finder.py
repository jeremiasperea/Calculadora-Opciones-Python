"""Tests del buscador de puntos de equilibrio.

Un breakeven es el precio del subyacente donde la estrategia deja de perder y
empieza a ganar: donde la curva de P&L cruza el cero. Para el operador es el
numero mas concreto de la pantalla — "de aca para arriba gano".

Esto es un *domain service*: logica del negocio que no le corresponde a
ninguna entidad en particular. Podria ser un metodo de Strategy, pero opera
sobre una curva ya calculada (dos arrays), no sobre la estructura de la
estrategia. Dejarlo suelto lo hace reutilizable y mas facil de testear.
"""

import numpy as np
import pytest

from domain.entities.leg import Leg
from domain.entities.strategy import Strategy
from domain.services.breakeven_finder import find_breakevens


class TestCasosBasicos:
    def test_un_solo_cruce(self):
        precios = np.array([900.0, 1000.0, 1100.0])
        pnl = np.array([-50.0, 0.0, 50.0])
        assert find_breakevens(precios, pnl) == pytest.approx([1000.0])

    def test_interpola_entre_dos_puntos(self):
        """El cruce casi nunca cae justo en un punto de la grilla.

        Entre 1000 (pnl=-10) y 1100 (pnl=+30) el cero esta al 25% del tramo:
        1000 + 100 * 10/40 = 1025.
        """
        precios = np.array([1000.0, 1100.0])
        pnl = np.array([-10.0, 30.0])
        assert find_breakevens(precios, pnl) == pytest.approx([1025.0])

    def test_dos_cruces(self):
        """Las estrategias de rango tienen dos: por donde entra y por donde sale."""
        precios = np.array([900.0, 1000.0, 1100.0])
        pnl = np.array([-20.0, 20.0, -20.0])
        be = find_breakevens(precios, pnl)
        assert len(be) == 2
        assert be[0] == pytest.approx(950.0)
        assert be[1] == pytest.approx(1050.0)

    def test_sin_cruces_devuelve_lista_vacia(self):
        precios = np.array([900.0, 1000.0, 1100.0])
        assert find_breakevens(precios, np.array([10.0, 20.0, 30.0])) == []
        assert find_breakevens(precios, np.array([-10.0, -20.0, -30.0])) == []

    def test_funciona_con_listas_ademas_de_arrays(self):
        assert find_breakevens([1000.0, 1100.0], [-10.0, 30.0]) == pytest.approx([1025.0])


class TestCasosBorde:
    def test_el_ultimo_punto_no_se_evalua(self):
        """Limitacion heredada del codigo original, preservada a proposito.

        El recorrido mira pares consecutivos, asi que un cero exacto en el
        ultimo punto de la grilla no se detecta. En la practica no molesta: la
        grilla va de 0.5x a 1.5x del spot y el borde es zona de perdida o
        ganancia plana, no de cruce.

        Se documenta como comportamiento conocido y no se corrige, porque la
        Fase 1 migra sin cambiar resultados. Cambiar esto ahora haria que un
        numero distinto pudiera atribuirse a la migracion.
        """
        precios = np.array([900.0, 1000.0])
        pnl = np.array([-50.0, 0.0])
        assert find_breakevens(precios, pnl) == []

    def test_curva_pegada_al_cero_sin_cruzar(self):
        precios = np.array([900.0, 1000.0, 1100.0])
        pnl = np.array([5.0, 0.0, 5.0])
        # El cero exacto en el medio cuenta como punto de equilibrio
        assert find_breakevens(precios, pnl) == pytest.approx([1000.0])


class TestContraLosValoresDeReferencia:
    def test_iron_condor(self, golden):
        """Los dos breakevens de un condor: 930 y 1070."""
        caso = golden["plantillas"]["Iron Condor|x1"]

        s = Strategy([
            Leg(p["option_type"], p["side"], p["quantity"], p["strike"], p["premium"])
            for p in caso["patas"]
        ])
        precios = np.linspace(500, 1500, 401)

        assert find_breakevens(precios, s.payoff(precios)) == pytest.approx(
            caso["breakevens"], rel=1e-9)
