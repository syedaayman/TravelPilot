"""
TravelPilot Simulation Service
Orchestrates isolated what-if simulation branches, versioned candidate storage, and safe apply/reject mutations.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from uuid import uuid4

from backend.app.db.supabase_client import get_db
from backend.app.core.models import (
    WhatIfType,
    WhatIfRequest,
    WhatIfSimulationResult,
)
from backend.app.core.simulation_engine import simulation_engine
from backend.app.services.proposal_store import proposal_store, StaleProposalError
from backend.app.api.schemas.simulations import (
    TriggerSimulationRequest,
    TriggerSimulationResponse,
    ApplySimulationResponse,
    RejectSimulationResponse,
)


class SimulationService:
    def trigger_simulation(self, req: TriggerSimulationRequest) -> TriggerSimulationResponse:
        db = get_db()
        trip = db.get_trip(str(req.trip_id))
        if not trip:
            raise KeyError(f"Trip with ID '{req.trip_id}' not found.")

        # Map parameter payload to WhatIfRequest fields
        params = req.parameters or {}
        new_budget = params.get("budget") or params.get("new_budget")
        budget_delta = params.get("budget_delta")
        extra_days = params.get("extra_days") or params.get("days")
        target_destination_id = params.get("target_destination_id") or params.get("destination_id")
        replacement_destination_id = params.get("replacement_destination_id")
        activity_data = params.get("activity") or params.get("activity_data")

        def safe_float(val):
            try:
                if val is None or str(val).strip() == "" or str(val).lower() == "undefined":
                    return None
                return float(val)
            except (ValueError, TypeError):
                return None

        def safe_int(val):
            try:
                if val is None or str(val).strip() == "" or str(val).lower() == "undefined":
                    return None
                return int(float(val))
            except (ValueError, TypeError):
                return None

        what_if_req = WhatIfRequest(
            simulation_id=str(uuid4()),
            trip_id=str(req.trip_id),
            type=req.type,
            new_budget=safe_float(new_budget),
            budget_delta=safe_float(budget_delta),
            extra_days=safe_int(extra_days),
            target_destination_id=target_destination_id,
            replacement_destination_id=replacement_destination_id,
            activity_data=activity_data,
        )

        try:
            # 1. Execute isolated simulation
            result = simulation_engine.simulate_what_if(what_if_req)

            # 2. Store simulation in registry with baseline version hash
            record = proposal_store.store_simulation(result)
        except Exception as e:
            raise ValueError(f"Simulation failed: {str(e)}")

        return TriggerSimulationResponse(
            success=True,
            simulation_id=result.simulation_id,
            trip_id=result.trip_id,
            type=result.type,
            feasible=result.feasible,
            current_summary=result.current_summary,
            proposed_summary=result.proposed_summary,
            diff=result.diff,
            budget_before=result.budget_before,
            budget_after=result.budget_after,
            validation_before=result.validation_before,
            validation_after=result.validation_after,
            warnings=result.warnings,
            errors=result.errors,
        )

    def apply_simulation(self, simulation_id: str) -> ApplySimulationResponse:
        # Verify base version matches active trip state
        record = proposal_store.verify_and_get(simulation_id)
        if record.status == "APPLIED":
            raise ValueError(f"Simulation '{simulation_id}' has already been applied.")
        if record.status == "REJECTED":
            raise ValueError(f"Simulation '{simulation_id}' was rejected.")

        result: WhatIfSimulationResult = record.payload
        if not result.feasible:
            raise ValueError(f"Cannot apply infeasible simulation: {result.errors}")

        res = simulation_engine.apply_simulation(result)
        proposal_store.mark_applied(simulation_id)

        return ApplySimulationResponse(
            success=True,
            trip_id=result.trip_id,
            applied=True,
            message="Simulation branch applied to active trip.",
            items_count=res["items_count"],
        )

    def reject_simulation(self, simulation_id: str) -> RejectSimulationResponse:
        record = proposal_store.get_proposal(simulation_id)
        if not record:
            raise KeyError(f"Simulation '{simulation_id}' not found.")

        result: WhatIfSimulationResult = record.payload
        simulation_engine.reject_simulation(result)
        proposal_store.mark_rejected(simulation_id)

        return RejectSimulationResponse(
            success=True,
            trip_id=result.trip_id,
            applied=False,
            message="Simulation branch discarded. Active trip unchanged.",
        )


simulation_service = SimulationService()
