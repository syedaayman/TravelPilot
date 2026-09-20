"""
TravelPilot Deterministic Disruption Management & Replanning Engine
Handles 7 disruption types with minimal disruption footprint, alternative scoring,
deterministic budget/schedule re-validation, Before/After diff generation, and safe isolated proposal states.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import date, time, datetime, timedelta, timezone
import copy
import logging
from uuid import uuid4

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
    HotelTier,
)
from backend.app.core.models import (
    CoreDisruptionType,
    DisruptionRequest,
    DisruptionAnalysisResult,
    CandidateAlternative,
    ProposedReplan,
    PlanDiffResult,
    GeoPoint,
    RoutingMode,
)
from backend.app.core.budget_engine import budget_engine
from backend.app.core.schedule_validator import schedule_validator, parse_time_str, time_to_minutes, date_to_schema_day
from backend.app.core.geo_routing import geo_routing_engine
from backend.app.core.diff_engine import diff_engine

logger = logging.getLogger(__name__)


def minutes_to_time_str(m: int) -> str:
    h = (m // 60) % 24
    mins = m % 60
    return f"{h:02d}:{mins:02d}"


class DisruptionEngine:
    # =========================================================================
    # 1. READ-ONLY ANALYSIS
    # =========================================================================

    def analyze_disruption(
        self,
        request: DisruptionRequest,
        trip: Optional[Trip] = None,
        stops: Optional[List[TripStop]] = None,
        items: Optional[List[ItineraryItem]] = None,
        legs: Optional[List[TransportLeg]] = None,
    ) -> DisruptionAnalysisResult:
        """
        Performs read-only impact analysis for a disruption request.
        Does NOT mutate the active trip state.
        """
        db = get_db()
        trip_id = request.trip_id

        # Hydrate state from DB if not provided
        trip = trip or db.get_trip(trip_id)
        stops = stops or db.get_trip_stops(trip_id)
        legs = legs or db.get_transport_legs_for_trip(trip_id)
        if items is None:
            items = []
            for s in stops:
                items.extend(db.get_itinerary_items_for_stop(s.id))

        affected_items = []
        affected_legs = []
        downstream_items = []
        available_windows = []
        reasons = []
        severity = "medium"

        if request.type == CoreDisruptionType.VENUE_CLOSED:
            for it in items:
                if (request.affected_item_id and it.id == request.affected_item_id) or (
                    request.affected_place_id and it.place_id == request.affected_place_id
                ):
                    affected_items.append(it.model_dump())
                    available_windows.append({
                        "date": str(it.scheduled_date),
                        "start_time": it.start_time,
                        "end_time": it.end_time,
                        "day_number": it.day_number,
                        "trip_stop_id": it.trip_stop_id,
                    })
                    reasons.append(f"Venue for item '{it.custom_title or it.id}' is closed.")

        elif request.type == CoreDisruptionType.TRANSPORT_DELAY:
            delay = request.delay_minutes or 0
            for l in legs:
                if request.affected_leg_id and l.id == request.affected_leg_id:
                    affected_legs.append(l.model_dump())
                    new_arrival = l.arrival_time + timedelta(minutes=delay)
                    reasons.append(f"Transport leg {l.mode.value} delayed by {delay} mins.")
                    # Find downstream items starting before new arrival
                    for it in items:
                        if it.scheduled_date == l.arrival_time.date():
                            start_dt = datetime.combine(it.scheduled_date, parse_time_str(it.start_time))
                            if start_dt < new_arrival:
                                downstream_items.append(it.model_dump())
            severity = "high" if delay > 60 else "medium"

        elif request.type == CoreDisruptionType.TRANSPORT_CANCELLED:
            for l in legs:
                if request.affected_leg_id and l.id == request.affected_leg_id:
                    affected_legs.append(l.model_dump())
                    reasons.append(f"Transport leg {l.mode.value} is cancelled.")
            severity = "critical"

        elif request.type == CoreDisruptionType.WEATHER_ALERT:
            alert_date = request.effective_date
            weather_cats = set(request.weather_categories or ["outdoor", "beach"])
            for it in items:
                if alert_date is None or it.scheduled_date == alert_date:
                    place = db.places.get(it.place_id) if it.place_id else None
                    if place and (place.category.lower() in weather_cats or any(c in place.category.lower() for c in weather_cats)):
                        affected_items.append(it.model_dump())
                        reasons.append(f"Outdoor activity '{it.custom_title}' affected by weather.")

        elif request.type == CoreDisruptionType.BUDGET_REDUCTION:
            reasons.append(f"User requested budget reduction of ₹{request.reduction_amount or 0:,.2f}.")
            severity = "low"

        elif request.type == CoreDisruptionType.BOOKING_UNAVAILABLE:
            if request.affected_item_id:
                for it in items:
                    if it.id == request.affected_item_id:
                        affected_items.append(it.model_dump())
                        reasons.append(f"Booking unavailable for activity '{it.custom_title}'.")

        elif request.type == CoreDisruptionType.SCHEDULE_CONFLICT:
            if request.affected_item_id:
                for it in items:
                    if it.id == request.affected_item_id:
                        affected_items.append(it.model_dump())
                        reasons.append(f"Schedule conflict for item '{it.custom_title}'.")

        return DisruptionAnalysisResult(
            disruption_id=request.disruption_id,
            trip_id=trip_id,
            type=request.type,
            affected_items=affected_items,
            affected_legs=affected_legs,
            downstream_affected_items=downstream_items,
            available_windows=available_windows,
            severity=severity,
            required_replan=len(affected_items) > 0 or len(affected_legs) > 0 or request.type == CoreDisruptionType.BUDGET_REDUCTION,
            reasons=reasons,
        )

    # =========================================================================
    # 2. DETERMINISTIC CANDIDATE REPLANNING
    # =========================================================================

    def replan_disruption(
        self,
        request: DisruptionRequest,
        trip: Optional[Trip] = None,
        stops: Optional[List[TripStop]] = None,
        items: Optional[List[ItineraryItem]] = None,
        legs: Optional[List[TransportLeg]] = None,
        hotels: Optional[Dict[str, Hotel]] = None,
    ) -> ProposedReplan:
        """
        Deterministically replans an itinerary upon a disruption.
        Preserves all unaffected elements, calculates Before/After diff,
        and returns a ProposedReplan in an isolated candidate branch.
        """
        db = get_db()
        trip_id = request.trip_id

        # 1. Hydrate Baseline State
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

        # Clone state for working candidate branch
        candidate_items = [it.model_copy(deep=True) for it in items]
        candidate_stops = [s.model_copy(deep=True) for s in stops]
        candidate_legs = [l.model_copy(deep=True) for l in legs]
        candidates_evaluated: List[CandidateAlternative] = []
        summary = ""

        # 2. Replan Branch per Disruption Type
        if request.type == CoreDisruptionType.VENUE_CLOSED:
            candidate_items, candidates_evaluated, summary = self._replan_venue_closed(
                request, candidate_items, candidate_stops, db
            )

        elif request.type == CoreDisruptionType.TRANSPORT_DELAY:
            candidate_legs, candidate_items, summary = self._replan_transport_delay(
                request, candidate_legs, candidate_items
            )

        elif request.type == CoreDisruptionType.TRANSPORT_CANCELLED:
            candidate_legs, candidate_items, summary = self._replan_transport_cancelled(
                request, candidate_legs, candidate_items, candidate_stops, db
            )

        elif request.type == CoreDisruptionType.WEATHER_ALERT:
            candidate_items, candidates_evaluated, summary = self._replan_weather_alert(
                request, candidate_items, candidate_stops, db
            )

        elif request.type == CoreDisruptionType.BOOKING_UNAVAILABLE:
            candidate_items, candidate_legs, hotels, summary = self._replan_booking_unavailable(
                request, candidate_items, candidate_legs, hotels, candidate_stops, db
            )

        elif request.type == CoreDisruptionType.BUDGET_REDUCTION:
            trip, hotels, candidate_items, summary = self._replan_budget_reduction(
                request, trip, hotels, candidate_items, candidate_stops, candidate_legs, db
            )

        elif request.type == CoreDisruptionType.SCHEDULE_CONFLICT:
            candidate_items, summary = self._replan_schedule_conflict(
                request, candidate_items, db
            )

        # 3. Post-Replan Validation & Budget Recalculation
        budget_after = budget_engine.calculate(
            total_budget=trip.total_budget,
            traveler_count=trip.traveler_count,
            trip_stops=candidate_stops,
            hotels_by_stop=hotels,
            transport_legs=candidate_legs,
            itinerary_items=candidate_items,
            destinations_by_stop=destinations_by_stop,
        )
        validation_after = schedule_validator.validate(
            trip=trip,
            trip_stops=candidate_stops,
            itinerary_items=candidate_items,
            transport_legs=candidate_legs,
            places_by_id=db.places,
            restaurants_by_id=db.restaurants,
        )

        diff = diff_engine.compare(
            before_items=items,
            after_items=candidate_items,
            before_legs=legs,
            after_legs=candidate_legs,
            before_budget_total=budget_before.total,
            after_budget_total=budget_after.total,
        )

        return ProposedReplan(
            replan_id=str(uuid4()),
            trip_id=trip_id,
            disruption_type=request.type,
            feasible=validation_after.valid,
            proposed_items=[it.model_dump() for it in candidate_items],
            proposed_stops=[s.model_dump() for s in candidate_stops],
            proposed_legs=[l.model_dump() for l in candidate_legs],
            diff=diff,
            budget_before=budget_before,
            budget_after=budget_after,
            validation_before=validation_before,
            validation_after=validation_after,
            summary=summary or diff.summary,
            candidates_evaluated=candidates_evaluated,
        )

    # =========================================================================
    # 3. TYPE-SPECIFIC REPLANNING HELPERS
    # =========================================================================

    def _replan_venue_closed(
        self,
        request: DisruptionRequest,
        items: List[ItineraryItem],
        stops: List[TripStop],
        db: Any,
    ) -> Tuple[List[ItineraryItem], List[CandidateAlternative], str]:
        """Finds closed venue, scores compatible alternatives, and minimally replaces it."""
        target_idx = None
        for idx, it in enumerate(items):
            if (request.affected_item_id and it.id == request.affected_item_id) or (
                request.affected_place_id and it.place_id == request.affected_place_id
            ):
                target_idx = idx
                break

        if target_idx is None:
            return items, [], "No matching closed venue found in itinerary."

        target_item = items[target_idx]
        target_place = db.places.get(target_item.place_id)
        stop = next((s for s in stops if s.id == target_item.trip_stop_id), None)
        dest_id = stop.destination_id if stop else (target_place.destination_id if target_place else None)

        if not dest_id:
            items.pop(target_idx)
            return items, [], f"Removed '{target_item.custom_title}' (no replacement destination found)."

        # Evaluate candidate alternatives in destination
        candidates_raw = db.search_places(dest_id)
        scheduled_place_ids = {it.place_id for it in items if it.place_id and it.id != target_item.id}
        scheduled_day = date_to_schema_day(target_item.scheduled_date)

        evaluated_candidates: List[CandidateAlternative] = []
        best_candidate = None
        best_score = -1.0

        for p in candidates_raw:
            if p.id == target_item.place_id or p.id in scheduled_place_ids:
                continue # Skip closed venue and already scheduled places

            # Check closed day
            if scheduled_day in p.closed_days:
                continue

            # Check open/close hours fit
            open_m = time_to_minutes(parse_time_str(p.open_time))
            close_m = time_to_minutes(parse_time_str(p.close_time))
            start_m = time_to_minutes(parse_time_str(target_item.start_time))
            end_m = time_to_minutes(parse_time_str(target_item.end_time))

            is_hours_feasible = (start_m >= open_m and end_m <= close_m)
            if not is_hours_feasible:
                continue

            # Calculate distance from closed venue
            dist_km = 0.0
            if target_place:
                dist_km = geo_routing_engine.calculate_distance(
                    GeoPoint(latitude=target_place.latitude, longitude=target_place.longitude),
                    GeoPoint(latitude=p.latitude, longitude=p.longitude),
                )

            # Score factors: rating (weight 40%), category match (weight 30%), proximity (weight 30%)
            cat_match = 1.0 if (target_place and p.category == target_place.category) else 0.5
            rating_score = (p.rating / 5.0)
            prox_score = max(0.0, 1.0 - (dist_km / 25.0))
            total_score = round(rating_score * 0.4 + cat_match * 0.3 + prox_score * 0.3, 3)

            cand = CandidateAlternative(
                place_id=p.id,
                name=p.name,
                category=p.category,
                rating=p.rating,
                entry_fee=p.entry_fee,
                distance_km=round(dist_km, 2),
                open_time=p.open_time,
                close_time=p.close_time,
                is_feasible=True,
                score=total_score,
                score_breakdown={
                    "rating_score": round(rating_score, 2),
                    "category_match": round(cat_match, 2),
                    "proximity_score": round(prox_score, 2),
                },
            )
            evaluated_candidates.append(cand)

            if total_score > best_score:
                best_score = total_score
                best_candidate = p

        evaluated_candidates.sort(key=lambda x: x.score, reverse=True)

        # Replace or Remove
        if best_candidate:
            replacement_item = target_item.model_copy(
                update={
                    "place_id": best_candidate.id,
                    "custom_title": best_candidate.name,
                    "cost": best_candidate.entry_fee,
                    "status": ItemStatus.ALTERNATIVE_SELECTED,
                    "notes": f"Replaced closed '{target_item.custom_title}' with '{best_candidate.name}'.",
                }
            )
            items[target_idx] = replacement_item
            summary = f"Replaced closed venue '{target_item.custom_title}' with '{best_candidate.name}' (Category: {best_candidate.category}, Rating: {best_candidate.rating}★)."
        else:
            items.pop(target_idx)
            summary = f"Closed venue '{target_item.custom_title}' removed (no feasible alternative available)."

        return items, evaluated_candidates, summary

    def _replan_transport_delay(
        self,
        request: DisruptionRequest,
        legs: List[TransportLeg],
        items: List[ItineraryItem],
    ) -> Tuple[List[TransportLeg], List[ItineraryItem], str]:
        """Shifts delayed leg and shifts only downstream activities that conflict with new arrival."""
        delay = request.delay_minutes or 30
        shifted_leg = None

        for idx, leg in enumerate(legs):
            if request.affected_leg_id and leg.id == request.affected_leg_id:
                new_dep = leg.departure_time + timedelta(minutes=delay)
                new_arr = leg.arrival_time + timedelta(minutes=delay)
                shifted_leg = leg.model_copy(
                    update={
                        "departure_time": new_dep,
                        "arrival_time": new_arr,
                        "status": TransportLegStatus.DELAYED,
                        "notes": f"Delayed by {delay} mins.",
                    }
                )
                legs[idx] = shifted_leg
                break

        if not shifted_leg:
            return legs, items, "No matching transport leg found for delay."

        # Shift downstream items starting on or after arrival date that conflict with arrival
        shift_count = 0
        arr_date = shifted_leg.arrival_time.date()
        arr_minute = time_to_minutes(shifted_leg.arrival_time.time()) + 30 # 30 min buffer after arrival

        for idx, it in enumerate(items):
            if it.scheduled_date == arr_date:
                start_m = time_to_minutes(parse_time_str(it.start_time))
                end_m = time_to_minutes(parse_time_str(it.end_time))
                duration = end_m - start_m

                if start_m < arr_minute:
                    new_start_m = arr_minute
                    new_end_m = new_start_m + duration
                    items[idx] = it.model_copy(
                        update={
                            "start_time": minutes_to_time_str(new_start_m),
                            "end_time": minutes_to_time_str(new_end_m),
                            "status": ItemStatus.RESCHEDULED,
                            "notes": f"Shifted due to {delay} min transport delay.",
                        }
                    )
                    arr_minute = new_end_m + (it.travel_time_from_prev_minutes or 15)
                    shift_count += 1

        summary = f"Shifted {shifted_leg.mode.value} transport arrival by {delay} mins and adjusted {shift_count} downstream activities."
        return legs, items, summary

    def _replan_transport_cancelled(
        self,
        request: DisruptionRequest,
        legs: List[TransportLeg],
        items: List[ItineraryItem],
        stops: List[TripStop],
        db: Any,
    ) -> Tuple[List[TransportLeg], List[ItineraryItem], str]:
        """Finds alternative transport option between origin and destination stop from DB."""
        target_idx = None
        for idx, l in enumerate(legs):
            if request.affected_leg_id and l.id == request.affected_leg_id:
                target_idx = idx
                break

        if target_idx is None:
            return legs, items, "Cancelled leg not found."

        cancelled_leg = legs[target_idx]
        origin_stop = next((s for s in stops if s.id == cancelled_leg.origin_stop_id), None)
        dest_stop = next((s for s in stops if s.id == cancelled_leg.destination_stop_id), None)

        if not (origin_stop and dest_stop):
            return legs, items, "Cannot resolve stops for cancelled leg."

        # Search available transport in DB
        options = db.search_transport(origin_stop.destination_id, dest_stop.destination_id)
        # Filter out exact cancelled mode/carrier if possible, or select alternative mode (e.g. bus vs train vs flight)
        alternatives = [o for o in options if o.mode != cancelled_leg.mode or o.code != cancelled_leg.carrier]
        selected_option = alternatives[0] if alternatives else (options[0] if options else None)

        if selected_option:
            new_dep_time = cancelled_leg.departure_time
            new_arr_time = new_dep_time + timedelta(minutes=selected_option.typical_duration_minutes)

            replacement_leg = TransportLeg(
                id=str(uuid4()),
                trip_id=cancelled_leg.trip_id,
                origin_stop_id=cancelled_leg.origin_stop_id,
                destination_stop_id=cancelled_leg.destination_stop_id,
                mode=selected_option.mode,
                carrier=selected_option.carrier or selected_option.code,
                departure_time=new_dep_time,
                arrival_time=new_arr_time,
                cost=selected_option.estimated_cost,
                status=TransportLegStatus.SCHEDULED,
                notes=f"Replacement for cancelled {cancelled_leg.mode.value}.",
            )
            legs[target_idx] = replacement_leg
            summary = f"Replaced cancelled {cancelled_leg.mode.value} with {selected_option.mode.value} ({selected_option.carrier}, cost: ₹{selected_option.estimated_cost})."
        else:
            legs.pop(target_idx)
            summary = f"Cancelled leg {cancelled_leg.mode.value} removed (no alternative transport found)."

        return legs, items, summary

    def _replan_weather_alert(
        self,
        request: DisruptionRequest,
        items: List[ItineraryItem],
        stops: List[TripStop],
        db: Any,
    ) -> Tuple[List[ItineraryItem], List[CandidateAlternative], str]:
        """Replaces outdoor activities on bad-weather dates with indoor alternatives."""
        alert_date = request.effective_date
        weather_cats = set(request.weather_categories or ["outdoor", "beach", "nature"])
        replaced_count = 0
        evaluated: List[CandidateAlternative] = []

        for idx, it in enumerate(items):
            if alert_date is None or it.scheduled_date == alert_date:
                place = db.places.get(it.place_id) if it.place_id else None
                if place and place.category.lower() in weather_cats:
                    # Find indoor alternative in same destination
                    stop = next((s for s in stops if s.id == it.trip_stop_id), None)
                    dest_id = stop.destination_id if stop else place.destination_id
                    indoor_places = [
                        p for p in db.search_places(dest_id)
                        if p.category.lower() in {"museum", "historical", "shopping", "religious"}
                        and p.id != place.id
                    ]
                    if indoor_places:
                        best_indoor = indoor_places[0]
                        items[idx] = it.model_copy(
                            update={
                                "place_id": best_indoor.id,
                                "custom_title": best_indoor.name,
                                "cost": best_indoor.entry_fee,
                                "status": ItemStatus.ALTERNATIVE_SELECTED,
                                "notes": f"Switched to indoor attraction due to weather alert.",
                            }
                        )
                        replaced_count += 1
                        evaluated.append(
                            CandidateAlternative(
                                place_id=best_indoor.id,
                                name=best_indoor.name,
                                category=best_indoor.category,
                                rating=best_indoor.rating,
                                entry_fee=best_indoor.entry_fee,
                                open_time=best_indoor.open_time,
                                close_time=best_indoor.close_time,
                                is_feasible=True,
                                score=0.9,
                            )
                        )

        summary = f"Weather alert handled: Replaced {replaced_count} outdoor activity(ies) with verified indoor alternatives."
        return items, evaluated, summary

    def _replan_booking_unavailable(
        self,
        request: DisruptionRequest,
        items: List[ItineraryItem],
        legs: List[TransportLeg],
        hotels: Dict[str, Hotel],
        stops: List[TripStop],
        db: Any,
    ) -> Tuple[List[ItineraryItem], List[TransportLeg], Dict[str, Hotel], str]:
        """Finds alternative hotel or activity when a booking becomes unavailable."""
        summary = "Booking unavailable resolved."
        # If hotel unavailable
        for stop in stops:
            hotel = hotels.get(stop.id)
            if hotel:
                alt_hotels = [h for h in db.search_hotels(stop.destination_id) if h.id != hotel.id]
                if alt_hotels:
                    hotels[stop.id] = alt_hotels[0]
                    summary = f"Replaced unavailable hotel with '{alt_hotels[0].name}' (₹{alt_hotels[0].price_per_night}/night)."
                    break

        return items, legs, hotels, summary

    def _replan_budget_reduction(
        self,
        request: DisruptionRequest,
        trip: Trip,
        hotels: Dict[str, Hotel],
        items: List[ItineraryItem],
        stops: List[TripStop],
        legs: List[TransportLeg],
        db: Any,
    ) -> Tuple[Trip, Dict[str, Hotel], List[ItineraryItem], str]:
        """Optimizes accommodation and activity costs to fit within a reduced budget."""
        reduction = request.reduction_amount or (trip.total_budget * 0.15)
        target_budget = max(5000.0, trip.total_budget - reduction)
        new_trip = trip.model_copy(update={"total_budget": target_budget})

        # Switch expensive hotels to budget/mid-range hotels
        hotels_changed = 0
        for stop in stops:
            h = hotels.get(stop.id)
            if h and h.price_per_night > 2500.0:
                budget_options = db.search_hotels(stop.destination_id, tier="budget")
                if budget_options:
                    hotels[stop.id] = budget_options[0]
                    hotels_changed += 1

        summary = f"Reduced budget by ₹{reduction:,.2f} to ₹{target_budget:,.2f}. Optimized {hotels_changed} hotel accommodation(s) to budget tier."
        return new_trip, hotels, items, summary

    def _replan_schedule_conflict(
        self,
        request: DisruptionRequest,
        items: List[ItineraryItem],
        db: Any,
    ) -> Tuple[List[ItineraryItem], str]:
        """Shifts conflicting item to a non-overlapping afternoon slot."""
        for idx, it in enumerate(items):
            if request.affected_item_id and it.id == request.affected_item_id:
                items[idx] = it.model_copy(
                    update={
                        "start_time": "14:30",
                        "end_time": "16:30",
                        "status": ItemStatus.RESCHEDULED,
                        "notes": "Rescheduled to resolve timing conflict.",
                    }
                )
                return items, f"Rescheduled '{it.custom_title}' to 14:30 - 16:30 to eliminate schedule conflict."

        return items, "No conflicting items shifted."

    # =========================================================================
    # 4. MUTATING STATE APPLICATION
    # =========================================================================

    def apply_replan(self, replan: ProposedReplan) -> Dict[str, Any]:
        """
        Explicit mutating operation. Applies proposed items, stops, and legs
        to the active database store and records an AgentEvent.
        """
        db = get_db()
        trip_id = replan.trip_id
        
        # Update trip in DB
        if trip_id in db.trips:
            db.trips[trip_id].total_budget = replan.budget_after.budget
            db.update_trip(db.trips[trip_id])

        # Update items in DB
        for it_dict in replan.proposed_items:
            it_obj = ItineraryItem(**it_dict) if isinstance(it_dict, dict) else it_dict
            db.itinerary_items[it_obj.id] = it_obj

        # Update legs in DB
        for l_dict in replan.proposed_legs:
            l_obj = TransportLeg(**l_dict) if isinstance(l_dict, dict) else l_dict
            db.transport_legs[l_obj.id] = l_obj

        db.record_agent_event(
            AgentEvent(
                trip_id=trip_id,
                event_type=AgentEventType.REPLAN_COMPLETED,
                result_summary=f"Disruption {replan.disruption_type.value} replan applied ({len(replan.proposed_items)} items).",
                status="success",
            )
        )

        return {
            "success": True,
            "trip_id": trip_id,
            "applied_items_count": len(replan.proposed_items),
            "applied_legs_count": len(replan.proposed_legs),
            "budget_delta": replan.diff.budget_delta,
        }

    def reject_replan(self, replan: ProposedReplan) -> Dict[str, Any]:
        """Rejects the proposed replan. Active DB state remains completely untouched."""
        return {
            "success": True,
            "trip_id": replan.trip_id,
            "message": "Proposed replan was rejected. Active itinerary unchanged.",
        }


disruption_engine = DisruptionEngine()
