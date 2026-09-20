"""
Destinations API Routes
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.db.supabase_client import get_db
from backend.app.api.schemas.destinations import (
    DestinationSummaryResponse,
    DestinationListResponse,
    DestinationDetailResponse,
    PlaceResponse,
    HotelResponse,
    RestaurantResponse,
    TransportConnectionResponse,
)

router = APIRouter(prefix="/destinations", tags=["Destinations"])


@router.get(
    "",
    response_model=DestinationListResponse,
    summary="List and search destinations",
    description="Retrieve all available travel destinations or filter by search query.",
)
def list_destinations(q: Optional[str] = Query(None, description="Search term for destination name or state")):
    db = get_db()
    if q and q.strip():
        destinations = db.search_destinations(q.strip())
    else:
        destinations = list(db.destinations.values())

    items = [
        DestinationSummaryResponse(
            id=d.id,
            name=d.name,
            state_province=d.state_province,
            country=d.country,
            latitude=d.latitude,
            longitude=d.longitude,
            description=d.description,
            ideal_duration_days=d.ideal_duration_days,
            average_daily_cost=d.average_daily_cost,
            hero_image_url=d.hero_image_url,
        )
        for d in destinations
    ]

    return DestinationListResponse(items=items, count=len(items))


@router.get(
    "/{destination_id}",
    response_model=DestinationDetailResponse,
    summary="Get destination details",
    description="Retrieve comprehensive destination reference data including attractions, hotels, restaurants, and transport connections.",
)
def get_destination(destination_id: str):
    db = get_db()
    destination = db.destinations.get(destination_id)
    if not destination:
        # Also try searching by name (case-insensitive)
        matches = [d for d in db.destinations.values() if d.name.lower() == destination_id.lower()]
        if matches:
            destination = matches[0]
            destination_id = destination.id
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Destination '{destination_id}' not found.",
            )

    places = db.search_places(destination.id)
    hotels = db.search_hotels(destination.id)
    restaurants = db.search_restaurants(destination.id)
    transport = db.search_transport(origin_destination_id=destination.id)

    dest_summary = DestinationSummaryResponse(
        id=destination.id,
        name=destination.name,
        state_province=destination.state_province,
        country=destination.country,
        latitude=destination.latitude,
        longitude=destination.longitude,
        description=destination.description,
        ideal_duration_days=destination.ideal_duration_days,
        average_daily_cost=destination.average_daily_cost,
        hero_image_url=destination.hero_image_url,
    )

    return DestinationDetailResponse(
        destination=dest_summary,
        places=[
            PlaceResponse(
                id=p.id,
                destination_id=p.destination_id,
                name=p.name,
                category=p.category,
                description=p.description,
                entry_fee=p.entry_fee,
                typical_duration_minutes=p.typical_duration_minutes,
                rating=p.rating,
                open_time=p.open_time,
                close_time=p.close_time,
                closed_days=p.closed_days,
                latitude=p.latitude,
                longitude=p.longitude,
                image_url=p.image_url,
            )
            for p in places
        ],
        hotels=[
            HotelResponse(
                id=h.id,
                destination_id=h.destination_id,
                name=h.name,
                tier=h.tier.value if hasattr(h.tier, "value") else str(h.tier),
                price_per_night=h.price_per_night,
                rating=h.rating,
                amenities=h.amenities,
                image_url=h.image_url,
                address=h.address,
            )
            for h in hotels
        ],
        restaurants=[
            RestaurantResponse(
                id=r.id,
                destination_id=r.destination_id,
                name=r.name,
                cuisine=r.cuisine,
                price_level=r.price_level.value if hasattr(r.price_level, "value") else str(r.price_level) if r.price_level else None,
                average_cost_per_person=r.average_cost_per_person,
                rating=r.rating,
                open_time=r.open_time,
                close_time=r.close_time,
            )
            for r in restaurants
        ],
        transport_connections=[
            TransportConnectionResponse(
                id=t.id,
                origin_id=t.origin_destination_id,
                destination_id=t.dest_destination_id,
                mode=t.mode.value if hasattr(t.mode, "value") else str(t.mode),
                carrier=t.carrier,
                code=t.code,
                estimated_cost=t.estimated_cost,
                typical_duration_minutes=t.typical_duration_minutes,
                frequency=f"{t.frequency_per_day} per day" if hasattr(t, "frequency_per_day") else None,
            )
            for t in transport
        ],
    )
