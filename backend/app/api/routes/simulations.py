"""
Simulations API Routes
"""

from fastapi import APIRouter, HTTPException, status

from backend.app.services.simulation_service import simulation_service
from backend.app.services.proposal_store import StaleProposalError
from backend.app.api.schemas.simulations import (
    TriggerSimulationRequest,
    TriggerSimulationResponse,
    ApplySimulationResponse,
    RejectSimulationResponse,
)

router = APIRouter(prefix="/simulations", tags=["Simulations"])


@router.post(
    "/what-if",
    response_model=TriggerSimulationResponse,
    summary="Run what-if simulation",
    description="Simulates hypothetical changes (budget change, add day, remove/replace destination, add activity) in an isolated branch without mutating active trip state.",
)
def run_what_if_simulation(request: TriggerSimulationRequest):
    try:
        return simulation_service.trigger_simulation(request)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/{simulation_id}/apply",
    response_model=ApplySimulationResponse,
    summary="Apply simulation branch to active trip",
    description="Mutating operation: commits a verified simulation branch to the active trip state if not stale and feasible.",
)
def apply_simulation(simulation_id: str):
    try:
        return simulation_service.apply_simulation(simulation_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except StaleProposalError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/{simulation_id}/reject",
    response_model=RejectSimulationResponse,
    summary="Reject simulation branch",
    description="Discards a simulation branch. Active trip state remains completely untouched.",
)
def reject_simulation(simulation_id: str):
    try:
        return simulation_service.reject_simulation(simulation_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
