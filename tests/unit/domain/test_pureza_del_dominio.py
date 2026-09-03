"""Test arquitectonico: el dominio no depende de infraestructura.

Los otros tests verifican que el codigo hace lo correcto. Este verifica que
esta en el lugar correcto — es una regla de diseno convertida en assert.

Sin algo asi, la regla "el dominio no importa infraestructura" vive en un
documento que nadie relee. Un dia alguien necesita una distribucion normal,
escribe `from scipy.stats import norm` en el dominio, nadie lo nota en la
revision, y la separacion se perdio sin que ningun test se ponga rojo.

Este test se pone rojo.
"""

import ast
from pathlib import Path

import pytest

DOMINIO = Path(__file__).resolve().parents[3] / "domain"

# numpy se permite a proposito: es una estructura de datos con operaciones
# vectorizadas, no infraestructura. No hace I/O ni habla con nada externo.
# La regla es "sin frameworks, sin I/O, sin base de datos", no "solo stdlib".
PERMITIDOS = {
    "numpy", "dataclasses", "enum", "typing", "abc", "math",
    "__future__",  # solo habilita anotaciones diferidas, no trae nada
    "domain",
}

PROHIBIDOS = {
    "scipy": "modelo de pricing -> infrastructure/adapters/",
    "pandas": "exportacion -> infrastructure/adapters/",
    "matplotlib": "graficos -> capa de presentacion",
    "tkinter": "UI -> capa de presentacion",
    "flet": "UI -> capa de presentacion",
    "sqlite3": "persistencia -> infrastructure/adapters/",
    "sqlalchemy": "persistencia -> infrastructure/adapters/",
    "fastapi": "API -> adaptador de entrada",
    "requests": "red -> infrastructure/",
    "httpx": "red -> infrastructure/",
}


def modulos_importados(archivo: Path) -> set[str]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    raices = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            raices.update(a.name.split(".")[0] for a in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            raices.add(nodo.module.split(".")[0])
    return raices


ARCHIVOS = sorted(DOMINIO.rglob("*.py"))


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda p: p.name)
def test_no_importa_infraestructura(archivo):
    for modulo in modulos_importados(archivo):
        if modulo in PROHIBIDOS:
            pytest.fail(
                f"{archivo.relative_to(DOMINIO.parent)} importa '{modulo}'.\n"
                f"Eso no es dominio: {PROHIBIDOS[modulo]}"
            )


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda p: p.name)
def test_solo_importa_lo_permitido(archivo):
    """Mas estricto que el anterior: lista blanca en vez de lista negra.

    Atrapa dependencias que todavia no se le ocurrieron a nadie.
    """
    inesperados = modulos_importados(archivo) - PERMITIDOS
    assert not inesperados, (
        f"{archivo.relative_to(DOMINIO.parent)} importa {sorted(inesperados)}, "
        f"que no esta en la lista permitida {sorted(PERMITIDOS)}.\n"
        "Si de verdad corresponde al dominio, agregalo a PERMITIDOS con su motivo."
    )
