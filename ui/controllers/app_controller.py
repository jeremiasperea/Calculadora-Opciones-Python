"""Controlador: conecta la pantalla con los casos de uso."""

import base64
from pathlib import Path
from typing import Callable

from application.dtos.calculation import CalculationResult, PriceRange
from application.dtos.snapshot import SimulationSnapshot
from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from application.use_cases.export_strategy import ExportStrategyUseCase
from application.use_cases.load_template import LoadTemplateUseCase
from application.use_cases.simulation_library import SimulationLibraryUseCase
from infrastructure.charts.payoff_chart import render_payoff_png
from ui.mappers.form_mapper import (
    FormError, LegForm, MarketForm, to_market, to_strategy,
)
from ui.views.main_view import MainView

# Cuantas filas mostrar en la tabla de escenarios. La curva tiene 401 puntos;
# mostrarlos todos es una lista que nadie recorre. Se toma una de cada tantas.
FILAS_EN_TABLA = 60


class AppController:
    """Traduce entre lo que pasa en la pantalla y lo que hacen los casos de uso.

    No calcula nada. Lee el formulario, se lo pasa al mapper, llama al caso de
    uso que corresponda y escribe el resultado en la vista. Toda decision de
    negocio esta rio abajo, ya cubierta por los tests de las fases 1 a 4.

    Lo unico propio que tiene es el formato de los numeros —cuantos decimales,
    donde va el signo de porcentaje, que color usar— que es una decision de
    presentacion y le corresponde.
    """

    def __init__(
        self,
        view: MainView,
        calcular: CalculateStrategyUseCase,
        cargar_plantilla: LoadTemplateUseCase,
        exportar: ExportStrategyUseCase,
        biblioteca: SimulationLibraryUseCase,
        refrescar: Callable[[], None],
    ) -> None:
        self._view = view
        self._calcular = calcular
        self._cargar_plantilla = cargar_plantilla
        self._exportar = exportar
        self._biblioteca = biblioteca
        self._refrescar = refrescar

        # Ultimo calculo, para poder exportar sin recalcular
        self._ultimo: SimulationSnapshot | None = None

    # ---- acciones -------------------------------------------------------

    def inicializar(self) -> None:
        """Carga el catalogo de plantillas y muestra la primera."""
        nombres = self._cargar_plantilla.list_available()
        self._view.set_opciones_plantilla(nombres)
        if nombres:
            self.cargar_plantilla(nombres[0])

    def cargar_plantilla(self, nombre: str) -> None:
        """Escribe una plantilla en la grilla y calcula."""
        try:
            estrategia = self._cargar_plantilla.execute(nombre)
        except KeyError:
            self._error(f"No se encontro la plantilla {nombre}.")
            return

        self._view.set_patas([
            (leg.option_type.value, leg.side.value,
             f"{leg.quantity:g}", f"{leg.strike:g}", f"{leg.premium:g}")
            for leg in estrategia.legs
        ])
        self.calcular()

    def calcular(self) -> None:
        """Lee el formulario, calcula y pinta el resultado."""
        try:
            mercado = to_market(self._leer_mercado())
            multiplicador = self._leer_multiplicador()
            estrategia = to_strategy(self._leer_patas(), multiplicador)
        except FormError as e:
            self._error(str(e))
            return

        resultado = self._calcular.execute(estrategia, mercado, PriceRange())
        self._ultimo = SimulationSnapshot(estrategia, mercado, resultado)

        self._pintar_metricas(resultado)
        self._pintar_grafico()
        self._pintar_escenarios(resultado)
        self._view.set_mensaje("")
        self._refrescar()

    def exportar(self, destino: Path) -> None:
        """Guarda el ultimo calculo en el archivo elegido."""
        if self._ultimo is None:
            self._error("Calcule antes de exportar.")
            return
        try:
            self._exportar.execute(self._ultimo, destino)
        except ValueError as e:
            self._error(str(e))
            return
        except OSError as e:
            # Permisos, disco lleno, ruta invalida: el operador puede
            # arreglarlo, asi que se le dice que paso en lugar de dejar que la
            # excepcion suba y cierre la ventana.
            self._error(f"No se pudo guardar el archivo: {e.strerror or e}.")
            return

        self._view.set_mensaje(f"Exportado a {destino.name}", es_error=False)
        self._refrescar()

    def formatos_de_exportacion(self) -> list[tuple[str, str]]:
        return self._exportar.available_formats()

    # ---- lectura del formulario -----------------------------------------

    def _leer_mercado(self) -> MarketForm:
        campos = self._view.campos_mercado
        return MarketForm(
            spot=campos["spot"].value or "",
            volatility_pct=campos["volatility_pct"].value or "",
            rate_pct=campos["rate_pct"].value or "",
            dividend_pct=campos["dividend_pct"].value or "",
            days=campos["days"].value or "",
            multiplier=campos["multiplier"].value or "",
        )

    def _leer_multiplicador(self) -> float:
        from ui.mappers.form_mapper import _leer

        return _leer(self._view.campos_mercado["multiplier"].value or "",
                     "el multiplicador")

    def _leer_patas(self) -> list[LegForm]:
        return [
            LegForm(
                option_type=fila["option_type"].value or "CALL",
                side=fila["side"].value or "COMPRA",
                quantity=fila["quantity"].value or "",
                strike=fila["strike"].value or "",
                premium=fila["premium"].value or "",
            )
            for fila in self._view.filas_patas
        ]

    # ---- pintado --------------------------------------------------------

    def _pintar_metricas(self, r: CalculationResult) -> None:
        verde, rojo = "#2e7d32", "#c62828"

        def color(valor: float) -> str:
            return verde if valor >= 0 else rojo

        self._view.set_metrica("P&L inicial", f"{r.net_premium:,.2f}",
                               color(r.net_premium))
        self._view.set_metrica("Perdida maxima", f"{r.min_pnl:,.2f}", rojo)
        self._view.set_metrica("Ganancia maxima", f"{r.max_pnl:,.2f}", verde)
        self._view.set_metrica(
            "Break-even",
            ", ".join(f"{b:,.2f}" for b in r.breakevens) or "—",
        )
        self._view.set_metrica("Prob. de beneficio", f"{r.profit_probability:.1%}")
        self._view.set_metrica("P&L esperado", f"{r.expected_pnl:,.2f}",
                               color(r.expected_pnl))

        for nombre, valor in [
            ("Delta", r.greeks.delta), ("Gamma", r.greeks.gamma),
            ("Vega", r.greeks.vega), ("Theta", r.greeks.theta),
            ("Rho", r.greeks.rho),
        ]:
            self._view.set_metrica(nombre, f"{valor:,.4f}")

    def _pintar_grafico(self) -> None:
        png = render_payoff_png(self._ultimo, width=9.0, height=5.0, dpi=110)
        self._view.set_grafico(base64.b64encode(png).decode("ascii"))

    def _pintar_escenarios(self, r: CalculationResult) -> None:
        paso = max(1, len(r.prices) // FILAS_EN_TABLA)
        inversion = abs(r.net_premium)

        filas = []
        for i in range(0, len(r.prices), paso):
            pnl = r.pnl[i]
            # El retorno solo tiene sentido si hubo desembolso. Una estrategia
            # a credito no tiene inversion inicial contra la cual medirlo.
            retorno = f"{pnl / inversion:.1%}" if inversion else "—"
            filas.append((f"{r.prices[i]:,.2f}", f"{pnl:,.2f}", retorno))

        self._view.set_escenarios(filas)

    def _error(self, mensaje: str) -> None:
        self._view.set_mensaje(mensaje, es_error=True)
        self._refrescar()

    # ---- simulaciones guardadas -----------------------------------------

    def guardar_simulacion(self, nombre: str) -> bool:
        """Guarda el ultimo calculo con el nombre que puso el operador.

        Devuelve si pudo, para que la pantalla sepa si cerrar el dialogo o
        dejarlo abierto con el mensaje de error a la vista.
        """
        if self._ultimo is None:
            self._error("Calcule antes de guardar.")
            return False
        try:
            self._biblioteca.save(nombre, self._ultimo)
        except ValueError as e:
            self._error(str(e))
            return False

        self._view.set_mensaje(f"Guardado como «{nombre.strip()}»", es_error=False)
        self._refrescar()
        return True

    def listar_simulaciones(self) -> list:
        return self._biblioteca.list_all()

    def abrir_simulacion(self, sim_id: str) -> None:
        """Carga una simulacion guardada en el formulario y recalcula.

        Se escriben los datos y se vuelve a calcular en lugar de mostrar el
        resultado guardado. Asi lo que se ve en pantalla siempre corresponde a
        lo que dice el formulario, y el operador puede modificar un parametro
        y ver el efecto sin que queden numeros viejos mezclados.
        """
        try:
            guardada = self._biblioteca.load(sim_id)
        except KeyError:
            self._error("Esa simulacion ya no existe.")
            return

        estrategia = guardada.snapshot.strategy
        mercado = guardada.snapshot.market

        self._view.set_mercado(
            spot=mercado.spot,
            volatilidad_pct=mercado.volatility * 100,
            tasa_pct=mercado.rate * 100,
            dividendo_pct=mercado.dividend_yield * 100,
            dias=mercado.days_to_expiry,
            multiplicador=estrategia.multiplier,
        )
        self._view.set_patas([
            (leg.option_type.value, leg.side.value,
             f"{leg.quantity:g}", f"{leg.strike:g}", f"{leg.premium:g}")
            for leg in estrategia.legs
        ])
        self.calcular()
        self._view.set_mensaje(f"Abierta «{guardada.name}»", es_error=False)
        self._refrescar()

    def borrar_simulacion(self, sim_id: str) -> None:
        try:
            self._biblioteca.delete(sim_id)
        except KeyError:
            self._error("Esa simulacion ya no existe.")
            return
        self._refrescar()
