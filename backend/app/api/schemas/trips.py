"""
Trip API Schemas
"""

from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field, model_validator
from backend.app.core.models import BudgetCalculationResult, ScheduleValidationResult


class TripPlanRequest(BaseModel):
    destinations: List[str] = Field(..., min_length=1, description="List of city/destination names.")
    duration_days: Optional[int] = Field(None, gt=0, le=30, description="Inclusive calendar itinerary days.")
    budget: float = Field(..., gt=0, description="Total budget in INR.")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    travelers: int = Field(default=1, gt=0, description="Number of travelers.")
    interests: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    starting_point: Optional[str] = None
    constraints: Optional[str] = None

    @model_validator(mode="after")
    def derive_inclusive_duration(self):
        if self.end_date and not self.start_date:
            raise ValueError("START_DATE_REQUIRED: end_date requires start_date.")
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("INVALID_DATE_RANGE: end_date cannot be before start_date.")
            calendar_days = (self.end_date - self.start_date).days + 1
            if self.duration_days is not None and self.duration_days != calendar_days:
                raise ValueError("DURATION_MISMATCH: duration_days must equal the inclusive date range.")
            self.duration_days = calendar_days
        elif self.duration_days is None:
            raise ValueError("DURATION_REQUIRED: provide duration_days or both start_date and end_date.")
        return self


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
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    map_url: Optional[str] = None
    rating: Optional[float] = None
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


class HotelUpdateRequest(BaseModel):
    """Request body for updating the selected hotel for a trip stop."""
    hotel_id: str = Field(..., description="The ID of the hotel to assign to the relevant trip stop.")
    stop_id: Optional[str] = Field(None, description="Specific stop ID. If omitted, updates the first/only stop.")


class ActivityValidateRequest(BaseModel):
    """
    Dry-run feasibility check for inserting a candidate activity into an existing trip day.
    Does NOT persist anything.
    """
    day_number: int = Field(..., gt=0, description="Target itinerary day number (1-based).")
    start_time: str = Field(..., description="Proposed start time in HH:MM format.")
    end_time: str = Field(..., description="Proposed end time in HH:MM format.")
    place_id: Optional[str] = Field(None, description="Reference place ID if matching an existing place in the DB.")
    custom_title: Optional[str] = Field(None, description="Free-text activity title when no place_id is available.")
    duration_minutes: Optional[int] = Field(None, gt=0, description="Override for activity duration in minutes.")
    trip_stop_id: Optional[str] = Field(None, description="Scope check to a specific stop. Auto-detected from day_number if omitted.")


class ActivityValidateSuggestion(BaseModel):
    """A valid alternative time window where the candidate activity would fit."""
    start_time: str
    end_time: str
    reason: str


class ActivityValidateResponse(BaseModel):
    """Result of a dry-run feasibility check. Does NOT modify the trip."""
    feasible: bool
    issues: List[str] = Field(default_factory=list)
    suggestions: List[ActivityValidateSuggestion] = Field(default_factory=list)
    validation: Optional["ScheduleValidationResult"] = None


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
    nights: int  # = duration_days - 1; computed by backend, never by the LLM
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
