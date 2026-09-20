"""
Simulation API Schemas
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from backend.app.core.models import (
    WhatIfType,
    WhatIfSimulationResult,
    PlanDiffResult,
    BudgetCalculationResult,
    ScheduleValidationResult,
)


class TriggerSimulationRequest(BaseModel):
    trip_id: UUID
    type: WhatIfType
    parameters: Dict[str, Any] = Field(default_factory=dict)


class TriggerSimulationResponse(BaseModel):
    success: bool = True
    simulation_id: str
    trip_id: str
    type: WhatIfType
    feasible: bool
    current_summary: Dict[str, Any]
    proposed_summary: Dict[str, Any]
    diff: PlanDiffResult
    budget_before: BudgetCalculationResult
    budget_after: BudgetCalculationResult
    validation_before: ScheduleValidationResult
    validation_after: ScheduleValidationResult
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class ApplySimulationResponse(BaseModel):
    success: bool = True
    trip_id: str
    applied: bool = True
    message: str = "Simulation branch applied to active trip."
    items_count: int


class RejectSimulationResponse(BaseModel):
    success: bool = True
    trip_id: str
    applied: bool = False
    message: str = "Simulation branch discarded. Active trip unchanged."
