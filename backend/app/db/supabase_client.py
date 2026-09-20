"""
TravelPilot Database Client Abstraction
Provides seamless access to Supabase PostgreSQL when credentials exist,
or transparently delegates to the in-memory mock repository for tests / local development.
"""

from typing import Optional, Any
import logging
from backend.app.config import settings
from backend.app.db.memory_store import InMemoryDB, memory_db

logger = logging.getLogger(__name__)

# Optional Supabase client instance
_supabase_client = None


def get_supabase_client() -> Optional[Any]:
    """Initializes or returns singleton Supabase client if configured."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if settings.is_supabase_configured:
        try:
            from supabase import create_client, Client
            _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            logger.info("Connected to remote Supabase database instance.")
            return _supabase_client
        except Exception as e:
            logger.warning(f"Failed to initialize Supabase client: {e}. Falling back to in-memory store.")
            return None
    return None


class DatabaseGateway:
    """
    Unified gateway for DB operations.
    If Supabase is connected and mode is 'supabase', operations can route to Supabase;
    otherwise, operations route to the deterministic in-memory store.
    """
    def __init__(self):
        self.memory: InMemoryDB = memory_db
        self.client = get_supabase_client()
        self.supabase_store = None
        if self.client:
            from backend.app.db.supabase_store import SupabaseStore
            self.supabase_store = SupabaseStore(self.client)

    @property
    def is_mock(self) -> bool:
        return self.client is None or settings.DB_MODE == "mock"

    def get_store(self) -> Any:
        """Returns the appropriate database store."""
        if not self.is_mock and self.supabase_store:
            return self.supabase_store
        return self.memory


db_gateway = DatabaseGateway()


def get_db() -> Any:
    """Dependency injection helper returning the database store."""
    return db_gateway.get_store()
