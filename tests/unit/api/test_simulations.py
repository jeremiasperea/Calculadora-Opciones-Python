"""Tests de los endpoints de simulaciones guardadas."""

import pytest


@pytest.fixture
def guardar(cliente, condor):
    """Guarda una simulacion y devuelve su respuesta."""
    def _guardar(nombre="Condor de marzo", **cambios):
        pedido = {**condor, "name": nombre, **cambios}
        return cliente.post("/api/simulations", json=pedido)
    return _guardar


class TestGuardar:
    def test_devuelve_201_y_la_simulacion(self, guardar):
        r = guardar()
        assert r.status_code == 201

        d = r.json()
        assert d["name"] == "Condor de marzo"
        assert d["id"]
        assert len(d["legs"]) == 4
        assert d["result"]["net_premium"] == pytest.approx(20.0)

    def test_sin_nombre_da_422(self, cliente, condor):
        assert cliente.post("/api/simulations",
                            json={**condor, "name": ""}).status_code == 422

    def test_el_resultado_se_recalcula_en_el_servidor(self, cliente, condor):
        """El cliente no manda el resultado, y si lo mandara se rechaza.

        Aceptarlo permitiria guardar una simulacion cuyos numeros no
        correspondan a sus parametros. Esa inconsistencia despues es imposible
        de detectar: los dos valores parecen igual de validos.
        """
        pedido = {**condor, "name": "Mentirosa", "result": {"net_premium": 999999}}
        assert cliente.post("/api/simulations", json=pedido).status_code == 422

    def test_los_nombres_repetidos_conviven(self, guardar):
        a, b = guardar("Prueba"), guardar("Prueba")
        assert a.json()["id"] != b.json()["id"]


class TestListar:
    def test_vacio_al_principio(self, cliente):
        assert cliente.get("/api/simulations").json() == []

    def test_trae_los_resumenes(self, cliente, guardar):
        guardar("Mi condor")
        resumen = cliente.get("/api/simulations").json()[0]

        assert resumen["name"] == "Mi condor"
        assert resumen["net_premium"] == pytest.approx(20.0)
        assert "4 patas" in resumen["description"]

    def test_el_resumen_no_trae_la_curva(self, cliente, guardar):
        """Cien simulaciones con sus curvas serian varios megabytes de
        respuesta para dibujar cinco columnas."""
        guardar()
        resumen = cliente.get("/api/simulations").json()[0]
        assert "result" not in resumen
        assert "legs" not in resumen

    def test_las_mas_nuevas_primero(self, cliente, guardar):
        for nombre in ["Primera", "Segunda", "Tercera"]:
            guardar(nombre)
        nombres = [s["name"] for s in cliente.get("/api/simulations").json()]
        assert nombres == ["Tercera", "Segunda", "Primera"]


class TestObtener:
    def test_devuelve_la_simulacion_completa(self, cliente, guardar):
        sim_id = guardar("Completa").json()["id"]
        d = cliente.get(f"/api/simulations/{sim_id}").json()

        assert d["name"] == "Completa"
        assert len(d["legs"]) == 4
        assert d["market"]["volatility"] == pytest.approx(0.35)
        assert len(d["result"]["prices"]) == 401

    def test_una_inexistente_da_404(self, cliente):
        assert cliente.get("/api/simulations/no-existe").status_code == 404


class TestBorrar:
    def test_devuelve_204(self, cliente, guardar):
        sim_id = guardar().json()["id"]
        assert cliente.delete(f"/api/simulations/{sim_id}").status_code == 204
        assert cliente.get("/api/simulations").json() == []

    def test_borrar_algo_inexistente_da_404(self, cliente):
        assert cliente.delete("/api/simulations/no-existe").status_code == 404

    def test_borrar_dos_veces_da_404_la_segunda(self, cliente, guardar):
        sim_id = guardar().json()["id"]
        assert cliente.delete(f"/api/simulations/{sim_id}").status_code == 204
        assert cliente.delete(f"/api/simulations/{sim_id}").status_code == 404


class TestCicloCompleto:
    def test_guardar_listar_abrir_borrar(self, cliente, guardar):
        sim_id = guardar("Ciclo completo").json()["id"]

        assert len(cliente.get("/api/simulations").json()) == 1
        assert cliente.get(f"/api/simulations/{sim_id}").json()["name"] == "Ciclo completo"
        assert cliente.delete(f"/api/simulations/{sim_id}").status_code == 204
        assert cliente.get("/api/simulations").json() == []


class TestMismosNumerosQueLaPantalla:
    """La API y la interfaz de escritorio dan exactamente lo mismo.

    Es la consecuencia concreta de que las dos sean adaptadores sobre los
    mismos casos de uso. Si estos numeros difirieran, significaria que alguna
    de las dos tiene logica propia que no deberia tener.
    """

    def test_iron_condor(self, cliente, condor, tmp_path):
        from ui.main import build_controller
        from ui.views.main_view import MainView

        por_http = cliente.post("/api/calculate", json=condor).json()

        vista = MainView()
        controlador = build_controller(vista, lambda: None, tmp_path / "x.db")
        controlador.inicializar()
        controlador.cargar_plantilla("Iron Condor")

        assert vista.metricas["P&L inicial"].value == f"{por_http['net_premium']:,.2f}"
        assert vista.metricas["Ganancia maxima"].value == f"{por_http['max_pnl']:,.2f}"
        assert vista.metricas["Prob. de beneficio"].value == (
            f"{por_http['profit_probability']:.1%}"
        )
        assert vista.metricas["Delta"].value == f"{por_http['greeks']['delta']:,.4f}"
