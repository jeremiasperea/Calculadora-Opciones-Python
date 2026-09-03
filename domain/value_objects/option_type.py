"""Tipo de opcion: CALL o PUT."""

from enum import Enum


class OptionType(str, Enum):
    """Los dos tipos de opcion que existen.

    Hereda de `str` a proposito, por dos razones distintas:

    1. Compatibilidad durante la migracion. El codigo que todavia compara con
       strings crudos (`leg.option_type == "CALL"`) sigue funcionando sin
       cambios, asi que las fases se pueden mover de a una.

    2. Serializacion gratis. `json.dumps` y SQLite lo guardan como texto sin
       conversion, lo cual importa en la Fase 7 (persistencia).

    Lo que se gana: `OptionType("CAL")` lanza ValueError en el momento de
    construir el dato. Antes ese typo no fallaba — el codigo lo trataba como
    PUT y devolvia un payoff equivocado sin avisar.
    """

    CALL = "CALL"
    PUT = "PUT"

    def __str__(self) -> str:
        return self.value
