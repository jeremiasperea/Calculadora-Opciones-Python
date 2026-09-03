"""Endpoints de simulaciones guardadas."""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.dependencies import get_calculate, get_library
from api.schemas import (
    CalculationOut, LegIn, MarketIn, SaveSimulationRequest,
    SavedSimulationOut, SimulationSummaryOut,
)
from application.dtos.snapshot import SimulationSnapshot
from application.use_cases.calculate_strategy import CalculateStrategyUseCase
from application.use_cases.simulation_library import SimulationLibraryUseCase

router = APIRouter(prefix="/simulations", tags=["simulaciones"])


@router.get("", response_model=list[SimulationSummaryOut])
def listar(biblioteca: SimulationLibraryUseCase = Depends(get_library)):
    """Resumenes de las simulaciones guardadas, de la mas nueva a la mas vieja.

    Devuelve resumenes y no simulaciones completas: cada una guarda 401 pares
    de numeros, y una lista de cien seria una respuesta de varios megabytes
    para mostrar cinco columnas.
    """
    return [
        SimulationSummaryOut(
            id=s.id, name=s.name, created_at=s.created_at.isoformat(),
            description=s.description, net_premium=s.net_premium,
        )
        for s in biblioteca.list_all()
    ]


@router.post("", response_model=SavedSimulationOut,
             status_code=status.HTTP_201_CREATED)
def guardar(
    pedido: SaveSimulationRequest,
    biblioteca: SimulationLibraryUseCase = Depends(get_library),
    calcular: CalculateStrategyUseCase = Depends(get_calculate),
):
    """Guarda una simulacion.

    El resultado se recalcula en el servidor en lugar de aceptarlo del
    cliente. Aceptarlo permitiria guardar una simulacion cuyos numeros no
    correspondan a sus parametros, y esa inconsistencia despues no hay forma
    de detectarla: los dos valores parecen igual de validos.
    """
    estrategia = pedido.strategy()
    mercado = pedido.market.to_domain()
    rango = pedido.price_range.to_domain() if pedido.price_range else None

    snapshot = SimulationSnapshot(
        estrategia, mercado, calcular.execute(estrategia, mercado, rango)
    )
    sim_id = biblioteca.save(pedido.name, snapshot)
    return _a_respuesta(biblioteca.load(sim_id))


@router.get("/{sim_id}", response_model=SavedSimulationOut)
def obtener(sim_id: str, biblioteca: SimulationLibraryUseCase = Depends(get_library)):
    try:
        return _a_respuesta(biblioteca.load(sim_id))
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe la simulacion '{sim_id}'",
        ) from None


@router.delete("/{sim_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(sim_id: str, biblioteca: SimulationLibraryUseCase = Depends(get_library)):
    try:
        biblioteca.delete(sim_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe la simulacion '{sim_id}'",
        ) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _a_respuesta(guardada) -> SavedSimulationOut:
    estrategia = guardada.snapshot.strategy
    mercado = guardada.snapshot.market
    return SavedSimulationOut(
        id=guardada.id,
        name=guardada.name,
        created_at=guardada.created_at.isoformat(),
        multiplier=estrategia.multiplier,
        legs=[
            LegIn(option_type=leg.option_type.value, side=leg.side.value,
                  quantity=leg.quantity, strike=leg.strike, premium=leg.premium)
            for leg in estrategia.legs
        ],
        market=MarketIn(
            spot=mercado.spot, days_to_expiry=mercado.days_to_expiry,
            volatility=mercado.volatility, rate=mercado.rate,
            dividend_yield=mercado.dividend_yield,
        ),
        result=CalculationOut.from_domain(guardada.snapshot.result),
    )
