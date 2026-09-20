"""
TravelPilot Supabase Runtime Database Store
Provides a Supabase REST API backed implementation of the InMemoryDB interface.
"""
from typing import Dict, List, Optional, Any
import logging
from uuid import UUID
from collections.abc import Mapping

from backend.app.models.entities import (
    Destination, Place, Hotel, Restaurant, TransportOption, User,
    Trip, TripStop, TransportLeg, ItineraryItem, Disruption, AgentEvent
)

logger = logging.getLogger(__name__)

class LazyDictWrapper(Mapping):
    """A dictionary-like wrapper that lazily fetches a specific table from Supabase."""
    def __init__(self, client, table_name: str, model_cls):
        self.client = client
        self.table_name = table_name
        self.model_cls = model_cls

    def __getitem__(self, key):
        res = self.client.table(self.table_name).select("*").eq("id", str(key)).execute()
        if not res.data:
            raise KeyError(key)
        return self.model_cls(**res.data[0])
    
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __iter__(self):
        res = self.client.table(self.table_name).select("id").execute()
        return (row["id"] for row in res.data)

    def __len__(self):
        res = self.client.table(self.table_name).select("id", count="exact").execute()
        return res.count

    def values(self):
        res = self.client.table(self.table_name).select("*").execute()
        return [self.model_cls(**row) for row in res.data]

    def __contains__(self, key):
        res = self.client.table(self.table_name).select("id").eq("id", str(key)).execute()
        return len(res.data) > 0


class SupabaseStore:
    def __init__(self, client):
        self.client = client
        
        # Lazy dictionary properties mirroring InMemoryDB
        self.destinations = LazyDictWrapper(client, "destinations", Destination)
        self.places = LazyDictWrapper(client, "places", Place)
        self.hotels = LazyDictWrapper(client, "hotels", Hotel)
        self.restaurants = LazyDictWrapper(client, "restaurants", Restaurant)
        self.transport_options = LazyDictWrapper(client, "transport_options", TransportOption)
        self.trips = LazyDictWrapper(client, "trips", Trip)

    # --- Destination-Agnostic Search Helpers ---

    def search_destinations(self, query: str) -> List[Destination]:
        q = query.lower().strip()
        # Fallback to local filtering for complex logic since we have only 8 destinations
        all_dest = self.destinations.values()
        results = []
        for dest in all_dest:
            if (q in dest.name.lower() or 
               (dest.state_province and q in dest.state_province.lower()) or 
               q in dest.country.lower()):
                results.append(dest)
        return results

    def get_destination_by_name(self, name: str, country: str = "India") -> Optional[Destination]:
        res = self.client.table("destinations").select("*").ilike("name", name).ilike("country", country).execute()
        if res.data:
            return Destination(**res.data[0])
        return None

    def search_places(self, destination_id: str, category: Optional[str] = None, max_entry_fee: Optional[float] = None) -> List[Place]:
        query = self.client.table("places").select("*").eq("destination_id", destination_id)
        if category:
            query = query.ilike("category", category)
        res = query.execute()
        places = [Place(**row) for row in res.data]
        if max_entry_fee is not None:
            places = [p for p in places if p.entry_fee <= max_entry_fee]
        return sorted(places, key=lambda x: x.rating, reverse=True)

    def search_hotels(self, destination_id: str, tier: Optional[str] = None, max_price: Optional[float] = None) -> List[Hotel]:
        query = self.client.table("hotels").select("*").eq("destination_id", destination_id)
        if tier:
            query = query.ilike("tier", tier)
        res = query.execute()
        hotels = [Hotel(**row) for row in res.data]
        if max_price is not None:
            hotels = [h for h in hotels if h.price_per_night <= max_price]
        return sorted(hotels, key=lambda x: x.rating, reverse=True)

    def search_restaurants(self, destination_id: str, price_level: Optional[str] = None) -> List[Restaurant]:
        query = self.client.table("restaurants").select("*").eq("destination_id", destination_id)
        if price_level:
            query = query.ilike("price_level", price_level)
        res = query.execute()
        restaurants = [Restaurant(**row) for row in res.data]
        return sorted(restaurants, key=lambda x: x.rating, reverse=True)

    def search_transport(self, origin_destination_id: Optional[str] = None, dest_destination_id: Optional[str] = None, mode: Optional[str] = None) -> List[TransportOption]:
        query = self.client.table("transport_options").select("*")
        if origin_destination_id:
            query = query.eq("origin_destination_id", origin_destination_id)
        if dest_destination_id:
            query = query.eq("dest_destination_id", dest_destination_id)
        if mode:
            query = query.ilike("mode", mode)
        res = query.execute()
        trans = [TransportOption(**row) for row in res.data]
        return sorted(trans, key=lambda x: x.typical_duration_minutes)

    # --- Trip Operational CRUD ---

    def create_trip(self, trip: Trip) -> Trip:
        # Convert date to isoformat
        data = trip.model_dump(mode="json")
        self.client.table("trips").insert(data).execute()
        return trip
        
    def update_trip(self, trip: Trip) -> Trip:
        data = trip.model_dump(mode="json")
        self.client.table("trips").update(data).eq("id", str(trip.id)).execute()
        return trip

    def get_trip(self, trip_id: str) -> Optional[Trip]:
        return self.trips.get(trip_id)

    def add_trip_stop(self, stop: TripStop) -> TripStop:
        data = stop.model_dump(mode="json")
        self.client.table("trip_stops").insert(data).execute()
        return stop

    def get_trip_stops(self, trip_id: str) -> List[TripStop]:
        res = self.client.table("trip_stops").select("*").eq("trip_id", trip_id).execute()
        stops = [TripStop(**row) for row in res.data]
        return sorted(stops, key=lambda s: s.order_index)

    def add_itinerary_item(self, item: ItineraryItem) -> ItineraryItem:
        data = item.model_dump(mode="json")
        self.client.table("itinerary_items").insert(data).execute()
        return item

    def get_itinerary_items_for_stop(self, trip_stop_id: str) -> List[ItineraryItem]:
        res = self.client.table("itinerary_items").select("*").eq("trip_stop_id", trip_stop_id).execute()
        items = [ItineraryItem(**row) for row in res.data]
        return sorted(items, key=lambda i: i.start_time)

    def add_transport_leg(self, leg: TransportLeg) -> TransportLeg:
        data = leg.model_dump(mode="json")
        self.client.table("transport_legs").insert(data).execute()
        return leg

    def get_transport_legs_for_trip(self, trip_id: str) -> List[TransportLeg]:
        res = self.client.table("transport_legs").select("*").eq("trip_id", trip_id).execute()
        legs = [TransportLeg(**row) for row in res.data]
        return sorted(legs, key=lambda l: l.departure_time)

    def record_agent_event(self, event: AgentEvent) -> AgentEvent:
        data = event.model_dump(mode="json")
        self.client.table("agent_events").insert(data).execute()
        return event

    def get_agent_events_for_trip(self, trip_id: str) -> List[AgentEvent]:
        res = self.client.table("agent_events").select("*").eq("trip_id", trip_id).execute()
        events = [AgentEvent(**row) for row in res.data]
        return sorted(events, key=lambda e: e.created_at)

    def add_disruption(self, disruption: Disruption) -> Disruption:
        data = disruption.model_dump(mode="json")
        self.client.table("disruptions").insert(data).execute()
        return disruption

    def update_disruption(self, disruption: Disruption) -> Disruption:
        data = disruption.model_dump(mode="json")
        self.client.table("disruptions").update(data).eq("id", str(disruption.id)).execute()
        return disruption

    def get_disruptions_for_trip(self, trip_id: str) -> List[Disruption]:
        res = self.client.table("disruptions").select("*").eq("trip_id", trip_id).execute()
        return [Disruption(**row) for row in res.data]
        
    def delete_trip_stops_for_trip(self, trip_id: str):
        self.client.table("trip_stops").delete().eq("trip_id", trip_id).execute()
        
    def delete_itinerary_items_for_trip(self, trip_id: str):
        self.client.table("itinerary_items").delete().eq("trip_id", trip_id).execute()
        
    def delete_transport_legs_for_trip(self, trip_id: str):
        self.client.table("transport_legs").delete().eq("trip_id", trip_id).execute()
