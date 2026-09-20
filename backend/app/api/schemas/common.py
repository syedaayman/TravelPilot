"""
Common API Schemas & Error Models
"""

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class APIErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "travelpilot"
    environment: str = "development"
    database_mode: str = "in_memory_mock"
    reference_destinations_count: int = 0
    reference_places_count: int = 0
