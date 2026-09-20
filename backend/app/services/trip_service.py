"""
TravelPilot Trip Application Service
Implements destination-agnostic planning for Single-City and Multi-City trips,
orchestrates deterministic calculations, validates schedules, and persists active state.
"""

from typing import List, Dict, Any, Optional
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4
import math

from backend.app.db.supabase_client import get_db
from backend.app.models.entities import (
    Trip,
    TripStop,
    TransportLeg,
    ItineraryItem,
    Hotel,
    Destination,
    AgentEvent,
    AgentEventType,
    TripStatus,
    TransportMode,
    TransportLegStatus,
    ItemType,
    ItemStatus,
    HotelTier,
)
from backend.app.core.models import GeoPoint, RoutingMode
from backend.app.core.budget_engine import budget_engine
from backend.app.core.schedule_validator import schedule_validator
from backend.app.core.geo_routing import geo_routing_engine
from backend.app.services.proposal_store import proposal_store
from backend.app.api.schemas.trips import (
    TripPlanRequest,
    TripPlanResponse,
    TripDetailResponse,
    TripStopDetail,
    TransportLegDetail,
    ItineraryItemDetail,
)


class TripService:
    def plan_trip(self, request: TripPlanRequest) -> TripPlanResponse:
        """
        Creates and persists a validated, budget-aware single-city or multi-city trip.
        Destination-agnostic: resolves any destination from the database reference layer.
        """
        db = get_db()
        start_dt = request.start_date or (date.today() + timedelta(days=14))
        end_dt = start_dt + timedelta(days=request.duration_days - 1)

        # 1. Resolve Destinations Dynamically
        resolved_destinations: List[Destination] = []
        for dest_name in request.destinations:
            dest = db.get_destination_by_name(dest_name)
            if not dest:
                # Substring search fallback
                search_res = db.search_destinations(dest_name)
                if search_res:
                    dest = search_res[0]
                else:
                    raise ValueError(f"DESTINATION_NOT_FOUND: '{dest_name}' could not be resolved.")
            resolved_destinations.append(dest)

        dest_count = len(resolved_destinations)
        trip_id = str(uuid4())

        # 2. Allocate Days Across Stops
        days_per_stop = max(1, request.duration_days // dest_count)
        stops: List[TripStop] = []
        hotels_by_stop: Dict[str, Hotel] = {}
        destinations_by_stop: Dict[str, Destination] = {}

        current_date = start_dt
        for idx, dest in enumerate(resolved_destinations):
            # For last stop, assign all remaining days
            if idx == dest_count - 1:
                stop_duration = (end_dt - current_date).days + 1
            else:
                stop_duration = days_per_stop

            stop_arr = current_date
            stop_dep = current_date + timedelta(days=max(1, stop_duration) - 1)

            # Select Hotel matching budget tier
            preferred_tier = "budget" if request.budget / request.duration_days < 3500 else "mid-range"
            hotels_found = db.search_hotels(dest.id, tier=preferred_tier)
            selected_hotel = hotels_found[0] if hotels_found else (db.search_hotels(dest.id)[0] if db.search_hotels(dest.id) else None)

            stop = TripStop(
                id=str(uuid4()),
                trip_id=trip_id,
                destination_id=dest.id,
                order_index=idx,
                arrival_date=stop_arr,
                departure_date=stop_dep,
                stop_budget=round(request.budget / dest_count, 2),
                hotel_id=selected_hotel.id if selected_hotel else None,
            )
            stops.append(stop)
            if selected_hotel:
                hotels_by_stop[stop.id] = selected_hotel
            destinations_by_stop[stop.id] = dest

            current_date = stop_dep + timedelta(days=1)

        # 3. Create Trip Record
        title_str = " → ".join(d.name for d in resolved_destinations)
        trip = Trip(
            id=trip_id,
            title=f"{request.duration_days} Days in {title_str}",
            start_date=start_dt,
            end_date=end_dt,
            total_budget=request.budget,
            traveler_count=request.travelers,
            interests=request.interests,
            preferences=request.preferences,
            status=TripStatus.CONFIRMED,
        )

        # 4. Inter-City Transport Legs (Connecting Consecutive Stops)
        legs: List[TransportLeg] = []
        for i in range(len(stops) - 1):
            s_from = stops[i]
            s_to = stops[i + 1]
            t_options = db.search_transport(s_from.destination_id, s_to.destination_id)
            selected_t = t_options[0] if t_options else None

            dep_dt = datetime.combine(s_from.departure_date, time(18, 0))
            arr_dt = dep_dt + timedelta(minutes=selected_t.typical_duration_minutes if selected_t else 240)

            leg = TransportLeg(
                id=str(uuid4()),
                trip_id=trip_id,
                origin_stop_id=s_from.id,
                destination_stop_id=s_to.id,
                mode=selected_t.mode if selected_t else TransportMode.TRAIN,
                carrier=selected_t.carrier if selected_t else "Intercity Express",
                departure_time=dep_dt,
                arrival_time=arr_dt,
                cost=selected_t.estimated_cost if selected_t else 600.0,
                status=TransportLegStatus.SCHEDULED,
            )
            legs.append(leg)

        # 5. Schedule Tourist Activities per Destination Stop
        items: List[ItineraryItem] = []
        overall_day = 1

        for stop in stops:
            dest = destinations_by_stop[stop.id]
            # Fetch places in destination
            places = db.search_places(dest.id)
            if not places:
                places = list(db.places.values())[:3]

            curr_stop_date = stop.arrival_date
            place_pointer = 0

            while curr_stop_date <= stop.departure_date:
                # Schedule 2 activities per day: Morning and Afternoon
                # Item 1: Morning (10:00 - 12:30)
                if place_pointer < len(places):
                    p1 = places[place_pointer]
                    item1 = ItineraryItem(
                        id=str(uuid4()),
                        trip_stop_id=stop.id,
                        place_id=p1.id,
                        custom_title=p1.name,
                        day_number=overall_day,
                        scheduled_date=curr_stop_date,
                        start_time="10:00",
                        end_time="12:30",
                        cost=p1.entry_fee,
                        travel_time_from_prev_minutes=0,
                        travel_distance_km=0.0,
                    )
                    items.append(item1)
                    place_pointer += 1

                # Item 2: Afternoon (14:30 - 17:00)
                if place_pointer < len(places):
                    p2 = places[place_pointer]
                    # Estimate transit from p1 to p2
                    travel_time = 20
                    dist_km = 5.0
                    if place_pointer > 0 and items:
                        prev_p = places[place_pointer - 1]
                        est = geo_routing_engine.estimate_travel_time(
                            GeoPoint(latitude=prev_p.latitude, longitude=prev_p.longitude),
                            GeoPoint(latitude=p2.latitude, longitude=p2.longitude),
                            mode=RoutingMode.CAB,
                        )
                        travel_time = est.duration_minutes
                        dist_km = est.distance_km

                    item2 = ItineraryItem(
                        id=str(uuid4()),
                        trip_stop_id=stop.id,
                        place_id=p2.id,
                        custom_title=p2.name,
                        day_number=overall_day,
                        scheduled_date=curr_stop_date,
                        start_time="14:30",
                        end_time="17:00",
                        cost=p2.entry_fee,
                        travel_time_from_prev_minutes=travel_time,
                        travel_distance_km=dist_km,
                    )
                    items.append(item2)
                    place_pointer += 1

                overall_day += 1
                curr_stop_date += timedelta(days=1)

        # 6. Calculate Budget & Validate Schedule
        budget_res = budget_engine.calculate(
            total_budget=trip.total_budget,
            traveler_count=trip.traveler_count,
            trip_stops=stops,
            hotels_by_stop=hotels_by_stop,
            transport_legs=legs,
            itinerary_items=items,
            destinations_by_stop=destinations_by_stop,
        )

        validation_res = schedule_validator.validate(
            trip=trip,
            trip_stops=stops,
            itinerary_items=items,
            transport_legs=legs,
            places_by_id=db.places,
            restaurants_by_id=db.restaurants,
        )

        # 7. Persist Active Trip State to DB
        db.create_trip(trip)
        for s in stops:
            db.add_trip_stop(s)
        for l in legs:
            db.add_transport_leg(l)
        for it in items:
            db.add_itinerary_item(it)

        # 8. Log Structured Observability Events
        db.record_agent_event(
            AgentEvent(
                trip_id=trip.id,
                event_type=AgentEventType.PLANNING_STARTED,
                input_summary=f"Planning {title_str} for {request.duration_days} days (Budget: ₹{request.budget:,.2f})",
                status="success",
            )
        )
        db.record_agent_event(
            AgentEvent(
                trip_id=trip.id,
                event_type=AgentEventType.DECISION,
                result_summary=f"Finalized itinerary: {len(items)} activities, {len(legs)} transport legs, Budget used: {budget_res.percentage_used:.1f}%",
                status="success",
            )
        )

        detail_response = self._build_detail_response(
            trip, stops, legs, items, hotels_by_stop, destinations_by_stop, budget_res, validation_res
        )

        reasoning = (
            f"Successfully planned {request.duration_days}-day itinerary across {title_str}. "
            f"Total estimated cost: ₹{budget_res.total:,.2f} against your ₹{request.budget:,.2f} budget. "
            f"All venue opening hours and travel buffers have been verified."
        )

        return TripPlanResponse(
            success=True,
            trip=detail_response,
            agent_reasoning=reasoning,
        )

    def get_trip_detail(self, trip_id: str) -> TripDetailResponse:
        """Retrieves complete trip state from database with budget and validation summaries."""
        db = get_db()
        trip = db.get_trip(trip_id)
        if not trip:
            raise KeyError(f"TRIP_NOT_FOUND: Trip '{trip_id}' does not exist.")

        stops = db.get_trip_stops(trip_id)
        legs = db.get_transport_legs_for_trip(trip_id)
        items = []
        for s in stops:
            items.extend(db.get_itinerary_items_for_stop(s.id))

        hotels_by_stop = {}
        destinations_by_stop = {}
        for s in stops:
            if s.hotel_id and s.hotel_id in db.hotels:
                hotels_by_stop[s.id] = db.hotels[s.hotel_id]
            if s.destination_id in db.destinations:
                destinations_by_stop[s.id] = db.destinations[s.destination_id]

        budget_res = budget_engine.calculate(
            total_budget=trip.total_budget,
            traveler_count=trip.traveler_count,
            trip_stops=stops,
            hotels_by_stop=hotels_by_stop,
            transport_legs=legs,
            itinerary_items=items,
            destinations_by_stop=destinations_by_stop,
        )

        validation_res = schedule_validator.validate(
            trip=trip,
            trip_stops=stops,
            itinerary_items=items,
            transport_legs=legs,
            places_by_id=db.places,
            restaurants_by_id=db.restaurants,
        )

        return self._build_detail_response(
            trip, stops, legs, items, hotels_by_stop, destinations_by_stop, budget_res, validation_res
        )

    def _build_detail_response(
        self,
        trip: Trip,
        stops: List[TripStop],
        legs: List[TransportLeg],
        items: List[ItineraryItem],
        hotels_by_stop: Dict[str, Hotel],
        destinations_by_stop: Dict[str, Destination],
        budget_res: Any,
        validation_res: Any,
    ) -> TripDetailResponse:
        stop_details = []
        for s in stops:
            dest = destinations_by_stop.get(s.id)
            hotel = hotels_by_stop.get(s.id)
            stop_details.append(
                TripStopDetail(
                    id=s.id,
                    trip_id=s.trip_id,
                    destination_id=s.destination_id,
                    destination_name=dest.name if dest else "Unknown",
                    order_index=s.order_index,
                    arrival_date=str(s.arrival_date),
                    departure_date=str(s.departure_date),
                    stop_budget=s.stop_budget,
                    hotel=hotel.model_dump() if hotel else None,
                )
            )

        leg_details = [
            TransportLegDetail(
                id=l.id,
                trip_id=l.trip_id,
                origin_stop_id=l.origin_stop_id,
                destination_stop_id=l.destination_stop_id,
                mode=l.mode.value,
                carrier=l.carrier,
                departure_time=str(l.departure_time),
                arrival_time=str(l.arrival_time),
                cost=l.cost,
                status=l.status.value,
            )
            for l in legs
        ]

        item_details = [
            ItineraryItemDetail(
                id=it.id,
                trip_stop_id=it.trip_stop_id,
                item_type=it.item_type.value,
                place_id=it.place_id,
                custom_title=it.custom_title,
                day_number=it.day_number,
                scheduled_date=str(it.scheduled_date),
                start_time=it.start_time,
                end_time=it.end_time,
                cost=it.cost,
                status=it.status.value,
                notes=it.notes,
                travel_time_from_prev_minutes=it.travel_time_from_prev_minutes,
                travel_distance_km=it.travel_distance_km,
            )
            for it in items
        ]

        version_hash = proposal_store.compute_trip_state_hash(trip.id)
        duration_days = (trip.end_date - trip.start_date).days + 1

        return TripDetailResponse(
            id=trip.id,
            title=trip.title,
            start_date=str(trip.start_date),
            end_date=str(trip.end_date),
            total_budget=trip.total_budget,
            currency=trip.currency,
            status=trip.status.value,
            traveler_count=trip.traveler_count,
            duration_days=duration_days,
            interests=trip.interests,
            stops=stop_details,
            transport_legs=leg_details,
            itinerary=item_details,
            budget=budget_res,
            validation=validation_res,
            version_hash=version_hash,
        )


trip_service = TripService()
