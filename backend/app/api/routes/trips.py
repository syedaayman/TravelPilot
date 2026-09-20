"""
Trips API Routes
"""

from fastapi import APIRouter, HTTPException, status

from backend.app.services.trip_service import trip_service
from backend.app.api.schemas.trips import (
    TripPlanRequest,
    TripDetailResponse,
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
