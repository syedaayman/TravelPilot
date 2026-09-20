"""
TravelPilot Core Engine Domain Schemas
Pydantic v2 models for budget calculations, schedule validation, routing, and plan diffing.
"""

from datetime import date, time, datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# 1. Budget Models
# ============================================================================

class DailyBudgetBreakdown(BaseModel):
    day_number: int
    scheduled_date: date
    destination_name: str
    accommodation_cost: float = 0.0
    intercity_transport_cost: float = 0.0
    local_transport_cost: float = 0.0
    activities_cost: float = 0.0
    food_cost: float = 0.0
    miscellaneous_cost: float = 0.0
    total_cost: float = 0.0


class BudgetCalculationResult(BaseModel):
    accommodation: float = 0.0
    intercity_transport: float = 0.0
    local_transport: float = 0.0
    activities: float = 0.0
    food: float = 0.0
    miscellaneous: float = 0.0
    total: float = 0.0
    budget: float = 0.0
    remaining: float = 0.0
    variance: float = 0.0  # total - budget (positive = over budget)
    percentage_used: float = 0.0
    within_budget: bool = True
    traveler_count: int = 1
    cost_per_traveler: float = 0.0
    daily_breakdowns: List[DailyBudgetBreakdown] = Field(default_factory=list)


# ============================================================================
# 2. Schedule & Conflict Models
# ============================================================================

class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class ValidationIssueType(str, Enum):
    INVALID_TIME_RANGE = "invalid_time_range"
    OVERLAP = "overlap"
    TRAVEL_CONFLICT = "travel_conflict"
    VENUE_CLOSED_HOURS = "venue_closed_hours"
    VENUE_CLOSED_DAY = "venue_closed_day"
    DATE_OUT_OF_BOUNDS = "date_out_of_bounds"
    STOP_BOUNDARY_VIOLATION = "stop_boundary_violation"
    TRANSPORT_CONFLICT = "transport_conflict"
    INSUFFICIENT_BUFFER = "insufficient_buffer"


class ValidationIssue(BaseModel):
    type: ValidationIssueType
    severity: ValidationSeverity
    message: str
    item_id: Optional[str] = None
    conflicting_item_id: Optional[str] = None
    day_number: Optional[int] = None
    suggested_fix: Optional[str] = None


class ScheduleValidationResult(BaseModel):
    valid: bool
    errors: List[ValidationIssue] = Field(default_factory=list)
    warnings: List[ValidationIssue] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


# ============================================================================
# 3. Geo & Routing Models
# ============================================================================

class GeoPoint(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    id: Optional[str] = None
    name: Optional[str] = None


class RoutingMode(str, Enum):
    WALK = "walk"
    BICYCLE = "bicycle"
    CAR = "car"
    CAB = "cab"
    BUS = "bus"
    METRO = "metro"
    TRAIN = "train"
    FLIGHT = "flight"


class TravelEstimate(BaseModel):
    origin: GeoPoint
    destination: GeoPoint
    mode: RoutingMode
    distance_km: float
    duration_minutes: int
    is_estimate: bool = True
    assumed_speed_kmh: float
    notes: Optional[str] = None


class RouteSegment(BaseModel):
    origin: GeoPoint
    destination: GeoPoint
    distance_km: float
    duration_minutes: int
    mode: RoutingMode


class RouteSummary(BaseModel):
    ordered_points: List[GeoPoint]
    total_distance_km: float
    total_duration_minutes: int
    mode: RoutingMode
    segments: List[RouteSegment] = Field(default_factory=list)


# ============================================================================
# 4. Plan Diff Models
# ============================================================================

class FieldChange(BaseModel):
    before: Any
    after: Any


class ItemModification(BaseModel):
    item_id: str
    title: Optional[str] = None
    field_changes: Dict[str, FieldChange]


class LegModification(BaseModel):
    leg_id: str
    field_changes: Dict[str, FieldChange]


class PlanDiffResult(BaseModel):
    added_items: List[Dict[str, Any]] = Field(default_factory=list)
    removed_items: List[Dict[str, Any]] = Field(default_factory=list)
    modified_items: List[ItemModification] = Field(default_factory=list)
    unchanged_items: List[Dict[str, Any]] = Field(default_factory=list)
    added_legs: List[Dict[str, Any]] = Field(default_factory=list)
    removed_legs: List[Dict[str, Any]] = Field(default_factory=list)
    modified_legs: List[LegModification] = Field(default_factory=list)
    budget_before: float = 0.0
    budget_after: float = 0.0
    budget_delta: float = 0.0
    travel_distance_delta_km: float = 0.0
    summary: str = ""


# ============================================================================
# 5. Disruption Management Models
# ============================================================================

class CoreDisruptionType(str, Enum):
    VENUE_CLOSED = "VENUE_CLOSED"
    TRANSPORT_DELAY = "TRANSPORT_DELAY"
    TRANSPORT_CANCELLED = "TRANSPORT_CANCELLED"
    WEATHER_ALERT = "WEATHER_ALERT"
    BOOKING_UNAVAILABLE = "BOOKING_UNAVAILABLE"
    BUDGET_REDUCTION = "BUDGET_REDUCTION"
    SCHEDULE_CONFLICT = "SCHEDULE_CONFLICT"


class DisruptionRequest(BaseModel):
    disruption_id: str = Field(default_factory=lambda: f"disr-{int(datetime.now(timezone.utc).timestamp())}")
    trip_id: str
    type: CoreDisruptionType
    affected_item_id: Optional[str] = None
    affected_leg_id: Optional[str] = None
    affected_place_id: Optional[str] = None
    effective_date: Optional[date] = None
    effective_time: Optional[str] = None
    delay_minutes: Optional[int] = None
    reason: Optional[str] = None
    reduction_amount: Optional[float] = None
    replacement_budget: Optional[float] = None
    weather_categories: List[str] = Field(default_factory=lambda: ["outdoor", "beach"])
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DisruptionAnalysisResult(BaseModel):
    disruption_id: str
    trip_id: str
    type: CoreDisruptionType
    affected_items: List[Dict[str, Any]] = Field(default_factory=list)
    affected_legs: List[Dict[str, Any]] = Field(default_factory=list)
    downstream_affected_items: List[Dict[str, Any]] = Field(default_factory=list)
    available_windows: List[Dict[str, Any]] = Field(default_factory=list)
    severity: str = "medium"
    required_replan: bool = True
    reasons: List[str] = Field(default_factory=list)


class CandidateAlternative(BaseModel):
    place_id: str
    name: str
    category: str
    rating: float
    entry_fee: float
    distance_km: float = 0.0
    travel_time_from_prev_mins: int = 0
    travel_time_to_next_mins: int = 0
    open_time: str
    close_time: str
    is_feasible: bool = True
    score: float = 0.0
    score_breakdown: Dict[str, float] = Field(default_factory=dict)


class ProposedReplan(BaseModel):
    replan_id: str = Field(default_factory=lambda: f"replan-{int(datetime.now(timezone.utc).timestamp())}")
    trip_id: str
    disruption_type: CoreDisruptionType
    feasible: bool = True
    proposed_items: List[Dict[str, Any]] = Field(default_factory=list)
    proposed_stops: List[Dict[str, Any]] = Field(default_factory=list)
    proposed_legs: List[Dict[str, Any]] = Field(default_factory=list)
    diff: PlanDiffResult
    budget_before: BudgetCalculationResult
    budget_after: BudgetCalculationResult
    validation_before: ScheduleValidationResult
    validation_after: ScheduleValidationResult
    summary: str = ""
    candidates_evaluated: List[CandidateAlternative] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# 6. What-If Simulation Models
# ============================================================================

class WhatIfType(str, Enum):
    BUDGET_CHANGE = "BUDGET_CHANGE"
    ADD_DAY = "ADD_DAY"
    REMOVE_DESTINATION = "REMOVE_DESTINATION"
    REPLACE_DESTINATION = "REPLACE_DESTINATION"
    ADD_ACTIVITY = "ADD_ACTIVITY"


class WhatIfRequest(BaseModel):
    simulation_id: str = Field(default_factory=lambda: f"sim-{int(datetime.now(timezone.utc).timestamp())}")
    trip_id: str
    type: WhatIfType
    budget_delta: Optional[float] = None
    new_budget: Optional[float] = None
    extra_days: Optional[int] = None
    target_destination_id: Optional[str] = None
    replacement_destination_id: Optional[str] = None
    activity_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WhatIfSimulationResult(BaseModel):
    simulation_id: str
    trip_id: str
    type: WhatIfType
    success: bool = True
    feasible: bool = True
    current_summary: Dict[str, Any] = Field(default_factory=dict)
    proposed_summary: Dict[str, Any] = Field(default_factory=dict)
    proposed_items: List[Dict[str, Any]] = Field(default_factory=list)
    proposed_stops: List[Dict[str, Any]] = Field(default_factory=list)
    proposed_legs: List[Dict[str, Any]] = Field(default_factory=list)
    diff: PlanDiffResult
    budget_before: BudgetCalculationResult
    budget_after: BudgetCalculationResult
    validation_before: ScheduleValidationResult
    validation_after: ScheduleValidationResult
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

