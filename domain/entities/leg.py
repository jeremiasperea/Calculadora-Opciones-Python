"""Leg: una pata individual de una estrategia de opciones."""

from dataclasses import dataclass

from domain.value_objects.option_type import OptionType
from domain.value_objects.position_side import PositionSide


@dataclass(frozen=True)
class Leg:
    """Una posicion en una sola opcion.

    Cinco datos la definen: que tipo de opcion, de que lado se esta, cuantos
    contratos, a que strike y a que prima.

    Es inmutable (`frozen=True`) a proposito. Las invariantes se validan al
    construir; si despues se pudiera reasignar un campo, esa validacion seria
    un chequeo inicial y no una garantia. Con frozen, "estaba bien cuando la
    cree" pasa a ser "esta bien siempre", y cualquier codigo que reciba un Leg
    puede confiar en el sin revalidar. Una pata no se modifica: se reemplaza.

    Las tres invariantes:

    - strike > 0    -- un precio de ejercicio negativo no existe.
    - quantity > 0  -- la cantidad es magnitud; el signo lo pone el lado.
    - premium >= 0  -- la prima es cuanto cuesta la opcion; si se cobra o se
                       paga lo decide el lado. Cero es valido.

    La segunda merece explicacion. Si se permitiera quantity=-5 con
    side=COMPRA, esa posicion se podria escribir de dos formas distintas
    (tambien como quantity=5 con side=VENTA). Dos representaciones del mismo
    estado es de donde salen los bugs de signo, asi que se elige una sola.
    """

    option_type: OptionType
    side: PositionSide
    quantity: float
    strike: float
    premium: float

    def __post_init__(self) -> None:
        # Coercion: acepta strings ("CALL") ademas de value objects. Un valor
        # invalido lanza ValueError aca, en la linea que creo el dato.
        # Como la clase es frozen, hay que saltear el __setattr__ bloqueado.
        object.__setattr__(self, "option_type", OptionType(self.option_type))
        object.__setattr__(self, "side", PositionSide(self.side))

        if self.strike <= 0:
            raise ValueError(f"El strike debe ser positivo, se recibio {self.strike}")
        if self.quantity <= 0:
            raise ValueError(
                f"La cantidad debe ser positiva, se recibio {self.quantity}. "
                "El signo lo determina el lado (COMPRA/VENTA), no la cantidad."
            )
        if self.premium < 0:
            raise ValueError(f"La prima no puede ser negativa, se recibio {self.premium}")

    @property
    def signed_quantity(self) -> float:
        """Cuanto suma (+) o resta (-) esta pata a la posicion agregada.

        Delega el signo en PositionSide en lugar de repetir el `if side ==
        "COMPRA"`. Si manana aparece un lado nuevo, se toca un solo archivo.
        """
        return self.quantity * self.side.sign
