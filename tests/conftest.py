"""Fixtures compartidas por toda la suite."""

import json
from pathlib import Path

import pytest

RUTA_GOLDEN = Path(__file__).parent / "golden_master.json"


@pytest.fixture(scope="session")
def golden():
    """Los valores que producia el codigo original, capturados antes de borrarlo.

    Durante las fases 1 a 5 estos numeros se obtenian importando models.py y
    llamandolo en cada test. Al eliminar ese codigo en la Fase 6 esa
    comparacion deja de ser posible, asi que se congelaron en un archivo.

    Lo que cambia no es el valor de la red de seguridad sino que afirma. Antes
    decia "el codigo nuevo da lo mismo que el viejo"; ahora dice "el codigo da
    estos numeros, que son los que se verificaron contra el original". La
    segunda forma es la que sirve de aca en adelante: el viejo ya no esta para
    volver a preguntarle.

    La unica diferencia deliberada es la probabilidad de Butterfly Call, donde
    el codigo original acumulaba un error de redondeo. Ver
    tests/integration/test_pipeline_completo.py.
    """
    return json.loads(RUTA_GOLDEN.read_text(encoding="utf-8"))
