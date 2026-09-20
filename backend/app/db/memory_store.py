"""
TravelPilot In-Memory Database Store
Provides deterministic, in-memory relational store with seed loading, foreign key integrity,
and search capabilities for testing, mock mode, and standalone execution.
"""

from typing import Dict, List, Optional, Any, Callable
from uuid import uuid4
from datetime import datetime
import copy

from backend.app.models.entities import (
    Destination,
    Place,
    Hotel,
    Restaurant,
    TransportOption,
    User,
    Trip,
    TripStop,
    TransportLeg,
    ItineraryItem,
    Disruption,
    AgentEvent,
)
from backend.app.db.seed_data import (
    DESTINATIONS_DATA,
    PLACES_DATA,
    HOTELS_DATA,
    RESTAURANTS_DATA,
    TRANSPORT_OPTIONS_DATA,
)


class InMemoryDB:
    def __init__(self, load_seed: bool = True):
        self.destinations: Dict[str, Destination] = {}
        self.places: Dict[str, Place] = {}
        self.hotels: Dict[str, Hotel] = {}
        self.restaurants: Dict[str, Restaurant] = {}
        self.transport_options: Dict[str, TransportOption] = {}
        self.users: Dict[str, User] = {}
        self.trips: Dict[str, Trip] = {}
        self.trip_stops: Dict[str, TripStop] = {}
        self.transport_legs: Dict[str, TransportLeg] = {}
        self.itinerary_items: Dict[str, ItineraryItem] = {}
        self.disruptions: Dict[str, Disruption] = {}
        self.agent_events: Dict[str, AgentEvent] = {}

        if load_seed:
            self.load_seed_data()

    def load_seed_data(self):
        """Loads curated static reference data into memory."""
        for d in DESTINATIONS_DATA:
            dest = Destination(**d)
            self.destinations[dest.id] = dest

        for p in PLACES_DATA:
            place = Place(**p)
            self.places[place.id] = place

        for h in HOTELS_DATA:
            hotel = Hotel(**h)
            self.hotels[hotel.id] = hotel

        for r in RESTAURANTS_DATA:
            rest = Restaurant(**r)
            self.restaurants[rest.id] = rest

        for t in TRANSPORT_OPTIONS_DATA:
            trans = TransportOption(**t)
            self.transport_options[trans.id] = trans

    def clear(self):
        """Clears operational and reference data."""
        self.destinations.clear()
        self.places.clear()
        self.hotels.clear()
        self.restaurants.clear()
        self.transport_options.clear()
        self.users.clear()
        self.trips.clear()
        self.trip_stops.clear()
        self.transport_legs.clear()
        self.itinerary_items.clear()
        self.disruptions.clear()
        self.agent_events.clear()

    # --- Destination-Agnostic Search Helpers ---

    def search_destinations(self, query: str) -> List[Destination]:
        """Resolves destinations dynamically matching name, state, or country."""
        q = query.lower().strip()
        results = []
        for dest in self.destinations.values():
            if (
                q in dest.name.lower()
                or (dest.state_province and q in dest.state_province.lower())
                or q in dest.country.lower()
            ):
                results.append(dest)
        return results

    def get_destination_by_name(self, name: str) -> Optional[Destination]:
        """Exact or case-insensitive match for destination name."""
        n = name.lower().strip()
        for dest in self.destinations.values():
            if dest.name.lower().strip() == n:
                return dest
        # Fallback to prefix/substring
        for dest in self.destinations.values():
            if n in dest.name.lower():
                return dest
        return None

    def search_places(
        self,
        destination_id: str,
        category: Optional[str] = None,
        max_entry_fee: Optional[float] = None
    ) -> List[Place]:
        results = []
        for p in self.places.values():
            if p.destination_id == destination_id:
                if category and p.category.lower() != category.lower():
                    continue
                if max_entry_fee is not None and p.entry_fee > max_entry_fee:
                    continue
                results.append(p)
        return sorted(results, key=lambda x: x.rating, reverse=True)

    def search_hotels(
        self,
        destination_id: str,
        tier: Optional[str] = None,
        max_price: Optional[float] = None
    ) -> List[Hotel]:
        results = []
        for h in self.hotels.values():
            if h.destination_id == destination_id:
                if tier and h.tier.value.lower() != tier.lower():
                    continue
                if max_price is not None and h.price_per_night > max_price:
                    continue
                results.append(h)
        return sorted(results, key=lambda x: x.price_per_night)

    def search_restaurants(
        self,
        destination_id: str,
        price_level: Optional[str] = None
    ) -> List[Restaurant]:
        results = []
        for r in self.restaurants.values():
            if r.destination_id == destination_id:
                if price_level and r.price_level.value.lower() != price_level.lower():
                    continue
                results.append(r)
        return sorted(results, key=lambda x: x.rating, reverse=True)

    def search_transport(
        self,
        origin_destination_id: Optional[str] = None,
        dest_destination_id: Optional[str] = None,
        mode: Optional[str] = None
    ) -> List[TransportOption]:
        results = []
        for t in self.transport_options.values():
            if origin_destination_id and t.origin_destination_id != origin_destination_id:
                continue
            if dest_destination_id and t.dest_destination_id != dest_destination_id:
                continue
            if mode and t.mode.value.lower() != mode.lower():
                continue
            results.append(t)
        return sorted(results, key=lambda x: x.typical_duration_minutes)

    # --- Trip Operational CRUD ---

    def create_trip(self, trip: Trip) -> Trip:
        self.trips[trip.id] = trip
        return trip

    def get_trip(self, trip_id: str) -> Optional[Trip]:
        return self.trips.get(trip_id)

    def update_trip(self, trip: Trip) -> Trip:
        if trip.id not in self.trips:
            raise ValueError(f"Trip {trip.id} does not exist.")
        self.trips[trip.id] = trip
        return trip

    def add_trip_stop(self, stop: TripStop) -> TripStop:
        # Validate foreign keys
        if stop.trip_id not in self.trips:
            raise ValueError(f"Trip {stop.trip_id} does not exist.")
        if stop.destination_id not in self.destinations:
            raise ValueError(f"Destination {stop.destination_id} does not exist.")
        self.trip_stops[stop.id] = stop
        return stop

    def get_trip_stops(self, trip_id: str) -> List[TripStop]:
        stops = [s for s in self.trip_stops.values() if s.trip_id == trip_id]
        return sorted(stops, key=lambda s: s.order_index)

    def add_itinerary_item(self, item: ItineraryItem) -> ItineraryItem:
        if item.trip_stop_id not in self.trip_stops:
            raise ValueError(f"TripStop {item.trip_stop_id} does not exist.")
        self.itinerary_items[item.id] = item
        return item

    def get_itinerary_items_for_stop(self, trip_stop_id: str) -> List[ItineraryItem]:
        items = [i for i in self.itinerary_items.values() if i.trip_stop_id == trip_stop_id]
        return sorted(items, key=lambda x: (x.day_number, x.start_time))

    def add_transport_leg(self, leg: TransportLeg) -> TransportLeg:
        if leg.trip_id not in self.trips:
            raise ValueError(f"Trip {leg.trip_id} does not exist.")
        self.transport_legs[leg.id] = leg
        return leg

    def get_transport_legs_for_trip(self, trip_id: str) -> List[TransportLeg]:
        legs = [l for l in self.transport_legs.values() if l.trip_id == trip_id]
        return sorted(legs, key=lambda l: l.departure_time)

    def record_agent_event(self, event: AgentEvent) -> AgentEvent:
        """Appends a structured agent audit event."""
        self.agent_events[event.id] = event
        return event

    def get_agent_events_for_trip(self, trip_id: str) -> List[AgentEvent]:
        events = [e for e in self.agent_events.values() if e.trip_id == trip_id]
        return sorted(events, key=lambda e: e.created_at or datetime.min)

    def add_disruption(self, disruption: Disruption) -> Disruption:
        self.disruptions[disruption.id] = disruption
        return disruption

    def update_disruption(self, disruption: Disruption) -> Disruption:
        if disruption.id not in self.disruptions:
            raise ValueError(f"Disruption {disruption.id} does not exist.")
        self.disruptions[disruption.id] = disruption
        return disruption

    def get_disruptions_for_trip(self, trip_id: str) -> List[Disruption]:
        return [d for d in self.disruptions.values() if d.trip_id == trip_id]


# Global memory store instance
memory_db = InMemoryDB(load_seed=True)
