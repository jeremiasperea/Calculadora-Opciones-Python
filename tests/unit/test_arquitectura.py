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

RAIZ = Path(__file__).resolve().parents[2]

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


ARCHIVOS = sorted((RAIZ / "domain").rglob("*.py"))


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda p: p.name)
def test_no_importa_infraestructura(archivo):
    for modulo in modulos_importados(archivo):
        if modulo in PROHIBIDOS:
            pytest.fail(
                f"{archivo.relative_to(RAIZ)} importa '{modulo}'.\n"
                f"Eso no es dominio: {PROHIBIDOS[modulo]}"
            )


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda p: p.name)
def test_solo_importa_lo_permitido(archivo):
    """Mas estricto que el anterior: lista blanca en vez de lista negra.

    Atrapa dependencias que todavia no se le ocurrieron a nadie.
    """
    inesperados = modulos_importados(archivo) - PERMITIDOS
    assert not inesperados, (
        f"{archivo.relative_to(RAIZ)} importa {sorted(inesperados)}, "
        f"que no esta en la lista permitida {sorted(PERMITIDOS)}.\n"
        "Si de verdad corresponde al dominio, agregalo a PERMITIDOS con su motivo."
    )


# --- Capa de aplicacion -------------------------------------------------
#
# La regla cambia segun la capa. El dominio no puede importar NADA externo.
# La aplicacion si puede importar el dominio (lo orquesta), pero sigue sin
# poder tocar infraestructura: si un caso de uso importara scipy, el puerto
# que se escribio para evitarlo no serviria de nada.

APLICACION = RAIZ / "application"
ARCHIVOS_APP = sorted(APLICACION.rglob("*.py")) if APLICACION.exists() else []


@pytest.mark.parametrize("archivo", ARCHIVOS_APP, ids=lambda p: p.name)
def test_la_aplicacion_no_importa_infraestructura(archivo):
    """Los casos de uso y los puertos hablan con abstracciones.

    Si un caso de uso importa scipy directamente, el PricingPort deja de
    tener sentido: se puso justamente para que la aplicacion no sepa como se
    valua una opcion.
    """
    for modulo in modulos_importados(archivo):
        if modulo in PROHIBIDOS:
            pytest.fail(
                f"{archivo.relative_to(RAIZ)} importa '{modulo}'.\n"
                f"La aplicacion depende de puertos, no de implementaciones: "
                f"{PROHIBIDOS[modulo]}"
            )


@pytest.mark.parametrize("archivo", ARCHIVOS_APP, ids=lambda p: p.name)
def test_la_aplicacion_no_importa_la_ui(archivo):
    """Ni presentacion ni adaptadores.

    La dependencia va hacia adentro: ui -> application -> domain. Un import
    en sentido contrario convierte las capas en un adorno.
    """
    prohibidos_por_capa = {"ui", "presentation", "api", "app", "main"}
    importados = modulos_importados(archivo) & prohibidos_por_capa
    assert not importados, (
        f"{archivo.relative_to(RAIZ)} importa {sorted(importados)}. "
        "Las dependencias apuntan hacia adentro: ui -> application -> domain."
    )


# --- Adaptadores de entrada ---------------------------------------------
#
# ui/ y api/ son las dos puertas de entrada del sistema. Pueden usar
# infraestructura, porque son capas externas, pero solo desde su composition
# root: el lugar donde se arma el grafo de dependencias.
#
# Si una ruta de la API o un controlador de la pantalla importaran un
# adaptador concreto, estarian eligiendo la implementacion en vez de recibirla,
# y los puertos dejarian de servir para algo.

RUTAS_API = sorted((RAIZ / "api" / "routes").rglob("*.py")) if (RAIZ / "api").exists() else []


@pytest.mark.parametrize("archivo", RUTAS_API, ids=lambda p: p.name)
def test_las_rutas_de_la_api_no_eligen_implementaciones(archivo):
    """Las rutas reciben casos de uso por inyeccion, no los construyen.

    Solo api/dependencies.py, que es el composition root de esta capa, sabe
    que el pricing es Black-Scholes y que la persistencia es SQLite.
    """
    importados = modulos_importados(archivo)
    assert "infrastructure" not in importados, (
        f"{archivo.relative_to(RAIZ)} importa infrastructure directamente. "
        "Las rutas deben recibir los casos de uso por Depends(), no armarlos."
    )
