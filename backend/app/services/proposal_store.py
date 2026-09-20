"""
TravelPilot In-Memory Proposal Registry & Stale Proposal Protection
Tracks proposed replans and simulations with state version hashing to prevent race conditions or stale overwrites.
"""

import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from backend.app.db.supabase_client import get_db
from backend.app.core.models import ProposedReplan, WhatIfSimulationResult


class StaleProposalError(Exception):
    def __init__(self, message: str = "Active trip state has changed since this proposal was created."):
        super().__init__(message)
        self.message = message


class ProposalRecord:
    def __init__(
        self,
        proposal_id: str,
        trip_id: str,
        proposal_type: str, # 'replan' or 'simulation'
        base_version_hash: str,
        payload: Any,
        status: str = "PROPOSED", # 'PROPOSED', 'APPLIED', 'REJECTED'
    ):
        self.proposal_id = proposal_id
        self.trip_id = trip_id
        self.proposal_type = proposal_type
        self.base_version_hash = base_version_hash
        self.payload = payload
        self.status = status
        self.created_at = datetime.now(timezone.utc)


class ProposalStore:
    def __init__(self):
        self._proposals: Dict[str, ProposalRecord] = {}

    def compute_trip_state_hash(self, trip_id: str) -> str:
        """Computes a deterministic hash of current active trip state."""
        db = get_db()
        trip = db.get_trip(trip_id)
        if not trip:
            return "empty"

        stops = db.get_trip_stops(trip_id)
        items = []
        for s in stops:
            items.extend(db.get_itinerary_items_for_stop(s.id))
        legs = db.get_transport_legs_for_trip(trip_id)

        # Build stable digest string
        components = [
            f"trip:{trip.id}:{trip.total_budget}:{trip.start_date}:{trip.end_date}",
            ",".join(f"stop:{s.id}:{s.destination_id}:{s.arrival_date}:{s.departure_date}" for s in stops),
            ",".join(f"item:{it.id}:{it.place_id}:{it.start_time}:{it.end_time}:{it.cost}" for it in items),
            ",".join(f"leg:{l.id}:{l.mode.value}:{l.departure_time}:{l.cost}" for l in legs),
        ]
        raw = "|".join(components)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def store_replan(self, replan: ProposedReplan) -> ProposalRecord:
        base_hash = self.compute_trip_state_hash(replan.trip_id)
        record = ProposalRecord(
            proposal_id=replan.replan_id,
            trip_id=replan.trip_id,
            proposal_type="replan",
            base_version_hash=base_hash,
            payload=replan,
            status="PROPOSED",
        )
        self._proposals[replan.replan_id] = record
        return record

    def store_simulation(self, simulation: WhatIfSimulationResult) -> ProposalRecord:
        base_hash = self.compute_trip_state_hash(simulation.trip_id)
        record = ProposalRecord(
            proposal_id=simulation.simulation_id,
            trip_id=simulation.trip_id,
            proposal_type="simulation",
            base_version_hash=base_hash,
            payload=simulation,
            status="PROPOSED",
        )
        self._proposals[simulation.simulation_id] = record
        return record

    def get_proposal(self, proposal_id: str) -> Optional[ProposalRecord]:
        return self._proposals.get(proposal_id)

    def verify_and_get(self, proposal_id: str) -> ProposalRecord:
        record = self.get_proposal(proposal_id)
        if not record:
            raise KeyError(f"Proposal '{proposal_id}' not found.")

        current_hash = self.compute_trip_state_hash(record.trip_id)
        if current_hash != record.base_version_hash:
            raise StaleProposalError(
                f"Proposal '{proposal_id}' is stale. Active trip has changed (Base: {record.base_version_hash}, Current: {current_hash})."
            )
        return record

    def mark_applied(self, proposal_id: str):
        if proposal_id in self._proposals:
            self._proposals[proposal_id].status = "APPLIED"

    def mark_rejected(self, proposal_id: str):
        if proposal_id in self._proposals:
            self._proposals[proposal_id].status = "REJECTED"


proposal_store = ProposalStore()
