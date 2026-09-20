from backend.app.api.schemas.common import ErrorDetail, APIErrorResponse, HealthResponse
from backend.app.api.schemas.destinations import (
    DestinationSummaryResponse,
    DestinationListResponse,
    PlaceResponse,
    HotelResponse,
    RestaurantResponse,
    DestinationDetailResponse,
)
from backend.app.api.schemas.trips import (
    TripPlanRequest,
    TripPlanResponse,
    TripDetailResponse,
    TripStopDetail,
    TransportLegDetail,
    ItineraryItemDetail,
    HotelUpdateRequest,
    ActivityValidateRequest,
    ActivityValidateResponse,
    ActivityValidateSuggestion,
)
from backend.app.api.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentEventItem,
    AgentEventsResponse,
)
from backend.app.api.schemas.disruptions import (
    TriggerDisruptionRequest,
    TriggerDisruptionResponse,
    ApplyReplanResponse,
    RejectReplanResponse,
)
from backend.app.api.schemas.simulations import (
    TriggerSimulationRequest,
    TriggerSimulationResponse,
    ApplySimulationResponse,
    RejectSimulationResponse,
)

__all__ = [
    "ErrorDetail",
    "APIErrorResponse",
    "HealthResponse",
    "DestinationSummaryResponse",
    "DestinationListResponse",
    "PlaceResponse",
    "HotelResponse",
    "RestaurantResponse",
    "DestinationDetailResponse",
    "TripPlanRequest",
    "TripPlanResponse",
    "TripDetailResponse",
    "TripStopDetail",
    "TransportLegDetail",
    "ItineraryItemDetail",
    "HotelUpdateRequest",
    "ActivityValidateRequest",
    "ActivityValidateResponse",
    "ActivityValidateSuggestion",
    "AgentChatRequest",
    "AgentChatResponse",
    "AgentEventItem",
    "AgentEventsResponse",
    "TriggerDisruptionRequest",
    "TriggerDisruptionResponse",
    "ApplyReplanResponse",
    "RejectReplanResponse",
    "TriggerSimulationRequest",
    "TriggerSimulationResponse",
    "ApplySimulationResponse",
    "RejectSimulationResponse",
]
