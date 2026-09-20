"""
Destination API Schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DestinationSummaryResponse(BaseModel):
    id: str
    name: str
    state_province: Optional[str] = None
    country: str = "India"
    latitude: float
    longitude: float
    ideal_duration_days: int = 3
    average_daily_cost: float = 3000.0
    hero_image_url: Optional[str] = None
    description: Optional[str] = None


class DestinationListResponse(BaseModel):
    items: List[DestinationSummaryResponse]
    count: int


class PlaceResponse(BaseModel):
    id: str
    destination_id: str
    name: str
    category: str
    description: Optional[str] = None
    entry_fee: float = 0.0
    typical_duration_minutes: int = 60
    rating: float = 4.0
    open_time: str = "09:00"
    close_time: str = "18:00"
    closed_days: List[int] = Field(default_factory=list)
    latitude: float
    longitude: float
    image_url: Optional[str] = None


class HotelResponse(BaseModel):
    id: str
    destination_id: str
    name: str
    tier: str
    price_per_night: float
    rating: float = 4.0
    amenities: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    address: Optional[str] = None


class RestaurantResponse(BaseModel):
    id: str
    destination_id: str
    name: str
    cuisine: str
    price_level: Optional[str] = None
    average_cost_per_person: float = 350.0
    open_time: str = "11:00"
    close_time: str = "23:00"
    rating: float = 4.0


class TransportConnectionResponse(BaseModel):
    id: str
    origin_id: str
    destination_id: str
    mode: str
    carrier: Optional[str] = None
    code: Optional[str] = None
    estimated_cost: float
    typical_duration_minutes: int
    frequency: Optional[str] = None


class DestinationDetailResponse(BaseModel):
    destination: DestinationSummaryResponse
    places: List[PlaceResponse] = Field(default_factory=list)
    hotels: List[HotelResponse] = Field(default_factory=list)
    restaurants: List[RestaurantResponse] = Field(default_factory=list)
    transport_connections: List[TransportConnectionResponse] = Field(default_factory=list)
