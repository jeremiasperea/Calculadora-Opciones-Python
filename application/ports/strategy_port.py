"""StrategyPort: contrato para obtener estrategias predefinidas."""

from abc import ABC, abstractmethod

from domain.entities.strategy import Strategy


class StrategyPort(ABC):
    """Lo que la aplicacion necesita de un catalogo de plantillas.

    Hoy las plantillas son un diccionario en strategies.py. Manana podrian ser
    un archivo JSON editable por el operador, o una tabla en SQLite junto con
    las simulaciones guardadas. Detras de este puerto, ese cambio no toca
    ningun caso de uso.

    Alguien podria objetar que envolver un diccionario en una interfaz es
    sobreingenieria, y en otro contexto tendria razon. Aca el punto de
    extension ya esta previsto: la Fase 7 agrega persistencia, y es razonable
    que el operador quiera guardar sus propias plantillas. El costo de la
    abstraccion hoy son doce lineas; el de no tenerla es tocar los casos de
    uso cuando llegue ese momento.
    """

    @abstractmethod
    def list_names(self) -> list[str]:
        """Nombres de las plantillas disponibles, para poblar el selector."""
        ...

    @abstractmethod
    def get_template(self, name: str) -> Strategy:
        """Devuelve la plantilla pedida.

        Lanza KeyError si no existe. Se elige una excepcion en vez de devolver
        None para que el error no viaje silencioso: un None se arrastra hasta
        que alguien lo desreferencia, tres capas mas abajo, con un mensaje que
        no dice nada del nombre que se pidio.
        """
        ...
