"""Endpoints de calculo y plantillas."""

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_calculate, get_templates
from api.schemas import CalculateRequest, CalculationOut, LegIn, TemplateOut
from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from application.use_cases.load_template import LoadTemplateUseCase

router = APIRouter(tags=["estrategias"])


@router.get("/templates", response_model=list[str])
def listar_plantillas(casos: LoadTemplateUseCase = Depends(get_templates)):
    """Nombres de las estrategias predefinidas."""
    return casos.list_available()


@router.get("/templates/{nombre}", response_model=TemplateOut)
def obtener_plantilla(
    nombre: str, casos: LoadTemplateUseCase = Depends(get_templates)
):
    try:
        estrategia = casos.execute(nombre)
    except KeyError:
        # El caso de uso lanza KeyError; traducirlo a 404 es trabajo de esta
        # capa. El caso de uso no sabe que existe HTTP y no tiene por que.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe la plantilla '{nombre}'",
        ) from None

    return TemplateOut(
        name=nombre,
        legs=[
            LegIn(option_type=leg.option_type.value, side=leg.side.value,
                  quantity=leg.quantity, strike=leg.strike, premium=leg.premium)
            for leg in estrategia.legs
        ],
    )


@router.post("/calculate", response_model=CalculationOut)
def calcular(
    pedido: CalculateRequest,
    casos: CalculateStrategyUseCase = Depends(get_calculate),
):
    """Perfil de riesgo de una estrategia.

    Fijarse en lo corto que es: arma los objetos del dominio, llama al caso de
    uso y traduce la respuesta. Ni una cuenta. Toda la logica ya estaba
    escrita y probada antes de que esta capa existiera.
    """
    rango = pedido.price_range.to_domain() if pedido.price_range else None
    resultado = casos.execute(pedido.strategy(), pedido.market.to_domain(), rango)
    return CalculationOut.from_domain(resultado)
