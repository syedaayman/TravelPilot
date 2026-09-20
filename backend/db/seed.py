"""
TravelPilot Seed Execution Script
Run with: python backend/db/seed.py
Populates Supabase PostgreSQL if configured, or tests in-memory seed data integrity.
"""

import sys
import logging
from backend.app.config import settings
from backend.app.db.seed_data import (
    DESTINATIONS_DATA,
    PLACES_DATA,
    HOTELS_DATA,
    RESTAURANTS_DATA,
    TRANSPORT_OPTIONS_DATA,
)
from backend.app.db.supabase_client import get_supabase_client
from backend.app.db.memory_store import InMemoryDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")


def seed_database():
    logger.info("Initializing TravelPilot Reference Seed Data...")
    logger.info(f"Target Destinations count: {len(DESTINATIONS_DATA)}")
    logger.info(f"Places / Attractions count: {len(PLACES_DATA)}")
    logger.info(f"Hotels count: {len(HOTELS_DATA)}")
    logger.info(f"Restaurants count: {len(RESTAURANTS_DATA)}")
    logger.info(f"Inter-city Transport count: {len(TRANSPORT_OPTIONS_DATA)}")

    # Verify via in-memory load
    mem_db = InMemoryDB(load_seed=True)
    assert len(mem_db.destinations) == len(DESTINATIONS_DATA)
    assert len(mem_db.places) == len(PLACES_DATA)
    assert len(mem_db.hotels) == len(HOTELS_DATA)
    assert len(mem_db.restaurants) == len(RESTAURANTS_DATA)
    assert len(mem_db.transport_options) == len(TRANSPORT_OPTIONS_DATA)
    logger.info("In-memory relational store successfully validated!")

    # Attempt Supabase remote seeding if configured
    supabase = get_supabase_client()
    if supabase is not None:
        logger.info("Supabase client detected. Upserting reference datasets...")
        try:
            supabase.table("destinations").upsert(DESTINATIONS_DATA).execute()
            supabase.table("places").upsert(PLACES_DATA).execute()
            supabase.table("hotels").upsert(HOTELS_DATA).execute()
            supabase.table("restaurants").upsert(RESTAURANTS_DATA).execute()
            supabase.table("transport_options").upsert(TRANSPORT_OPTIONS_DATA).execute()
            logger.info("Supabase remote database successfully seeded!")
        except Exception as e:
            logger.error(f"Error seeding Supabase: {e}")
    else:
        logger.info("Supabase not configured or in mock mode. Seed data active in local store.")

    return True


if __name__ == "__main__":
    success = seed_database()
    if not success:
        sys.exit(1)
