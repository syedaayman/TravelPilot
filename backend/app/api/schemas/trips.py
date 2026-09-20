"""
Trip API Schemas
"""

from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field
from backend.app.core.models import BudgetCalculationResult, ScheduleValidationResult


class TripPlanRequest(BaseModel):
    destinations: List[str] = Field(..., min_length=1, description="List of city/destination names.")
    duration_days: int = Field(..., gt=0, le=30, description="Total days for the trip.")
    budget: float = Field(..., gt=0, description="Total budget in INR.")
    start_date: Optional[date] = None
    travelers: int = Field(default=1, gt=0, description="Number of travelers.")
    interests: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    starting_point: Optional[str] = None
    constraints: Optional[str] = None


class ItineraryItemDetail(BaseModel):
    id: str
    trip_stop_id: str
    item_type: str
    place_id: Optional[str] = None
    custom_title: Optional[str] = None
    day_number: int
    scheduled_date: str
    start_time: str
    end_time: str
    cost: float
    status: str
    notes: Optional[str] = None
    travel_time_from_prev_minutes: int = 0
    travel_distance_km: float = 0.0


class TripStopDetail(BaseModel):
    id: str
    trip_id: str
    destination_id: str
    destination_name: str
    order_index: int
    arrival_date: str
    departure_date: str
    stop_budget: float
    hotel: Optional[Dict[str, Any]] = None


class TransportLegDetail(BaseModel):
    id: str
    trip_id: str
    origin_stop_id: str
    destination_stop_id: str
    mode: str
    carrier: Optional[str] = None
    departure_time: str
    arrival_time: str
    cost: float
    status: str


class TripDetailResponse(BaseModel):
    id: str
    title: str
    start_date: str
    end_date: str
    total_budget: float
    currency: str = "INR"
    status: str
    traveler_count: int
    duration_days: int
    interests: List[str]
    stops: List[TripStopDetail]
    transport_legs: List[TransportLegDetail]
    itinerary: List[ItineraryItemDetail]
    budget: BudgetCalculationResult
    validation: ScheduleValidationResult
    version_hash: str


class TripPlanResponse(BaseModel):
    success: bool = True
    trip: TripDetailResponse
    agent_reasoning: str
