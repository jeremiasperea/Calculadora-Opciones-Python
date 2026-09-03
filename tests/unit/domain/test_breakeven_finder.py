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
    def test_un_cero_en_el_ultimo_punto_si_se_detecta(self):
        """Esto antes no funcionaba.

        La version original recorria pares y solo miraba el primero de cada
        uno, asi que un cero exacto en el ultimo punto de la grilla quedaba
        afuera. Se habia documentado como limitacion heredada durante la
        Fase 1, que migraba sin cambiar resultados.

        Al reescribir la funcion para manejar las mesetas en cero, el caso
        quedo resuelto de paso: ahora se comparan los signos de los dos
        extremos de cada par, asi que la transicion de perder a no-perder se
        detecta este donde este.
        """
        precios = np.array([900.0, 1000.0])
        pnl = np.array([-50.0, 0.0])
        assert find_breakevens(precios, pnl) == pytest.approx([1000.0])

    def test_un_punto_aislado_en_cero(self):
        """Toca cero y vuelve a ganar: un solo punto, no dos."""
        precios = np.array([900.0, 1000.0, 1100.0])
        pnl = np.array([5.0, 0.0, 5.0])
        assert find_breakevens(precios, pnl) == pytest.approx([1000.0])


class TestZonasPlanasEnCero:
    """Tramos enteros donde el P&L vale exactamente cero.

    Aparecen cuando el credito neto de la estrategia es cero: en las alas no
    se gana ni se pierde nada. El Butterfly Call de las plantillas es asi
    (-70 + 90 - 20 = 0).

    El detector original agregaba un break-even por CADA punto en cero. Sobre
    una grilla de 401 puntos eso daba 361 break-evens, y la pantalla mostraba
    una lista ilegible en lugar de dos numeros.

    Un break-even es donde la curva CAMBIA entre ganar y no ganar, no cada
    lugar donde toca el cero. Una meseta en cero tiene dos bordes, no
    trescientos puntos.
    """

    def test_una_meseta_reporta_solo_sus_bordes(self):
        precios = np.array([900.0, 950.0, 1000.0, 1050.0, 1100.0])
        pnl = np.array([0.0, 0.0, 50.0, 0.0, 0.0])

        be = find_breakevens(precios, pnl)
        assert be == pytest.approx([950.0, 1050.0])

    def test_una_meseta_larga_sigue_dando_dos(self):
        """Con mas resolucion, la respuesta no cambia."""
        precios = np.linspace(500.0, 1500.0, 401)
        pnl = np.where((precios > 950) & (precios < 1050), 50.0, 0.0)

        assert len(find_breakevens(precios, pnl)) == 2

    def test_todo_en_cero_no_tiene_breakevens(self):
        """Si nunca gana ni pierde, no hay punto de equilibrio que marcar."""
        precios = np.linspace(900.0, 1100.0, 21)
        assert find_breakevens(precios, np.zeros(21)) == []

    def test_meseta_entre_perdida_y_ganancia(self):
        """De perder a ni-ni a ganar: dos transiciones."""
        precios = np.array([900.0, 950.0, 1000.0, 1050.0, 1100.0])
        pnl = np.array([-30.0, 0.0, 0.0, 0.0, 40.0])

        be = find_breakevens(precios, pnl)
        assert len(be) == 2
        assert be[0] == pytest.approx(950.0, abs=25.0)
        assert be[1] == pytest.approx(1050.0, abs=25.0)


class TestButterflyReal:
    """El caso que aparecio en la pantalla."""

    def test_reporta_dos_breakevens_y_no_trescientos(self):
        from domain.entities.leg import Leg

        butterfly = Strategy([
            Leg("CALL", "COMPRA", 1, 950, 70),
            Leg("CALL", "VENTA", 2, 1000, 45),
            Leg("CALL", "COMPRA", 1, 1050, 20),
        ])
        precios = np.linspace(500.0, 1500.0, 401)

        be = find_breakevens(precios, butterfly.payoff(precios))
        assert len(be) == 2
        assert be[0] == pytest.approx(950.0, abs=3.0)
        assert be[1] == pytest.approx(1050.0, abs=3.0)


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
