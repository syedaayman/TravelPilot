"""
Trips API Routes
"""

from fastapi import APIRouter, HTTPException, status

from backend.app.services.trip_service import trip_service
from backend.app.api.schemas.trips import (
    TripPlanRequest,
    TripDetailResponse,
    HotelUpdateRequest,
    ActivityValidateRequest,
    ActivityValidateResponse,
)

router = APIRouter(prefix="/trips", tags=["Trips"])


@router.post(
    "/plan",
    response_model=TripDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Plan a trip (single-city or multi-city)",
    description="Generate a fully scheduled, budgeted, and route-optimized single-city or multi-city itinerary.",
)
def plan_trip(request: TripPlanRequest):
    try:
        result = trip_service.plan_trip(request)
        if hasattr(result, "trip"):
            return result.trip
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to plan trip: {str(e)}",
        )


@router.get(
    "/{trip_id}",
    response_model=TripDetailResponse,
    summary="Get trip details",
    description="Retrieve the complete active trip state including metadata, stops, transport legs, accommodation, day-by-day itinerary, budget breakdown, and schedule validation status.",
)
def get_trip(trip_id: str):
    try:
        return trip_service.get_trip_detail(trip_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trip '{trip_id}' not found.",
        )


@router.post(
    "/{trip_id}/hotel",
    response_model=TripDetailResponse,
    summary="Update hotel selection for a trip stop",
    description=(
        "Swap the selected hotel for a trip stop without regenerating the entire itinerary. "
        "Travel distances and times from the new hotel to the first daily activity are recalculated "
        "using the existing geo-routing engine. Budget and schedule validation are re-run deterministically. "
        "Unaffected itinerary items remain unchanged."
    ),
)
def update_hotel(trip_id: str, request: HotelUpdateRequest):
    try:
        return trip_service.update_hotel(trip_id, request)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hotel update failed: {str(e)}",
        )


@router.post(
    "/{trip_id}/activity/validate",
    response_model=ActivityValidateResponse,
    summary="Dry-run feasibility check for adding an activity",
    description=(
        "Checks whether a proposed activity, restaurant, or experience can be inserted into an "
        "existing trip day without conflicts. Considers schedule overlaps, travel buffers, venue "
        "opening hours, and closed days. Does NOT persist anything. Returns feasible=true/false, "
        "blocking issues, and alternative time suggestions when infeasible."
    ),
)
def validate_activity(trip_id: str, request: ActivityValidateRequest):
    try:
        return trip_service.validate_activity_candidate(trip_id, request)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Activity validation failed: {str(e)}",
        )

