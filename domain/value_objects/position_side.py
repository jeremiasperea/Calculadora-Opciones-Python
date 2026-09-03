"""Lado de la posicion: COMPRA o VENTA."""

from enum import Enum


class PositionSide(str, Enum):
    """Si la pata se compra (largo) o se vende (corto).

    Los valores quedan en espanol porque son los que ya usa el dominio del
    proyecto y los que ve el operador en pantalla. Cambiarlos a BUY/SELL
    romperia las plantillas existentes sin ganar nada.

    De los dos value objects, este es el que mas protege: un lado mal escrito
    no desvia un poco el resultado, le da vuelta el signo. Una posicion
    comprada se cuenta como vendida y el P&L sale invertido.
    """

    COMPRA = "COMPRA"
    VENTA = "VENTA"

    def __str__(self) -> str:
        return self.value

    @property
    def sign(self) -> int:
        """+1 si esta comprada, -1 si esta vendida.

        Vive aca y no en Leg porque es una propiedad del lado en si: comprar
        siempre suma y vender siempre resta, sin importar de que instrumento
        se trate. Leg lo usa para calcular su cantidad con signo.
        """
        return 1 if self is PositionSide.COMPRA else -1
