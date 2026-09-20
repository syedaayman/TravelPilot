"""
TravelPilot Pydantic Domain Entities (Pydantic v2)
Unified schemas for reference and operational data.
"""

from datetime import date, time, datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Enums
# ============================================================================

class HotelTier(str, Enum):
    BUDGET = "budget"
    MID_RANGE = "mid-range"
    LUXURY = "luxury"
    HOSTEL = "hostel"


class PriceLevel(str, Enum):
    BUDGET = "budget"
    MID_RANGE = "mid-range"
    FINE_DINING = "fine-dining"


class TransportMode(str, Enum):
    TRAIN = "train"
    FLIGHT = "flight"
    BUS = "bus"
    CAB = "cab"
    LOCAL_TRANSIT = "local_transit"


class TripStatus(str, Enum):
    PLANNING = "planning"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    DISRUPTED = "disrupted"


class TransportLegStatus(str, Enum):
    SCHEDULED = "scheduled"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class ItemType(str, Enum):
    PLACE = "place"
    RESTAURANT = "restaurant"
    TRANSPORT = "transport"
    CUSTOM = "custom"
    HOTEL_CHECKIN = "hotel_checkin"
    HOTEL_CHECKOUT = "hotel_checkout"


class ItemStatus(str, Enum):
    PLANNED = "planned"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"
    ALTERNATIVE_SELECTED = "alternative_selected"


class DisruptionType(str, Enum):
    FLIGHT_DELAYED = "flight_delayed"
    FLIGHT_CANCELLED = "flight_cancelled"
    TRAIN_DELAYED = "train_delayed"
    PLACE_CLOSED = "place_closed"
    BAD_WEATHER = "bad_weather"
    BUDGET_OVERRUN = "budget_overrun"
    USER_REQUEST = "user_request"


class DisruptionSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DisruptionStatus(str, Enum):
    ACTIVE = "active"
    RESOLVING = "resolving"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class AgentEventType(str, Enum):
    REQUEST_RECEIVED = "request_received"
    PLANNING_STARTED = "planning_started"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    VALIDATION = "validation"
    DECISION = "decision"
    STATE_UPDATE = "state_update"
    DISRUPTION_DETECTED = "disruption_detected"
    ALTERNATIVE_FOUND = "alternative_found"
    REPLAN_STARTED = "replan_started"
    REPLAN_COMPLETED = "replan_completed"
    SIMULATION_STARTED = "simulation_started"
    SIMULATION_COMPLETED = "simulation_completed"
    ERROR = "error"


# ============================================================================
# Reference Entities (Catalogue)
# ============================================================================

class Destination(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    state_province: Optional[str] = None
    country: str = "India"
    latitude: float
    longitude: float
    timezone: str = "Asia/Kolkata"
    description: Optional[str] = None
    ideal_duration_days: int = 3
    best_season: Optional[str] = None
    average_daily_cost: float = 3000.0
    hero_image_url: Optional[str] = None
    source: str = "curated_static"
    last_verified_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class Place(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    destination_id: str
    name: str
    category: str # 'historical', 'nature', 'religious', 'beach', 'shopping', 'entertainment', 'museum'
    description: Optional[str] = None
    latitude: float
    longitude: float
    open_time: str = "09:00:00"
    close_time: str = "18:00:00"
    closed_days: List[int] = Field(default_factory=list) # 0=Sun, 1=Mon, ..., 6=Sat
    entry_fee: float = 0.0
    foreign_entry_fee: float = 0.0
    typical_duration_minutes: int = 120
    rating: float = 4.5
    tags: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    source: str = "curated_static"
    last_verified_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class Hotel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    destination_id: str
    name: str
    tier: HotelTier = HotelTier.MID_RANGE
    price_per_night: float
    latitude: float
    longitude: float
    address: Optional[str] = None
    rating: float = 4.2
    amenities: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    source: str = "curated_static"
    last_verified_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class Restaurant(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    destination_id: str
    name: str
    cuisine: str
    price_level: PriceLevel = PriceLevel.MID_RANGE
    average_cost_per_person: float = 350.0
    latitude: float
    longitude: float
    open_time: str = "11:00:00"
    close_time: str = "23:00:00"
    specialties: List[str] = Field(default_factory=list)
    rating: float = 4.3
    image_url: Optional[str] = None
    source: str = "curated_static"
    last_verified_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class TransportOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    origin_destination_id: str
    dest_destination_id: str
    mode: TransportMode
    carrier: Optional[str] = None
    code: Optional[str] = None
    typical_duration_minutes: int
    estimated_cost: float
    frequency_per_day: int = 2
    departure_schedules: List[str] = Field(default_factory=list) # e.g. ["06:00:00", "14:30:00"]
    source: str = "curated_static"
    last_verified_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# Operational Entities (User Trips & State)
# ============================================================================

class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    email: Optional[str] = None
    full_name: Optional[str] = None
    preferences: Dict[str, Any] = Field(default_factory=lambda: {
        "interests": [],
        "budget_tier": "mid-range",
        "pace": "moderate"
    })
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class Trip(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: Optional[str] = None
    title: str
    start_date: date
    end_date: date
    total_budget: float
    currency: str = "INR"
    status: TripStatus = TripStatus.PLANNING
    traveler_count: int = 1
    interests: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class TripStop(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    trip_id: str
    destination_id: str
    order_index: int = 0
    arrival_date: date
    departure_date: date
    stop_budget: float = 0.0
    hotel_id: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class TransportLeg(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    trip_id: str
    origin_stop_id: str
    destination_stop_id: str
    mode: TransportMode
    carrier: Optional[str] = None
    booking_reference: Optional[str] = None
    departure_time: datetime
    arrival_time: datetime
    cost: float = 0.0
    status: TransportLegStatus = TransportLegStatus.SCHEDULED
    notes: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class ItineraryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    trip_stop_id: str
    item_type: ItemType = ItemType.PLACE
    place_id: Optional[str] = None
    restaurant_id: Optional[str] = None
    custom_title: Optional[str] = None
    day_number: int = 1
    scheduled_date: date
    start_time: str # "HH:MM:SS" or "HH:MM"
    end_time: str   # "HH:MM:SS" or "HH:MM"
    cost: float = 0.0
    status: ItemStatus = ItemStatus.PLANNED
    notes: Optional[str] = None
    is_backup: bool = False
    travel_time_from_prev_minutes: int = 0
    travel_distance_km: float = 0.0
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class Disruption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    trip_id: str
    disruption_type: DisruptionType
    severity: DisruptionSeverity = DisruptionSeverity.MEDIUM
    affected_item_id: Optional[str] = None
    affected_leg_id: Optional[str] = None
    description: str
    status: DisruptionStatus = DisruptionStatus.ACTIVE
    suggested_action: Dict[str, Any] = Field(default_factory=dict)
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentEvent(BaseModel):
    """
    Structured Agent Observability Event.
    Strictly NO hidden private chain-of-thought or model internals.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    trip_id: str
    event_type: AgentEventType
    tool_name: Optional[str] = None
    input_summary: Optional[str] = None
    result_summary: Optional[str] = None
    status: str = "success" # 'success', 'warning', 'error', 'info'
    duration_ms: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

