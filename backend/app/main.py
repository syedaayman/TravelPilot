"""
TravelPilot FastAPI Application
Entrypoint for the Intelligent Trip Planning & Disruption Management Backend.
"""

from typing import Any, Dict
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.db.supabase_client import db_gateway
from backend.app.api.routes import api_router
from backend.app.services.proposal_store import StaleProposalError

tags_metadata = [
    {"name": "Destinations", "description": "Destination search, catalogs, places, hotels, and transport connections."},
    {"name": "Trips", "description": "Single-city and multi-city trip creation, deterministic planning, and state retrieval."},
    {"name": "Agent", "description": "Conversational agent interaction powered by Gemini orchestrator with structured tool logs."},
    {"name": "Disruptions", "description": "Deterministic disruption impact analysis, candidate replanning, and safe apply/reject."},
    {"name": "Simulations", "description": "Isolated what-if scenario simulations with diff generation and apply/reject."},
    {"name": "Health", "description": "System health and telemetry."},
]

app = FastAPI(
    title="TravelPilot API",
    description="Intelligent Trip Planning & Disruption Management Agent REST API. Exposes deterministic planning engines, Gemini agent orchestration, disruption recovery, and what-if simulation.",
    version="1.0.0",
    openapi_tags=tags_metadata,
)

# CORS configuration for React / Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# EXCEPTION HANDLERS (Standardized Error Model)
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Derive clean error code from status code
    code_map = {
        400: "BAD_REQUEST",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        500: "INTERNAL_SERVER_ERROR",
    }
    code = code_map.get(exc.status_code, "ERROR")

    # Map message to domain error code if recognizable
    msg = str(exc.detail) if exc.detail else "An error occurred."
    if "Trip" in msg and "not found" in msg:
        code = "TRIP_NOT_FOUND"
    elif "Destination" in msg and "not found" in msg:
        code = "DESTINATION_NOT_FOUND"
    elif "Place" in msg and "not found" in msg:
        code = "PLACE_NOT_FOUND"
    elif "replan" in msg.lower() and "not found" in msg.lower():
        code = "REPLAN_NOT_FOUND"
    elif "simulation" in msg.lower() and "not found" in msg.lower():
        code = "SIMULATION_NOT_FOUND"
    elif "stale" in msg.lower():
        code = "STALE_PROPOSAL"
    elif "infeasible" in msg.lower():
        code = "SIMULATION_NOT_FEASIBLE"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": msg,
                "details": getattr(exc, "headers", None) or {},
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    simplified_details = []
    for err in errors:
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        msg = err.get("msg", "")
        simplified_details.append({"location": loc, "message": msg, "type": err.get("type", "")})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request payload or query parameters.",
                "details": {"validation_errors": simplified_details},
            }
        },
    )


@app.exception_handler(StaleProposalError)
async def stale_proposal_exception_handler(request: Request, exc: StaleProposalError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": {
                "code": "STALE_PROPOSAL",
                "message": exc.message,
                "details": {},
            }
        },
    )


import traceback
import logging

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Manually append CORS headers so frontend doesn't get blocked on 500
    origin = request.headers.get("origin")
    headers = {}
    if origin in settings.ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "*"
        headers["Access-Control-Allow-Headers"] = "*"
        
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal server error occurred.",
                "details": str(exc),
            }
        },
        headers=headers,
    )


# =============================================================================
# HEALTH & TELEMETRY ENDPOINTS
# =============================================================================

@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint confirming API service and database connectivity."""
    return {
        "status": "healthy",
        "service": "TravelPilot API",
        "environment": settings.ENVIRONMENT,
        "database_mode": "supabase" if not db_gateway.is_mock else "in_memory_mock",
        "reference_destinations_count": len(db_gateway.memory.destinations),
        "reference_places_count": len(db_gateway.memory.places),
    }


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "Welcome to TravelPilot: Intelligent Trip Planning & Disruption Management Agent",
        "docs_url": "/docs",
        "health_check": "/api/health",
    }


# Include API Routers under /api
app.include_router(api_router)
