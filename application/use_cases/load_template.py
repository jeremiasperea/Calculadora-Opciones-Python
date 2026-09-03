"""Caso de uso: cargar una estrategia predefinida."""

from application.ports.strategy_port import StrategyPort
from domain.entities.strategy import Strategy


class LoadTemplateUseCase:
    """Trae una plantilla del catalogo.

    Es casi una linea, y aun asi vale la pena que exista. Sin el, la UI
    tendria que hablarle directo al repositorio, y el dia que cargar una
    plantilla implique algo mas — registrar cual se uso, adaptar los strikes
    al spot actual, avisar que quedo desactualizada — ese agregado terminaria
    escrito adentro de un manejador de boton.

    El caso de uso es el lugar reservado para esa logica que todavia no
    existe. Cuesta doce lineas ahora y evita tener que reorganizar despues.
    """

    def __init__(self, strategies: StrategyPort) -> None:
        self._strategies = strategies

    def list_available(self) -> list[str]:
        return self._strategies.list_names()

    def execute(self, name: str) -> Strategy:
        return self._strategies.get_template(name)
