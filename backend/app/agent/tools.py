"""
TravelPilot Typed Agent Tool Registry & Implementations
Exposes deterministic backend engines and database retrieval capabilities
as safe, typed tools callable by the Gemini agent.
"""

import time as pytime
from typing import Dict, Any, List, Optional, Callable
from datetime import date, datetime
import logging

from backend.app.db.supabase_client import get_db
from backend.app.core.budget_engine import budget_engine
from backend.app.core.schedule_validator import schedule_validator
from backend.app.core.geo_routing import geo_routing_engine, GeoPoint, RoutingMode
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
    HotelTier,
    PriceLevel,
    TransportMode,
)

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Raised when a tool fails during execution."""
    def __init__(self, message: str, tool_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.tool_name = tool_name
        self.details = details or {}


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()

    def register(self, name: str, func: Callable, schema: Dict[str, Any]):
        self._tools[name] = func
        self._schemas[name] = schema

    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def get_schema(self, name: str) -> Optional[Dict[str, Any]]:
        return self._schemas.get(name)

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        return list(self._schemas.values())

    def execute(self, name: str, args: Dict[str, Any], trip_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Safely executes a registered tool with argument validation, exception handling,
        and structured AgentEvent logging.
        """
        tool = self.get_tool(name)
        if not tool:
            return {
                "success": False,
                "error_code": "TOOL_NOT_FOUND",
                "message": f"Tool '{name}' is not registered.",
            }

        db = get_db()
        start_time = pytime.perf_counter()

        # 1. Log Tool Call Event
        if trip_id:
            db.record_agent_event(
                AgentEvent(
                    trip_id=trip_id,
                    event_type=AgentEventType.TOOL_CALL,
                    tool_name=name,
                    input_summary=str({k: v for k, v in args.items() if k != "trip_id"})[:200],
                    status="info",
                )
            )

        # 2. Execute Tool
        try:
            result = tool(**args)
            duration_ms = int((pytime.perf_counter() - start_time) * 1000)

            # 3. Log Tool Result Event
            if trip_id:
                result_count = len(result) if isinstance(result, list) else 1
                db.record_agent_event(
                    AgentEvent(
                        trip_id=trip_id,
                        event_type=AgentEventType.TOOL_RESULT,
                        tool_name=name,
                        result_summary=f"Success ({result_count} items)" if isinstance(result, list) else "Success",
                        duration_ms=duration_ms,
                        status="success",
                    )
                )

            return {
                "success": True,
                "tool": name,
                "data": result,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            duration_ms = int((pytime.perf_counter() - start_time) * 1000)
            logger.error(f"Error executing tool '{name}': {e}", exc_info=True)

            if trip_id:
                db.record_agent_event(
                    AgentEvent(
                        trip_id=trip_id,
                        event_type=AgentEventType.ERROR,
                        tool_name=name,
                        result_summary=f"Tool error: {str(e)}",
                        duration_ms=duration_ms,
                        status="error",
                    )
                )

            return {
                "success": False,
                "tool": name,
                "error_code": "TOOL_EXECUTION_ERROR",
                "message": str(e),
                "duration_ms": duration_ms,
            }

    # =========================================================================
    # Tool Implementations
    # =========================================================================

    def _register_default_tools(self):
        # 1. search_destinations
        self.register(
            name="search_destinations",
            func=self._search_destinations,
            schema={
                "name": "search_destinations",
                "description": "Resolves destination cities/regions dynamically matching user query (e.g. 'Hyderabad', 'Hampi', 'Goa').",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "City or destination name to search."}
                    },
                    "required": ["query"],
                },
            },
        )

        # 2. search_places
        self.register(
            name="search_places",
            func=self._search_places,
            schema={
                "name": "search_places",
                "description": "Retrieves verified attractions and landmarks for a destination with opening hours, entry fees, closed days, and ratings.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "destination_id": {"type": "STRING", "description": "UUID of the destination."},
                        "category": {"type": "STRING", "description": "Optional category filter: historical, nature, religious, beach, museum, shopping."},
                        "max_budget": {"type": "NUMBER", "description": "Optional max entry fee in INR."},
                    },
                    "required": ["destination_id"],
                },
            },
        )

        # 3. get_place_details
        self.register(
            name="get_place_details",
            func=self._get_place_details,
            schema={
                "name": "get_place_details",
                "description": "Retrieves detailed attributes for a specific place including exact hours, closed days, entry cost, and description.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "place_id": {"type": "STRING", "description": "UUID of the place."}
                    },
                    "required": ["place_id"],
                },
            },
        )

        # 4. search_hotels
        self.register(
            name="search_hotels",
            func=self._search_hotels,
            schema={
                "name": "search_hotels",
                "description": "Searches verified accommodations in a destination matching budget tier and price constraints.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "destination_id": {"type": "STRING", "description": "UUID of the destination."},
                        "tier": {"type": "STRING", "description": "Optional tier: budget, mid-range, luxury, hostel."},
                        "max_price": {"type": "NUMBER", "description": "Optional max price per night in INR."},
                    },
                    "required": ["destination_id"],
                },
            },
        )

        # 5. search_restaurants
        self.register(
            name="search_restaurants",
            func=self._search_restaurants,
            schema={
                "name": "search_restaurants",
                "description": "Searches dining options in a destination matching cuisine or price level.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "destination_id": {"type": "STRING", "description": "UUID of the destination."},
                        "cuisine": {"type": "STRING", "description": "Optional cuisine type."},
                        "price_level": {"type": "STRING", "description": "Optional price level: budget, mid-range, fine-dining."},
                    },
                    "required": ["destination_id"],
                },
            },
        )

        # 6. search_transport
        self.register(
            name="search_transport",
            func=self._search_transport,
            schema={
                "name": "search_transport",
                "description": "Searches verified inter-city transport options (train, flight, bus, cab) between two destinations.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "origin_destination_id": {"type": "STRING", "description": "Origin destination UUID."},
                        "dest_destination_id": {"type": "STRING", "description": "Target destination UUID."},
                        "mode": {"type": "STRING", "description": "Optional transport mode: train, flight, bus, cab."},
                    },
                    "required": ["origin_destination_id", "dest_destination_id"],
                },
            },
        )

        # 7. calculate_travel_time
        self.register(
            name="calculate_travel_time",
            func=self._calculate_travel_time,
            schema={
                "name": "calculate_travel_time",
                "description": "Deterministically calculates estimated travel distance and time in minutes between two coordinate pairs.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "origin_lat": {"type": "NUMBER", "description": "Origin latitude."},
                        "origin_lng": {"type": "NUMBER", "description": "Origin longitude."},
                        "dest_lat": {"type": "NUMBER", "description": "Destination latitude."},
                        "dest_lng": {"type": "NUMBER", "description": "Destination longitude."},
                        "mode": {"type": "STRING", "description": "Transport mode: walk, bicycle, car, cab, bus, metro, train, flight (default: cab)."},
                    },
                    "required": ["origin_lat", "origin_lng", "dest_lat", "dest_lng"],
                },
            },
        )

        # 8. validate_itinerary
        self.register(
            name="validate_itinerary",
            func=self._validate_itinerary,
            schema={
                "name": "validate_itinerary",
                "description": "Deterministically validates an itinerary schedule against opening hours, closed days, time overlaps, and transit buffers.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "items": {"type": "ARRAY", "description": "List of itinerary draft items to validate."},
                        "stops": {"type": "ARRAY", "description": "Optional list of trip stops."},
                        "transport_legs": {"type": "ARRAY", "description": "Optional list of inter-city transport legs."},
                    },
                    "required": ["items"],
                },
            },
        )

        # 9. calculate_budget
        self.register(
            name="calculate_budget",
            func=self._calculate_budget,
            schema={
                "name": "calculate_budget",
                "description": "Deterministically computes total budget breakdown, category sums, daily costs, remaining balance, and variance.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "total_budget": {"type": "NUMBER", "description": "Total user budget in INR."},
                        "traveler_count": {"type": "INTEGER", "description": "Number of travelers (default: 1)."},
                        "stops": {"type": "ARRAY", "description": "List of trip stops with dates and destination IDs."},
                        "hotels": {"type": "ARRAY", "description": "List of selected hotels per stop."},
                        "transport_legs": {"type": "ARRAY", "description": "List of inter-city transport legs."},
                        "items": {"type": "ARRAY", "description": "List of scheduled itinerary items."},
                        "daily_food_estimate": {"type": "NUMBER", "description": "Optional daily food estimate per person."},
                    },
                    "required": ["total_budget"],
                },
            },
        )

        # 10. find_alternatives
        self.register(
            name="find_alternatives",
            func=self._find_alternatives,
            schema={
                "name": "find_alternatives",
                "description": "Finds candidate alternative places nearby when an attraction is closed, unavailable, or rejected by user.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "place_id": {"type": "STRING", "description": "UUID of the place to replace."},
                        "category": {"type": "STRING", "description": "Optional desired category for alternative."},
                        "max_distance_km": {"type": "NUMBER", "description": "Max search radius in km (default: 15.0)."},
                    },
                    "required": ["place_id"],
                },
            },
        )

        # 11. get_trip_state
        self.register(
            name="get_trip_state",
            func=self._get_trip_state,
            schema={
                "name": "get_trip_state",
                "description": "Retrieves the current operational trip state, including stops, itinerary items, transport legs, and disruptions.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "trip_id": {"type": "STRING", "description": "UUID of the trip to retrieve."}
                    },
                    "required": ["trip_id"],
                },
            },
        )

        # 12. update_itinerary
        self.register(
            name="update_itinerary",
            func=self._update_itinerary,
            schema={
                "name": "update_itinerary",
                "description": "Persists or updates itinerary items, stops, and transport legs for an active trip.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "trip_id": {"type": "STRING", "description": "UUID of the trip."},
                        "items": {"type": "ARRAY", "description": "List of updated itinerary items."},
                        "stops": {"type": "ARRAY", "description": "Optional list of updated trip stops."},
                        "transport_legs": {"type": "ARRAY", "description": "Optional list of updated transport legs."},
                    },
                    "required": ["trip_id", "items"],
                },
            },
        )

    # =========================================================================
    # Internal Implementations
    # =========================================================================

    def _search_destinations(self, query: str) -> List[Dict[str, Any]]:
        db = get_db()
        destinations = db.search_destinations(query)
        return [
            {
                "id": d.id,
                "name": d.name,
                "state_province": d.state_province,
                "country": d.country,
                "latitude": d.latitude,
                "longitude": d.longitude,
                "ideal_duration_days": d.ideal_duration_days,
                "average_daily_cost": d.average_daily_cost,
                "description": d.description,
            }
            for d in destinations
        ]

    def _search_places(
        self,
        destination_id: str,
        category: Optional[str] = None,
        max_budget: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        db = get_db()
        places = db.search_places(destination_id, category=category, max_entry_fee=max_budget)
        return [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "description": p.description,
                "entry_fee": p.entry_fee,
                "typical_duration_minutes": p.typical_duration_minutes,
                "rating": p.rating,
                "open_time": p.open_time,
                "close_time": p.close_time,
                "closed_days": p.closed_days,
                "latitude": p.latitude,
                "longitude": p.longitude,
            }
            for p in places
        ]

    def _get_place_details(self, place_id: str) -> Dict[str, Any]:
        db = get_db()
        place = db.places.get(place_id)
        if not place:
            raise ToolExecutionError(f"Place with id '{place_id}' not found.", "get_place_details")
        return place.model_dump()

    def _search_hotels(
        self,
        destination_id: str,
        tier: Optional[str] = None,
        max_price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        db = get_db()
        hotels = db.search_hotels(destination_id, tier=tier, max_price=max_price)
        return [
            {
                "id": h.id,
                "name": h.name,
                "tier": h.tier.value if hasattr(h.tier, "value") else str(h.tier),
                "price_per_night": h.price_per_night,
                "rating": h.rating,
                "amenities": h.amenities,
                "latitude": h.latitude,
                "longitude": h.longitude,
            }
            for h in hotels
        ]

    def _search_restaurants(
        self,
        destination_id: str,
        cuisine: Optional[str] = None,
        price_level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        db = get_db()
        rests = db.search_restaurants(destination_id, price_level=price_level)
        if cuisine:
            rests = [r for r in rests if cuisine.lower() in r.cuisine.lower()]
        return [
            {
                "id": r.id,
                "name": r.name,
                "cuisine": r.cuisine,
                "price_level": r.price_level.value if hasattr(r.price_level, "value") else str(r.price_level),
                "average_cost_per_person": r.average_cost_per_person,
                "open_time": r.open_time,
                "close_time": r.close_time,
                "rating": r.rating,
            }
            for r in rests
        ]

    def _search_transport(
        self,
        origin_destination_id: str,
        dest_destination_id: str,
        mode: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        db = get_db()
        transports = db.search_transport(origin_destination_id, dest_destination_id, mode=mode)
        return [
            {
                "id": t.id,
                "origin_destination_id": t.origin_destination_id,
                "dest_destination_id": t.dest_destination_id,
                "mode": t.mode.value if hasattr(t.mode, "value") else str(t.mode),
                "carrier": t.carrier,
                "code": t.code,
                "typical_duration_minutes": t.typical_duration_minutes,
                "estimated_cost": t.estimated_cost,
                "departure_schedules": t.departure_schedules,
            }
            for t in transports
        ]

    def _calculate_travel_time(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        mode: str = "cab"
    ) -> Dict[str, Any]:
        p1 = GeoPoint(latitude=origin_lat, longitude=origin_lng)
        p2 = GeoPoint(latitude=dest_lat, longitude=dest_lng)
        try:
            routing_mode = RoutingMode(mode.lower())
        except ValueError:
            routing_mode = RoutingMode.CAB

        estimate = geo_routing_engine.estimate_travel_time(p1, p2, mode=routing_mode)
        return {
            "distance_km": estimate.distance_km,
            "duration_minutes": estimate.duration_minutes,
            "mode": estimate.mode.value,
            "notes": estimate.notes,
        }

    def _validate_itinerary(
        self,
        items: List[Dict[str, Any]],
        stops: Optional[List[Dict[str, Any]]] = None,
        transport_legs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        db = get_db()
        itinerary_objs = []
        for i in items:
            if isinstance(i, dict):
                # Ensure date is parsed
                s_date = i.get("scheduled_date")
                if isinstance(s_date, str):
                    s_date = date.fromisoformat(s_date)
                i_copy = dict(i)
                i_copy["scheduled_date"] = s_date
                itinerary_objs.append(ItineraryItem(**i_copy))
            elif isinstance(i, ItineraryItem):
                itinerary_objs.append(i)

        stop_objs = [TripStop(**s) if isinstance(s, dict) else s for s in (stops or [])]
        leg_objs = [TransportLeg(**l) if isinstance(l, dict) else l for l in (transport_legs or [])]

        res = schedule_validator.validate(
            trip_stops=stop_objs,
            itinerary_items=itinerary_objs,
            transport_legs=leg_objs,
            places_by_id=db.places,
            restaurants_by_id=db.restaurants,
        )
        return res.model_dump()

    def _calculate_budget(
        self,
        total_budget: float,
        traveler_count: int = 1,
        stops: Optional[List[Dict[str, Any]]] = None,
        hotels: Optional[List[Dict[str, Any]]] = None,
        transport_legs: Optional[List[Dict[str, Any]]] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        daily_food_estimate: Optional[float] = None,
    ) -> Dict[str, Any]:
        db = get_db()
        stop_objs = []
        for s in (stops or []):
            if isinstance(s, dict):
                arr = s.get("arrival_date")
                dep = s.get("departure_date")
                s_copy = dict(s)
                if isinstance(arr, str):
                    s_copy["arrival_date"] = date.fromisoformat(arr)
                if isinstance(dep, str):
                    s_copy["departure_date"] = date.fromisoformat(dep)
                stop_objs.append(TripStop(**s_copy))
            else:
                stop_objs.append(s)

        hotels_by_stop = {}
        for h in (hotels or []):
            hotel_obj = Hotel(**h) if isinstance(h, dict) else h
            hotels_by_stop[hotel_obj.destination_id] = hotel_obj

        leg_objs = [TransportLeg(**l) if isinstance(l, dict) else l for l in (transport_legs or [])]
        itinerary_objs = []
        for i in (items or []):
            if isinstance(i, dict):
                s_date = i.get("scheduled_date")
                if isinstance(s_date, str):
                    s_date = date.fromisoformat(s_date)
                i_copy = dict(i)
                i_copy["scheduled_date"] = s_date
                itinerary_objs.append(ItineraryItem(**i_copy))
            else:
                itinerary_objs.append(i)

        destinations_by_stop = {
            s.id: db.destinations.get(s.destination_id) for s in stop_objs if s.destination_id in db.destinations
        }

        res = budget_engine.calculate(
            total_budget=total_budget,
            traveler_count=traveler_count,
            trip_stops=stop_objs,
            hotels_by_stop=hotels_by_stop,
            transport_legs=leg_objs,
            itinerary_items=itinerary_objs,
            destinations_by_stop=destinations_by_stop,
            daily_food_estimate_per_person=daily_food_estimate,
        )
        return res.model_dump()

    def _find_alternatives(
        self,
        place_id: str,
        category: Optional[str] = None,
        max_distance_km: Optional[float] = 15.0
    ) -> List[Dict[str, Any]]:
        db = get_db()
        target = db.places.get(place_id)
        if not target:
            raise ToolExecutionError(f"Place '{place_id}' not found.", "find_alternatives")

        dest_places = db.search_places(target.destination_id, category=category)
        candidates = [p for p in dest_places if p.id != place_id]

        target_pt = GeoPoint(latitude=target.latitude, longitude=target.longitude)
        results = []

        for p in candidates:
            dist = geo_routing_engine.calculate_distance(
                target_pt, GeoPoint(latitude=p.latitude, longitude=p.longitude)
            )
            if max_distance_km is None or dist <= max_distance_km:
                results.append({
                    "id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "entry_fee": p.entry_fee,
                    "rating": p.rating,
                    "distance_from_target_km": dist,
                    "open_time": p.open_time,
                    "close_time": p.close_time,
                    "closed_days": p.closed_days,
                })

        return sorted(results, key=lambda x: x["distance_from_target_km"])

    def _get_trip_state(self, trip_id: str) -> Dict[str, Any]:
        db = get_db()
        trip = db.get_trip(trip_id)
        if not trip:
            raise ToolExecutionError(f"Trip '{trip_id}' not found.", "get_trip_state")

        stops = db.get_trip_stops(trip_id)
        legs = db.get_transport_legs_for_trip(trip_id)
        items = []
        for s in stops:
            items.extend(db.get_itinerary_items_for_stop(s.id))
        events = db.get_agent_events_for_trip(trip_id)

        return {
            "trip": trip.model_dump(),
            "stops": [s.model_dump() for s in stops],
            "transport_legs": [l.model_dump() for l in legs],
            "items": [i.model_dump() for i in items],
            "events_count": len(events),
        }

    def _update_itinerary(
        self,
        trip_id: str,
        items: List[Dict[str, Any]],
        stops: Optional[List[Dict[str, Any]]] = None,
        transport_legs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        db = get_db()
        trip = db.get_trip(trip_id)
        if not trip:
            raise ToolExecutionError(f"Trip '{trip_id}' not found.", "update_itinerary")

        # Update stops if provided
        if stops:
            for s in stops:
                s_obj = TripStop(**s) if isinstance(s, dict) else s
                db.trip_stops[s_obj.id] = s_obj

        # Update legs if provided
        if transport_legs:
            for l in transport_legs:
                l_obj = TransportLeg(**l) if isinstance(l, dict) else l
                db.transport_legs[l_obj.id] = l_obj

        # Update items
        for i in items:
            i_obj = ItineraryItem(**i) if isinstance(i, dict) else i
            db.itinerary_items[i_obj.id] = i_obj

        db.record_agent_event(
            AgentEvent(
                trip_id=trip_id,
                event_type=AgentEventType.STATE_UPDATE,
                result_summary=f"Updated {len(items)} itinerary items.",
                status="success",
            )
        )

        return {
            "success": True,
            "trip_id": trip_id,
            "items_count": len(items),
        }


tool_registry = ToolRegistry()
