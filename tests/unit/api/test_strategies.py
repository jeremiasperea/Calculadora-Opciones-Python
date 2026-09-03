"""Tests de los endpoints de calculo y plantillas.

Lo que se prueba aca es la traduccion HTTP, no la matematica. Que los griegos
esten bien lo cubren las fases 1 a 4; lo que hace falta verificar es que los
codigos de estado sean los correctos, que la validacion rechace lo que tiene
que rechazar y que los numeros lleguen enteros al otro lado.
"""

import pytest


class TestEstado:
    def test_health(self, cliente):
        assert cliente.get("/api/health").json() == {"status": "ok"}


class TestPlantillas:
    def test_lista_las_once(self, cliente):
        r = cliente.get("/api/templates")
        assert r.status_code == 200
        assert len(r.json()) == 11
        assert "Iron Condor" in r.json()

    def test_devuelve_una_plantilla(self, cliente):
        r = cliente.get("/api/templates/Iron Condor")
        assert r.status_code == 200

        datos = r.json()
        assert datos["name"] == "Iron Condor"
        assert len(datos["legs"]) == 4
        assert datos["legs"][0] == {
            "option_type": "PUT", "side": "COMPRA",
            "quantity": 1.0, "strike": 900.0, "premium": 10.0,
        }

    def test_una_plantilla_inexistente_da_404(self, cliente):
        """404 y no 500: el pedido esta bien formado, lo que no existe es el
        recurso. El caso de uso lanza KeyError y esta capa lo traduce."""
        r = cliente.get("/api/templates/Mariposa Invertida")
        assert r.status_code == 404
        assert "Mariposa Invertida" in r.json()["detail"]


class TestCalcular:
    def test_devuelve_el_resultado_completo(self, cliente, condor):
        r = cliente.post("/api/calculate", json=condor)
        assert r.status_code == 200

        d = r.json()
        assert d["net_premium"] == pytest.approx(20.0)
        assert d["max_pnl"] == pytest.approx(20.0)
        assert d["min_pnl"] == pytest.approx(-30.0)
        assert d["breakevens"] == pytest.approx([930.0, 1070.0])
        assert d["profit_probability"] == pytest.approx(0.515239261105258, rel=1e-9)

    def test_los_griegos_vienen_completos(self, cliente, condor):
        g = cliente.post("/api/calculate", json=condor).json()["greeks"]
        assert set(g) == {"value", "delta", "gamma", "vega", "theta", "rho"}
        assert g["delta"] == pytest.approx(-0.004556719861883218, rel=1e-9)

    def test_la_curva_viene_como_dos_listas(self, cliente, condor):
        d = cliente.post("/api/calculate", json=condor).json()
        assert len(d["prices"]) == 401
        assert len(d["pnl"]) == 401
        assert d["prices"][0] == pytest.approx(500.0)

    def test_acepta_un_rango_propio(self, cliente, condor):
        condor["price_range"] = {"min_factor": 0.9, "max_factor": 1.1, "points": 21}
        d = cliente.post("/api/calculate", json=condor).json()

        assert len(d["prices"]) == 21
        assert d["prices"][0] == pytest.approx(900.0)

    def test_aplica_el_multiplicador(self, cliente, condor):
        condor["multiplier"] = 100
        d = cliente.post("/api/calculate", json=condor).json()
        assert d["net_premium"] == pytest.approx(2000.0)


class TestValidacion:
    """Pydantic rechaza en el borde, con un 422 que dice que campo esta mal."""

    def test_sin_patas(self, cliente, condor):
        condor["legs"] = []
        assert cliente.post("/api/calculate", json=condor).status_code == 422

    def test_strike_negativo(self, cliente, condor):
        condor["legs"][0]["strike"] = -900
        r = cliente.post("/api/calculate", json=condor)
        assert r.status_code == 422
        assert "strike" in str(r.json()).lower()

    def test_cantidad_en_cero(self, cliente, condor):
        condor["legs"][0]["quantity"] = 0
        assert cliente.post("/api/calculate", json=condor).status_code == 422

    def test_volatilidad_en_cero(self, cliente, condor):
        condor["market"]["volatility"] = 0
        assert cliente.post("/api/calculate", json=condor).status_code == 422

    def test_tipo_de_opcion_inventado(self, cliente, condor):
        condor["legs"][0]["option_type"] = "CAL"
        assert cliente.post("/api/calculate", json=condor).status_code == 422

    def test_un_campo_que_no_existe_se_rechaza(self, cliente, condor):
        """extra='forbid' en los esquemas.

        Sin eso, un cliente que escribe 'stike' en vez de 'strike' recibiria
        un calculo hecho con el valor por defecto en lugar de un error. Es
        preferible fallar ruidosamente que devolver un numero equivocado.
        """
        condor["legs"][0]["stike"] = 900
        assert cliente.post("/api/calculate", json=condor).status_code == 422

    def test_la_tasa_negativa_se_acepta(self, cliente, condor):
        """Existen en el mundo real; la API no las prohibe."""
        condor["market"]["rate"] = -0.005
        assert cliente.post("/api/calculate", json=condor).status_code == 200
