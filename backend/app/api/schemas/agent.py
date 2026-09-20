"""
Agent API Schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    trip_id: str
    message: str = Field(..., min_length=1)


class AgentChatResponse(BaseModel):
    success: bool = True
    trip_id: str
    reply: str
    updated_trip: Optional[Dict[str, Any]] = None
    executed_tools: List[str] = Field(default_factory=list)


class AgentEventItem(BaseModel):
    id: str
    event_type: str
    tool_name: Optional[str] = None
    input_summary: Optional[str] = None
    result_summary: Optional[str] = None
    status: str
    duration_ms: int
    created_at: str


class AgentEventsResponse(BaseModel):
    trip_id: str
    events: List[AgentEventItem]
    count: int
