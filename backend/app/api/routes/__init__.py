"""
API Routes Registration
"""

from fastapi import APIRouter
from backend.app.api.routes.destinations import router as destinations_router
from backend.app.api.routes.trips import router as trips_router
from backend.app.api.routes.agent import router as agent_router
from backend.app.api.routes.disruptions import router as disruptions_router
from backend.app.api.routes.simulations import router as simulations_router

api_router = APIRouter(prefix="/api")

api_router.include_router(destinations_router)
api_router.include_router(trips_router)
api_router.include_router(agent_router)
api_router.include_router(disruptions_router)
api_router.include_router(simulations_router)

__all__ = ["api_router"]
