"""Traduccion entre el formulario de pantalla y el dominio."""

from dataclasses import dataclass

from domain.entities.leg import Leg
from domain.entities.strategy import Strategy
from domain.value_objects.market_conditions import MarketConditions


class FormError(Exception):
    """Error de carga, redactado para quien opera y no programa.

    Toda excepcion que llegue a la pantalla pasa por aca. Un ValueError de
    Python o un mensaje de una invariante del dominio son diagnosticos
    internos: le dicen al que escribio el codigo donde mirar, no al operador
    que corregir.

    Capitaliza la primera letra al construirse. Los mensajes se arman por
    partes —a veces la frase empieza con la etiqueta del campo, a veces con un
    prefijo— y sin esto algunos saldrian en minuscula. Hacerlo en un solo
    lugar es mas confiable que acordarse en cada punto donde se lanza.
    """

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje[:1].upper() + mensaje[1:] if mensaje else mensaje)


@dataclass(frozen=True)
class LegForm:
    """Una fila de la grilla de patas, tal como esta en pantalla: todo texto."""

    option_type: str
    side: str
    quantity: str
    strike: str
    premium: str

    @property
    def esta_vacia(self) -> bool:
        """Sin cantidad, la fila no describe ninguna posicion."""
        texto = self.quantity.strip()
        if not texto:
            return True
        try:
            return _a_numero(texto) == 0
        except ValueError:
            return False  # tiene algo escrito, aunque este mal: no es vacia


@dataclass(frozen=True)
class MarketForm:
    """El panel de condiciones de mercado, tal como esta en pantalla.

    Los porcentajes se llaman _pct para dejar explicito que llegan en la
    escala del operador (35, no 0.35). Confundir las dos escalas es un error
    de cien veces, asi que conviene que el nombre lo recuerde.
    """

    spot: str
    volatility_pct: str
    rate_pct: str
    dividend_pct: str
    days: str
    multiplier: str


def _a_numero(texto: str) -> float:
    """Convierte texto a numero aceptando como se escribe en la region.

    Admite coma decimal (1234,50), separador de miles (1.234,50) y el simbolo
    de porcentaje, que el operador tiende a escribir aunque el campo ya diga %.

    Rechazar '35%' con un error seria tecnicamente correcto y practicamente
    molesto: se entiende perfecto lo que quiso poner.
    """
    limpio = texto.strip().replace("%", "").replace(" ", "")
    if not limpio:
        raise ValueError("vacio")

    if "," in limpio:
        # Formato local: el punto separa miles y la coma decimales
        limpio = limpio.replace(".", "").replace(",", ".")

    return float(limpio)


def _leer(texto: str, etiqueta: str) -> float:
    try:
        return _a_numero(texto)
    except ValueError:
        if not texto.strip():
            raise FormError(f"Falta completar {etiqueta}.") from None
        raise FormError(
            f"{etiqueta}: {texto!r} no es un numero valido."
        ) from None


def to_market(form: MarketForm) -> MarketConditions:
    """Arma las condiciones de mercado desde el formulario."""
    spot = _leer(form.spot, "el spot")
    volatilidad = _leer(form.volatility_pct, "la volatilidad")
    tasa = _leer(form.rate_pct, "la tasa")
    dividendo = _leer(form.dividend_pct, "los dividendos")
    dias = _leer(form.days, "los dias al vencimiento")

    try:
        return MarketConditions(
            spot=spot,
            days_to_expiry=dias,
            # De la escala del operador (35) a la de las formulas (0.35)
            volatility=volatilidad / 100.0,
            rate=tasa / 100.0,
            dividend_yield=dividendo / 100.0,
        )
    except ValueError as e:
        raise FormError(_traducir_invariante(str(e))) from None


def to_strategy(forms: list[LegForm], multiplier: float) -> Strategy:
    """Arma la estrategia con las filas que tienen datos.

    Las filas vacias se descartan aca y no en el dominio: la grilla de seis
    posiciones es una decision de pantalla, y una pata con cantidad cero no es
    una posicion.
    """
    patas = []
    for numero, form in enumerate(forms, start=1):
        if form.esta_vacia:
            continue
        patas.append(_a_pata(form, numero))

    if not patas:
        raise FormError(
            "Cargue al menos una pata con cantidad mayor que cero."
        )

    try:
        return Strategy(patas, multiplier=multiplier)
    except ValueError as e:
        raise FormError(_traducir_invariante(str(e))) from None


def _a_pata(form: LegForm, numero: int) -> Leg:
    """Convierte una fila. El numero es el de pantalla, contando desde 1."""
    cantidad = _leer(form.quantity, f"la cantidad de la pata {numero}")
    strike = _leer(form.strike, f"el strike de la pata {numero}")
    prima = _leer(form.premium, f"la prima de la pata {numero}")

    try:
        return Leg(form.option_type, form.side, cantidad, strike, prima)
    except ValueError as e:
        raise FormError(f"Pata {numero}: {_traducir_invariante(str(e))}") from None


def _traducir_invariante(mensaje: str) -> str:
    """Reescribe un error del dominio en terminos del formulario.

    Los mensajes del dominio estan pensados para quien lee el codigo. Aca se
    los pasa al idioma de la pantalla, y se cae a un texto generico cuando
    aparece uno que todavia no se contemplo — mejor un mensaje impreciso que
    volcar una excepcion cruda.
    """
    m = mensaje.lower()

    if "spot" in m:
        return "El spot debe ser mayor que cero."
    if "volatilidad" in m:
        return "La volatilidad debe ser mayor que cero."
    if "dias" in m:
        return "Los dias al vencimiento no pueden ser negativos."
    if "dividendo" in m:
        return "Los dividendos no pueden ser negativos."
    if "strike" in m:
        return "el strike debe ser mayor que cero."
    if "cantidad" in m:
        return "la cantidad debe ser mayor que cero."
    if "prima" in m:
        return "la prima no puede ser negativa."
    if "multiplicador" in m:
        return "El multiplicador debe ser mayor que cero."
    if "pata" in m:
        return "La estrategia necesita al menos una pata."

    return "Revise los datos cargados."
