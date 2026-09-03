"""Aplicacion FastAPI: la misma logica, expuesta por HTTP."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from api.routes import simulations, strategies

app = FastAPI(
    title="Calculadora de Estrategias de Opciones",
    description=(
        "Calcula el perfil de riesgo de estrategias de opciones y guarda "
        "simulaciones. Expone los mismos casos de uso que la interfaz de "
        "escritorio, sobre exactamente el mismo dominio."
    ),
    version="1.0.0",
)

app.include_router(strategies.router, prefix="/api")
app.include_router(simulations.router, prefix="/api")


@app.exception_handler(ValueError)
async def errores_del_dominio(request: Request, exc: ValueError) -> JSONResponse:
    """Convierte una invariante del dominio en un 422.

    El dominio lanza ValueError cuando le llega algo que no acepta: un strike
    negativo, una estrategia sin patas, una volatilidad en cero. Sin este
    manejador esos casos saldrian como 500, que le dice al cliente "el
    servidor esta roto" cuando en realidad el pedido estaba mal.

    Es la misma traduccion que hace FormError en la interfaz de escritorio.
    Cada adaptador de entrada convierte los errores del dominio al idioma de
    su frontera: la pantalla los muestra en castellano, la API los devuelve
    como 422.

    Los esquemas de Pydantic ya rechazan casi todo esto antes de llegar al
    dominio. Este manejador cubre lo que se les escapa — por ejemplo una
    combinacion de campos individualmente validos que el dominio no acepta.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


@app.get("/api/health", tags=["estado"])
def estado():
    return {"status": "ok"}
