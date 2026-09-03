"""MarketConditions: el estado del mercado al momento de valuar una posicion."""

from dataclasses import dataclass

DIAS_POR_ANIO = 365.0


@dataclass(frozen=True)
class MarketConditions:
    """Los datos de mercado necesarios para valuar una opcion.

    - spot:            precio actual del subyacente
    - days_to_expiry:  dias corridos hasta el vencimiento
    - volatility:      volatilidad implicita anualizada (0.35 = 35%)
    - rate:            tasa libre de riesgo continua
    - dividend_yield:  rendimiento por dividendos continuo

    Existe para no pasar cinco floats sueltos. La firma vieja era
    `greeks(S, K, T_days, sigma, r, q, option_type)`: intercambiar r con q
    corre igual y devuelve otro numero sin avisar. Con un objeto nombrado ese
    error es imposible de escribir.

    Notar que la tasa puede ser negativa y el dividendo no. No es una
    inconsistencia: las tasas negativas existieron durante anios en Europa y
    Japon, mientras que un rendimiento por dividendos negativo significaria
    que tener la accion cuesta plata, que ya no es un dividendo. Las
    invariantes describen el negocio, no lo que a uno le suena normal.
    """

    spot: float
    days_to_expiry: float
    volatility: float
    rate: float = 0.0
    dividend_yield: float = 0.0

    def __post_init__(self) -> None:
        if self.spot <= 0:
            raise ValueError(f"El spot debe ser positivo, se recibio {self.spot}")
        if self.volatility <= 0:
            raise ValueError(
                f"La volatilidad debe ser positiva, se recibio {self.volatility}. "
                "Volatilidad cero implicaria conocer el precio futuro con certeza."
            )
        if self.days_to_expiry < 0:
            raise ValueError(
                f"Los dias al vencimiento no pueden ser negativos, "
                f"se recibio {self.days_to_expiry}"
            )
        if self.dividend_yield < 0:
            raise ValueError(
                f"El dividendo no puede ser negativo, se recibio {self.dividend_yield}"
            )

    @property
    def years_to_expiry(self) -> float:
        """Tiempo al vencimiento en anios, que es la unidad de los modelos.

        La convencion de 365 dias corridos (en vez de 252 ruedas) es una
        decision del negocio, no del modelo de pricing: cualquier modelo que
        se enchufe despues usa la misma. Por eso vive en el dominio.
        """
        return self.days_to_expiry / DIAS_POR_ANIO
