"""
TravelPilot Disruption Service
Orchestrates disruption impact analysis, candidate replanning, proposal caching, and safe apply/reject mutations.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from uuid import uuid4

from backend.app.db.supabase_client import get_db
from backend.app.core.models import (
    CoreDisruptionType,
    DisruptionRequest,
    ProposedReplan,
)
from backend.app.core.disruption_engine import disruption_engine
from backend.app.services.proposal_store import proposal_store, StaleProposalError
from backend.app.api.schemas.disruptions import (
    TriggerDisruptionRequest,
    TriggerDisruptionResponse,
    ApplyReplanResponse,
    RejectReplanResponse,
)


class DisruptionService:
    def trigger_disruption(self, req: TriggerDisruptionRequest) -> TriggerDisruptionResponse:
        db = get_db()
        trip = db.get_trip(req.trip_id)
        if not trip:
            raise KeyError(f"Trip with ID '{req.trip_id}' not found.")

        # Convert to core DisruptionRequest
        disruption_req = DisruptionRequest(
            disruption_id=str(uuid4()),
            trip_id=req.trip_id,
            type=req.type,
            affected_item_id=req.affected_item_id,
            affected_leg_id=req.affected_leg_id,
            affected_place_id=req.affected_place_id,
            effective_date=req.effective_date,
            effective_time=req.effective_time,
            delay_minutes=req.delay_minutes,
            reason=req.reason,
            reduction_amount=req.reduction_amount,
            weather_categories=req.weather_categories,
        )

        # 1. Read-only impact analysis
        analysis = disruption_engine.analyze_disruption(disruption_req)

        # 2. Replan candidate branch
        replan = disruption_engine.replan_disruption(disruption_req)

        # 3. Store proposal in registry with baseline version hash
        record = proposal_store.store_replan(replan)

        return TriggerDisruptionResponse(
            success=True,
            trip_id=req.trip_id,
            disruption_analysis=analysis,
            proposed_replan=replan,
            diff=replan.diff,
            replan_id=replan.replan_id,
        )

    def apply_replan(self, replan_id: str) -> ApplyReplanResponse:
        # Verify base version matches active trip state
        record = proposal_store.verify_and_get(replan_id)
        if record.status == "APPLIED":
            raise ValueError(f"Proposal '{replan_id}' has already been applied.")
        if record.status == "REJECTED":
            raise ValueError(f"Proposal '{replan_id}' was rejected.")

        replan: ProposedReplan = record.payload
        result = disruption_engine.apply_replan(replan)
        proposal_store.mark_applied(replan_id)

        return ApplyReplanResponse(
            success=True,
            trip_id=replan.trip_id,
            message="Disruption replan applied successfully.",
            applied_items_count=result["applied_items_count"],
            applied_legs_count=result["applied_legs_count"],
            diff=replan.diff,
        )

    def reject_replan(self, replan_id: str) -> RejectReplanResponse:
        record = proposal_store.get_proposal(replan_id)
        if not record:
            raise KeyError(f"Replan proposal '{replan_id}' not found.")

        replan: ProposedReplan = record.payload
        disruption_engine.reject_replan(replan)
        proposal_store.mark_rejected(replan_id)

        return RejectReplanResponse(
            success=True,
            trip_id=replan.trip_id,
            message="Proposed replan discarded. Active trip unchanged.",
        )


disruption_service = DisruptionService()
