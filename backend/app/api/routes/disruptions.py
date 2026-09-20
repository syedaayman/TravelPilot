"""
Disruptions API Routes
"""

from fastapi import APIRouter, HTTPException, status

from backend.app.services.disruption_service import disruption_service
from backend.app.services.proposal_store import StaleProposalError
from backend.app.api.schemas.disruptions import (
    TriggerDisruptionRequest,
    TriggerDisruptionResponse,
    ApplyReplanResponse,
    RejectReplanResponse,
)

router = APIRouter(prefix="/disruptions", tags=["Disruptions"])


@router.post(
    "/trigger",
    response_model=TriggerDisruptionResponse,
    summary="Trigger disruption analysis and replanning",
    description="Analyze a disruption event, score candidate alternatives, and return a candidate replan proposal in an isolated branch without mutating active trip state.",
)
def trigger_disruption(request: TriggerDisruptionRequest):
    try:
        return disruption_service.trigger_disruption(request)
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
    "/{replan_id}/apply",
    response_model=ApplyReplanResponse,
    summary="Apply proposed replan to active trip",
    description="Mutating operation: commits a verified proposed replan to the active trip state if not stale.",
)
def apply_replan(replan_id: str):
    try:
        return disruption_service.apply_replan(replan_id)
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
    "/{replan_id}/reject",
    response_model=RejectReplanResponse,
    summary="Reject proposed replan",
    description="Discards a proposed replan. Active trip state remains completely untouched.",
)
def reject_replan(replan_id: str):
    try:
        return disruption_service.reject_replan(replan_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
