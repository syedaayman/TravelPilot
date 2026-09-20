"""
TravelPilot Deterministic What-If Simulation Engine
Evaluates hypothetical itinerary branches (budget change, add day, remove destination,
replace destination, add activity) in isolated memory branches without mutating active state.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import date, time, datetime, timedelta, timezone
import copy
import logging

from backend.app.db.supabase_client import get_db
from backend.app.models.entities import (
    Trip,
    TripStop,
    TransportLeg,
    ItineraryItem,
    Hotel,
    Place,
    Restaurant,
    AgentEvent,
    AgentEventType,
    ItemType,
    ItemStatus,
    TransportMode,
    TransportLegStatus,
)
from backend.app.core.models import (
    WhatIfType,
    WhatIfRequest,
    WhatIfSimulationResult,
    PlanDiffResult,
    GeoPoint,
    RoutingMode,
)
from backend.app.core.budget_engine import budget_engine
from backend.app.core.schedule_validator import schedule_validator, parse_time_str, time_to_minutes
from backend.app.core.geo_routing import geo_routing_engine
from backend.app.core.diff_engine import diff_engine

logger = logging.getLogger(__name__)


class SimulationEngine:
    def simulate_what_if(
        self,
        request: WhatIfRequest,
        trip: Optional[Trip] = None,
        stops: Optional[List[TripStop]] = None,
        items: Optional[List[ItineraryItem]] = None,
        legs: Optional[List[TransportLeg]] = None,
        hotels: Optional[Dict[str, Hotel]] = None,
    ) -> WhatIfSimulationResult:
        """
        Executes an isolated what-if simulation on a cloned candidate branch.
        Strictly DOES NOT mutate the active database state.
        """
        db = get_db()
        trip_id = request.trip_id

        # 1. Hydrate Active Baseline State
        trip = trip or db.get_trip(trip_id) or Trip(
            id=trip_id, title="Trip", start_date=date.today(), end_date=date.today() + timedelta(days=3), total_budget=30000.0
        )
        stops = stops or db.get_trip_stops(trip_id)
        legs = legs or db.get_transport_legs_for_trip(trip_id)
        if items is None:
            items = []
            for s in stops:
                items.extend(db.get_itinerary_items_for_stop(s.id))

        hotels = hotels or {}
        destinations_by_stop = {
            s.id: db.destinations.get(s.destination_id) for s in stops if s.destination_id in db.destinations
        }

        # Baseline Calculations
        budget_before = budget_engine.calculate(
            total_budget=trip.total_budget,
            traveler_count=trip.traveler_count,
            trip_stops=stops,
            hotels_by_stop=hotels,
            transport_legs=legs,
            itinerary_items=items,
            destinations_by_stop=destinations_by_stop,
        )
        validation_before = schedule_validator.validate(
            trip=trip,
            trip_stops=stops,
            itinerary_items=items,
            transport_legs=legs,
            places_by_id=db.places,
            restaurants_by_id=db.restaurants,
        )

        # 2. Clone State for Isolated Simulation Branch
        cand_trip = trip.model_copy(deep=True)
        cand_stops = [s.model_copy(deep=True) for s in stops]
        cand_items = [it.model_copy(deep=True) for it in items]
        cand_legs = [l.model_copy(deep=True) for l in legs]
        cand_hotels = copy.deepcopy(hotels)

        warnings: List[str] = []
        errors: List[str] = []

        # 3. Apply Hypothetical Modification on Branch
        if request.type == WhatIfType.BUDGET_CHANGE:
            new_budget = request.new_budget or (
                cand_trip.total_budget + (request.budget_delta or 0.0)
            )
            cand_trip = cand_trip.model_copy(update={"total_budget": max(1000.0, new_budget)})

        elif request.type == WhatIfType.ADD_DAY:
            extra = request.extra_days or 1
            cand_trip = cand_trip.model_copy(update={"end_date": cand_trip.end_date + timedelta(days=extra)})
            if cand_stops:
                last_stop = cand_stops[-1]
                cand_stops[-1] = last_stop.model_copy(
                    update={"departure_date": last_stop.departure_date + timedelta(days=extra)}
                )

        elif request.type == WhatIfType.REMOVE_DESTINATION:
            target_dest_id = request.target_destination_id
            # Remove target stop
            removed_stop_id = None
            remaining_stops = []
            for s in cand_stops:
                if target_dest_id and s.destination_id == target_dest_id:
                    removed_stop_id = s.id
                else:
                    remaining_stops.append(s)
            cand_stops = remaining_stops

            # Remove items belonging to that stop
            if removed_stop_id:
                cand_items = [it for it in cand_items if it.trip_stop_id != removed_stop_id]
                cand_legs = [
                    l for l in cand_legs if l.origin_stop_id != removed_stop_id and l.destination_stop_id != removed_stop_id
                ]

        elif request.type == WhatIfType.REPLACE_DESTINATION:
            target_id = request.target_destination_id
            rep_id = request.replacement_destination_id
            rep_dest = db.destinations.get(rep_id)

            if rep_dest:
                for idx, s in enumerate(cand_stops):
                    if s.destination_id == target_id:
                        cand_stops[idx] = s.model_copy(update={"destination_id": rep_id})
                        # Replace items for that stop with representative items from replacement destination
                        cand_items = [it for it in cand_items if it.trip_stop_id != s.id]
                        new_places = db.search_places(rep_id)[:2]
                        for p_idx, np in enumerate(new_places):
                            cand_items.append(
                                ItineraryItem(
                                    id=str(uuid4()),
                                    trip_stop_id=s.id,
                                    place_id=np.id,
                                    custom_title=np.name,
                                    day_number=s.order_index + 1,
                                    scheduled_date=s.arrival_date,
                                    start_time="10:00" if p_idx == 0 else "14:00",
                                    end_time="12:30" if p_idx == 0 else "16:30",
                                    cost=np.entry_fee,
                                )
                            )

        elif request.type == WhatIfType.ADD_ACTIVITY:
            act_data = request.activity_data or {}
            new_item = ItineraryItem(
                id=str(uuid4()),
                trip_stop_id=cand_stops[0].id if cand_stops else "stop-1",
                custom_title=act_data.get("title", "New Custom Activity"),
                day_number=act_data.get("day_number", 1),
                scheduled_date=date.fromisoformat(act_data.get("scheduled_date", str(cand_trip.start_date))),
                start_time=act_data.get("start_time", "16:00"),
                end_time=act_data.get("end_time", "18:00"),
                cost=float(act_data.get("cost", 0.0)),
            )
            cand_items.append(new_item)

        # 4. Post-Simulation Validation & Budget Recalculation
        cand_destinations_by_stop = {
            s.id: db.destinations.get(s.destination_id) for s in cand_stops if s.destination_id in db.destinations
        }
        budget_after = budget_engine.calculate(
            total_budget=cand_trip.total_budget,
            traveler_count=cand_trip.traveler_count,
            trip_stops=cand_stops,
            hotels_by_stop=cand_hotels,
            transport_legs=cand_legs,
            itinerary_items=cand_items,
            destinations_by_stop=cand_destinations_by_stop,
        )
        validation_after = schedule_validator.validate(
            trip=cand_trip,
            trip_stops=cand_stops,
            itinerary_items=cand_items,
            transport_legs=cand_legs,
            places_by_id=db.places,
            restaurants_by_id=db.restaurants,
        )

        diff = diff_engine.compare(
            before_items=items,
            after_items=cand_items,
            before_legs=legs,
            after_legs=cand_legs,
            before_budget_total=budget_before.total,
            after_budget_total=budget_after.total,
        )

        if not validation_after.valid:
            for err in validation_after.errors:
                errors.append(err.message)

        return WhatIfSimulationResult(
            simulation_id=request.simulation_id,
            trip_id=trip_id,
            type=request.type,
            success=True,
            feasible=validation_after.valid,
            current_summary={
                "title": trip.title,
                "days": len(budget_before.daily_breakdowns),
                "total_budget": trip.total_budget,
                "estimated_cost": budget_before.total,
            },
            proposed_summary={
                "title": cand_trip.title,
                "days": len(budget_after.daily_breakdowns),
                "total_budget": cand_trip.total_budget,
                "estimated_cost": budget_after.total,
            },
            proposed_items=[it.model_dump() for it in cand_items],
            proposed_stops=[s.model_dump() for s in cand_stops],
            proposed_legs=[l.model_dump() for l in cand_legs],
            diff=diff,
            budget_before=budget_before,
            budget_after=budget_after,
            validation_before=validation_before,
            validation_after=validation_after,
            warnings=[w.message for w in validation_after.warnings],
            errors=errors,
        )

    def apply_simulation(self, result: WhatIfSimulationResult) -> Dict[str, Any]:
        """
        Explicit mutating operation. Overwrites the active database store
        with the approved simulation state and logs a state_update AgentEvent.
        """
        db = get_db()
        trip_id = result.trip_id
        
        # Update trip
        if trip_id in db.trips:
            from datetime import timedelta
            db.trips[trip_id].total_budget = result.proposed_summary["total_budget"]
            db.trips[trip_id].end_date = (
                db.trips[trip_id].start_date
                + timedelta(days=result.proposed_summary["days"] - 1)
            )
            db.trips[trip_id].title = result.proposed_summary["title"]
            db.update_trip(db.trips[trip_id])

        # Update stops
        for s_dict in result.proposed_stops:
            s_obj = TripStop(**s_dict) if isinstance(s_dict, dict) else s_dict
            db.trip_stops[s_obj.id] = s_obj

        # Update items
        for it_dict in result.proposed_items:
            it_obj = ItineraryItem(**it_dict) if isinstance(it_dict, dict) else it_dict
            db.itinerary_items[it_obj.id] = it_obj

        # Update legs
        for l_dict in result.proposed_legs:
            l_obj = TransportLeg(**l_dict) if isinstance(l_dict, dict) else l_dict
            db.transport_legs[l_obj.id] = l_obj

        db.record_agent_event(
            AgentEvent(
                trip_id=trip_id,
                event_type=AgentEventType.SIMULATION_COMPLETED,
                result_summary=f"Simulation {result.type.value} applied successfully.",
                status="success",
            )
        )

        return {
            "success": True,
            "trip_id": trip_id,
            "applied": True,
            "items_count": len(result.proposed_items),
        }

    def reject_simulation(self, result: WhatIfSimulationResult) -> Dict[str, Any]:
        """Rejects simulation branch. Leaves active state completely unchanged."""
        return {
            "success": True,
            "trip_id": result.trip_id,
            "applied": False,
            "message": "Simulation branch discarded.",
        }


simulation_engine = SimulationEngine()
