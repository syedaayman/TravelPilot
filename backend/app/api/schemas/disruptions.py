"""
Disruption API Schemas
"""

from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field
from backend.app.core.models import (
    CoreDisruptionType,
    DisruptionAnalysisResult,
    ProposedReplan,
    PlanDiffResult,
    BudgetCalculationResult,
    ScheduleValidationResult,
)


class TriggerDisruptionRequest(BaseModel):
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


class TriggerDisruptionResponse(BaseModel):
    success: bool = True
    trip_id: str
    disruption_analysis: DisruptionAnalysisResult
    proposed_replan: ProposedReplan
    diff: PlanDiffResult
    replan_id: str


class ApplyReplanResponse(BaseModel):
    success: bool = True
    trip_id: str
    message: str = "Disruption replan applied successfully."
    applied_items_count: int
    applied_legs_count: int
    diff: PlanDiffResult


class RejectReplanResponse(BaseModel):
    success: bool = True
    trip_id: str
    message: str = "Proposed replan discarded. Active trip unchanged."
