# TravelPilot — System Architecture & Design Specification

> **Intelligent Trip Planning & Disruption Management Agent**  
> *Production-Style Agentic AI Prototype Architecture*

---

## 1. System Overview & Core Philosophy

**TravelPilot** is an agentic AI travel planning and disruption management system built for high reliability, deterministic accuracy, and intuitive conversational interaction. It supports both **single-city** and **multi-city** itineraries through a unified, destination-agnostic planning pipeline.

### Core Philosophy: Agentic Orchestration + Deterministic Execution
A common failure mode in LLM travel planners is hallucinating hours, distances, costs, and availability. TravelPilot strictly separates concerns:

1. **LLM Agent (Gemini 2.5/Flash + Function Calling):**
   - Natural language comprehension & intent extraction.
   - Strategic reasoning & deciding which tools to call.
   - Selecting among validated alternatives when constraints require trade-offs.
   - Explaining plans, disruptions, and trade-offs concisely to the user.

2. **Deterministic Backend Engine (Python / FastAPI / Pydantic):**
   - Budget summation, currency validation, and category breakdowns.
   - Time arithmetic, opening hour validation, and schedule overlap detection.
   - Travel time calculations (Haversine / routing matrix).
   - Feasibility checks for alternate activities.
   - State persistence & diff calculation (before vs. after replanning).

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                              USER / CLIENT                             │
 │           (React + Vite + Tailwind CSS + Lucide Icons)                 │
 └──────────────────┬─────────────────────────────────▲───────────────────┘
                    │                                 │
            REST / WebSocket API              Streaming Events / State
                    │                                 │
 ┌──────────────────▼─────────────────────────────────┴───────────────────┐
 │                           FASTAPI BACKEND                              │
 │                                                                        │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │                         AGENT RUNTIME                            │  │
 │  │  - Prompt Orchestrator & Tool Call Loop                          │  │
 │  │  - Gemini LLM (Tool Planning & Reasoning)                       │  │
 │  │  - Agent Event Logger (Audit Trail & Timeline)                   │  │
 │  └──────────────────────────────┬───────────────────────────────────┘  │
 │                                 │ Tool Invocations                     │
 │  ┌──────────────────────────────▼───────────────────────────────────┐  │
 │  │                    DETERMINISTIC ENGINES                         │  │
 │  │  - Schedule Validator (Opening hours, slot overlaps, breaks)     │  │
 │  │  - Budget Engine (Per-day, category sums, variance alert)       │  │
 │  │  - Routing & Travel Time Engine (Distances, inter/intra-city)    │  │
 │  │  - Disruption & What-If Engine (Diff generator, replanner)       │  │
 │  └──────────────────────────────┬───────────────────────────────────┘  │
 │                                 │ Queries / State Sync                 │
 └─────────────────────────────────┼──────────────────────────────────────┘
                                   │
 ┌─────────────────────────────────▼──────────────────────────────────────┐
 │                      SUPABASE POSTGRESQL DATABASE                      │
 │                                                                        │
 │   [Reference Data]                   [Operational Trip State]          │
 │   - destinations                     - users                           │
 │   - places (attractions)             - trips                           │
 │   - hotels                           - trip_stops (ordered destinations│
 │   - restaurants                      - transport_legs (inter/intra-city│
 │   - transport_options                - itinerary_items (scheduled acts)│
 │                                      - disruptions (events & alerts)   │
 │                                      - agent_events (execution history)│
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Unified Trip Domain Model

To avoid duplicate code paths, **Single-City** and **Multi-City** trips use the **identical** underlying data model:
- A single-city trip consists of **1 `TripStop`** with start and end dates matching the trip.
- A multi-city trip consists of **N ordered `TripStop`s** connected by **N-1 `TransportLeg`s**.

```
Trip (id, user_id, title, start_date, end_date, total_budget, currency, status)
 ├── TripStop [1..N] (id, trip_id, destination_id, order_index, arrival_date, departure_date, stop_budget)
 │    ├── Destination (id, name, state, country, lat, lng, timezone, description, hero_image_url)
 │    └── ItineraryItem [0..M] (id, trip_stop_id, place_id/hotel_id/restaurant_id, day_number, start_time, end_time, cost, status, item_type)
 │
 ├── TransportLeg [0..K] (id, trip_id, origin_stop_id, destination_stop_id, mode, departure_time, arrival_time, cost, carrier, status)
 │
 ├── Disruption [0..D] (id, trip_id, type, severity, affected_item_id, description, status, resolved_at)
 │
 └── AgentEvent [0..E] (id, trip_id, event_type, tool_name, tool_input, tool_output, reasoning, created_at)
```

---

## 3. Database Schema (PostgreSQL / Supabase DDL)

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- REFERENCE ENTITIES (Destination-Agnostic Knowledge Base)
-- ============================================================================

CREATE TABLE destinations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    state_province VARCHAR(100),
    country VARCHAR(100) NOT NULL DEFAULT 'India',
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Kolkata',
    description TEXT,
    ideal_duration_days INT DEFAULT 3,
    best_season VARCHAR(100),
    average_daily_cost NUMERIC(10, 2) DEFAULT 3000.00,
    hero_image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_dest_name UNIQUE (name, country)
);

CREATE TABLE places (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    destination_id UUID NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL, -- 'historical', 'nature', 'religious', 'beach', 'shopping', 'entertainment', 'museum'
    description TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    open_time TIME NOT NULL DEFAULT '09:00:00',
    close_time TIME NOT NULL DEFAULT '18:00:00',
    closed_days INT[] DEFAULT '{}', -- 0=Sunday, 1=Monday, etc.
    entry_fee NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    foreign_entry_fee NUMERIC(10, 2) DEFAULT 0.00,
    typical_duration_minutes INT NOT NULL DEFAULT 120,
    rating NUMERIC(2, 1) DEFAULT 4.5,
    tags TEXT[] DEFAULT '{}',
    image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE hotels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    destination_id UUID NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    tier VARCHAR(50) NOT NULL, -- 'budget', 'mid-range', 'luxury', 'hostel'
    price_per_night NUMERIC(10, 2) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    address TEXT,
    rating NUMERIC(2, 1) DEFAULT 4.2,
    amenities TEXT[] DEFAULT '{}',
    image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE restaurants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    destination_id UUID NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    cuisine VARCHAR(100) NOT NULL,
    price_level VARCHAR(20) NOT NULL, -- 'budget', 'mid-range', 'fine-dining'
    average_cost_per_person NUMERIC(10, 2) NOT NULL DEFAULT 350.00,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    open_time TIME NOT NULL DEFAULT '11:00:00',
    close_time TIME NOT NULL DEFAULT '23:00:00',
    specialties TEXT[] DEFAULT '{}',
    rating NUMERIC(2, 1) DEFAULT 4.3,
    image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE transport_options (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    origin_destination_id UUID NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    dest_destination_id UUID NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    mode VARCHAR(50) NOT NULL, -- 'train', 'flight', 'bus', 'cab'
    carrier VARCHAR(100),
    code VARCHAR(50), -- e.g. Train #12728, Flight 6E-542
    typical_duration_minutes INT NOT NULL,
    estimated_cost NUMERIC(10, 2) NOT NULL,
    frequency_per_day INT DEFAULT 2,
    departure_schedules TIME[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- OPERATIONAL ENTITIES (User Trips, Itineraries, Disruptions, Agent Audit)
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE,
    full_name VARCHAR(100),
    preferences JSONB DEFAULT '{"interests": [], "budget_tier": "mid-range", "pace": "moderate"}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE trips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_budget NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    status VARCHAR(50) NOT NULL DEFAULT 'planning', -- 'planning', 'confirmed', 'in-progress', 'completed', 'disrupted'
    traveler_count INT NOT NULL DEFAULT 1,
    interests TEXT[] DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE trip_stops (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    destination_id UUID NOT NULL REFERENCES destinations(id),
    order_index INT NOT NULL,
    arrival_date DATE NOT NULL,
    departure_date DATE NOT NULL,
    stop_budget NUMERIC(10, 2) DEFAULT 0.00,
    hotel_id UUID REFERENCES hotels(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_trip_order UNIQUE (trip_id, order_index)
);

CREATE TABLE transport_legs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    origin_stop_id UUID REFERENCES trip_stops(id) ON DELETE CASCADE,
    destination_stop_id UUID REFERENCES trip_stops(id) ON DELETE CASCADE,
    mode VARCHAR(50) NOT NULL, -- 'train', 'flight', 'bus', 'cab', 'local_transit'
    carrier VARCHAR(100),
    booking_reference VARCHAR(100),
    departure_time TIMESTAMPTZ NOT NULL,
    arrival_time TIMESTAMPTZ NOT NULL,
    cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(50) NOT NULL DEFAULT 'scheduled', -- 'scheduled', 'delayed', 'cancelled', 'completed'
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE itinerary_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_stop_id UUID NOT NULL REFERENCES trip_stops(id) ON DELETE CASCADE,
    item_type VARCHAR(50) NOT NULL, -- 'place', 'restaurant', 'transport', 'custom', 'hotel_checkin', 'hotel_checkout'
    place_id UUID REFERENCES places(id) ON DELETE SET NULL,
    restaurant_id UUID REFERENCES restaurants(id) ON DELETE SET NULL,
    custom_title VARCHAR(200),
    day_number INT NOT NULL, -- 1-indexed relative to TripStop or Trip
    scheduled_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    status VARCHAR(50) NOT NULL DEFAULT 'planned', -- 'planned', 'completed', 'cancelled', 'rescheduled', 'alternative_selected'
    notes TEXT,
    is_backup BOOLEAN NOT NULL DEFAULT FALSE,
    travel_time_from_prev_minutes INT DEFAULT 0,
    travel_distance_km NUMERIC(6, 2) DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE disruptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    disruption_type VARCHAR(50) NOT NULL, -- 'flight_delayed', 'flight_cancelled', 'place_closed', 'bad_weather', 'budget_overrun', 'user_request'
    severity VARCHAR(20) NOT NULL DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
    affected_item_id UUID REFERENCES itinerary_items(id) ON DELETE SET NULL,
    affected_leg_id UUID REFERENCES transport_legs(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- 'active', 'resolving', 'resolved', 'ignored'
    suggested_action JSONB DEFAULT '{}',
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL, -- 'user_query', 'agent_thought', 'tool_call', 'tool_result', 'plan_generated', 'plan_validated', 'disruption_detected', 'replan_executed'
    tool_name VARCHAR(100),
    tool_input JSONB,
    tool_output JSONB,
    reasoning TEXT,
    duration_ms INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for high-performance lookup
CREATE INDEX idx_places_dest ON places(destination_id);
CREATE INDEX idx_hotels_dest ON hotels(destination_id);
CREATE INDEX idx_restaurants_dest ON restaurants(destination_id);
CREATE INDEX idx_itinerary_stop ON itinerary_items(trip_stop_id, day_number, start_time);
CREATE INDEX idx_trip_stops_trip ON trip_stops(trip_id, order_index);
CREATE INDEX idx_agent_events_trip ON agent_events(trip_id, created_at);
CREATE INDEX idx_disruptions_trip ON disruptions(trip_id, status);
```

---

## 4. Backend Module Architecture & Boundaries

The FastAPI backend is structured cleanly without bloated abstraction layers:

```
backend/
├── app/
│   ├── main.py                     # FastAPI entrypoint, CORS, routers
│   ├── config.py                   # Pydantic Settings (Supabase URL/Key, Gemini API Key)
│   │
│   ├── api/                        # REST Controllers
│   │   ├── routes_trips.py         # Trip CRUD, full trip summary, export
│   │   ├── routes_agent.py         # Conversational agent endpoint, execute action
│   │   ├── routes_disruptions.py   # Trigger/resolve disruptions, what-if simulations
│   │   └── routes_destinations.py  # Reference search for places, hotels, transport
│   │
│   ├── core/                       # Deterministic Logic & Algorithms
│   │   ├── budget_engine.py        # Exact budget calculation, category sums, alerts
│   │   ├── schedule_validator.py   # Time overlaps, opening hours, buffer times
│   │   ├── geo_routing.py          # Haversine distance, transit time estimation
│   │   └── diff_engine.py          # Before/After plan comparison for replanning
│   │
│   ├── agent/                      # Agentic LLM Engine
│   │   ├── orchestrator.py         # Multi-turn tool-calling loop with Gemini
│   │   ├── tools.py                # Concrete tool implementations & schemas
│   │   ├── prompts.py              # System prompts, role definitions, formatting
│   │   └── state.py                # Conversation context & session state
│   │
│   ├── db/                         # Database & Seed Management
│   │   ├── supabase_client.py      # Supabase connection & helpers
│   │   ├── seed_data.py            # Comprehensive destination seed data
│   │   └── repositories/           # Repositories for DB entities
│   │       ├── trip_repo.py
│   │       ├── destination_repo.py
│   │       ├── itinerary_repo.py
│   │       └── event_repo.py
│   │
│   └── models/                     # Pydantic Schemas (Request/Response/Domain)
│       ├── trip_models.py
│       ├── itinerary_models.py
│       ├── tool_models.py
│       ├── agent_models.py
│       └── disruption_models.py
```

---

## 5. Agent & Tool Architecture

### The ReAct / Tool-Calling Loop with Gemini

The agent executes using standard **Gemini Tool Calling** (Function Calling) over a structured set of Python backend functions.

```
User Prompt (e.g. "I have 8 days and ₹40,000. Plan Hyderabad -> Hampi -> Goa.")
       │
       ▼
[ Agent Orchestrator ] ── Sends System Prompt + Context + Available Tools to Gemini
       │
       ▼
Gemini emits `tool_call`: search_destinations(query="Hyderabad")
       │
       ▼
[ Tool Executor ] ── Executes DB / Search Lookup ──> Returns Structured JSON
       │
       ▼
[ Event Logger ] ── Records Tool Call & Result in `agent_events`
       │
       ▼
Gemini receives result, emits next tool_call: search_destinations(query="Hampi"), search_destinations(query="Goa")
       │
       ▼
Gemini calls `search_transport(origin="Hyderabad", destination="Hampi")`
       │
       ▼
Gemini drafts itinerary slots and invokes deterministic `validate_itinerary_schedule()` and `calculate_budget()`
       │
       ▼
Deterministic Engine verifies:
   - Are opening hours respected? (YES/NO)
   - Is there enough travel time between consecutive items? (YES/NO)
   - Is total cost <= ₹40,000? (YES/NO)
       │
       ▼
If validation passes:
   Agent calls `save_trip_plan()` and returns human-readable summary with breakdowns.
If validation fails:
   Deterministic error returned to Gemini: "Item Charminar closes at 17:30, slot ends at 18:30. Adjust slot or select alternative."
   Gemini adjusts dynamically.
```

### Core Agent Tools (Signatures & Responsibilities)

1. `search_destinations(query: str) -> List[DestinationSummary]`
   - Resolves any city/region dynamically from database or structured fallback.
2. `search_places(destination_id: str, categories: List[str], max_budget: float) -> List[PlaceSummary]`
   - Fetches verified attractions with opening hours, entry fees, typical durations, coordinates.
3. `search_hotels(destination_id: str, tier: str, max_price_per_night: float) -> List[HotelSummary]`
   - Returns verified accommodation options matching user budget tier.
4. `search_restaurants(destination_id: str, cuisine: Optional[str], price_level: Optional[str]) -> List[RestaurantSummary]`
   - Returns curated dining spots with price per person and coordinates.
5. `search_transport(origin_dest_id: str, target_dest_id: str, mode: Optional[str]) -> List[TransportOption]`
   - Returns inter-city options (train, flight, bus) with duration, cost, schedules.
6. `calculate_travel_time(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, mode: str) -> TravelEstimate`
   - Deterministic distance calculation (Haversine + city speed constants).
7. `validate_itinerary(items: List[ItineraryDraftItem]) -> ValidationResult`
   - Deterministic checks for time slot conflicts, venue open/closed hours, closed days, and minimum transit buffers.
8. `calculate_trip_budget(trip_id_or_draft: Union[str, TripDraft]) -> BudgetBreakdown`
   - Sums hotel costs, transport legs, entry fees, daily food estimates, and flags variance against total budget.
9. `find_alternatives(place_id: str, category: Optional[str], max_distance_km: float) -> List[PlaceSummary]`
   - Returns nearby valid alternatives when an attraction is closed, disrupted, or rejected by the user.
10. `simulate_disruption(trip_id: str, disruption_type: str, item_id: str, reason: str) -> DisruptionSimulationResult`
    - Creates a disruption record, removes/delays affected items, invokes replanning, and outputs a clear Before/After Diff.

---

## 6. Pydantic Domain & API Models

### Request & Response Schemas

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, time, datetime

# --- Tool Models ---
class DestinationSummary(BaseModel):
    id: str
    name: str
    state_province: Optional[str] = None
    country: str
    latitude: float
    longitude: float
    ideal_duration_days: int
    average_daily_cost: float
    hero_image_url: Optional[str] = None

class PlaceSummary(BaseModel):
    id: str
    destination_id: str
    name: str
    category: str
    latitude: float
    longitude: float
    open_time: str
    close_time: str
    closed_days: List[int]
    entry_fee: float
    typical_duration_minutes: int
    rating: float
    image_url: Optional[str] = None

class ValidationIssue(BaseModel):
    item_id: Optional[str] = None
    issue_type: str # 'OVERLAP', 'CLOSED_HOURS', 'CLOSED_DAY', 'INSUFFICIENT_TRANSIT', 'BUDGET_OVERRUN'
    message: str
    suggested_fix: Optional[str] = None

class ValidationResult(BaseModel):
    is_valid: bool
    issues: List[ValidationIssue] = []

class BudgetCategorySummary(BaseModel):
    accommodation: float
    intercity_transport: float
    local_transport: float
    activities_entry: float
    food_dining: float
    total_estimated: float
    budget_limit: float
    remaining_balance: float
    is_over_budget: bool

# --- Trip API Models ---
class CreateTripRequest(BaseModel):
    prompt: str = Field(..., description="Natural language prompt, e.g., '6 days in Hyderabad with ₹25,000 budget for history & food'")
    user_id: Optional[str] = None

class TripPlanResponse(BaseModel):
    trip_id: str
    title: str
    start_date: str
    end_date: str
    total_budget: float
    budget_summary: BudgetCategorySummary
    stops: List[Dict[str, Any]]
    transport_legs: List[Dict[str, Any]]
    agent_reasoning: str
    execution_timeline: List[Dict[str, Any]]

class AgentChatRequest(BaseModel):
    trip_id: str
    message: str # e.g. "Can I fit Golconda Fort into tomorrow afternoon?" or "What happens if Day 2 train is delayed?"

class AgentChatResponse(BaseModel):
    reply: str
    updated_trip: Optional[Dict[str, Any]] = None
    diff: Optional[Dict[str, Any]] = None
    agent_events: List[Dict[str, Any]] = []

class DisruptionTriggerRequest(BaseModel):
    trip_id: str
    disruption_type: str # 'flight_delayed', 'place_closed', 'budget_cut', 'custom'
    affected_item_id: Optional[str] = None
    affected_leg_id: Optional[str] = None
    details: str
```

---

## 7. Workflows & State Machines

### 1. Single-City Workflow
1. User provides prompt: *"Visit Hyderabad for 6 days with ₹25k budget. Focus: history, food, shopping."*
2. Agent resolves destination `Hyderabad`.
3. Sets up 1 `TripStop` (Days 1 to 6).
4. Selects optimal hotel within budget tier (~₹1,500 - ₹2,500/night).
5. Clusters places geographically by day (e.g. Day 1: Old City/Charminar/Chowmahalla; Day 2: Golconda & Qutb Shahi Tombs; Day 3: Ramoji Film City; Day 4: Museums & Birla Mandir; Day 5: Jubilee Hills / Hitec City dining & shopping; Day 6: Souvenirs & Laad Bazaar).
6. Deterministic engine verifies opening times, calculates local transit, and totals budget.
7. Agent stores plan and outputs structured breakdown with interactive map coordinates.

### 2. Multi-City Workflow
1. User provides prompt: *"8 days and ₹40,000. Plan Hyderabad -> Hampi -> Goa. History & beaches."*
2. Agent resolves all 3 destinations and determines day allocation (e.g., Hyderabad: 3 days, Hampi: 2 days, Goa: 3 days).
3. Queries inter-city transport legs:
   - Hyderabad to Hospet/Hampi (Overnight train or express bus).
   - Hampi to Goa (Train or private cab).
4. Creates 3 ordered `TripStop`s and 2 `TransportLeg`s.
5. Populates daily itineraries within each city stop.
6. Runs holistic budget and schedule validation across all stops + intercity legs.
7. Saves unified trip.

### 3. Disruption & Dynamic Replanning Workflow
1. User or event triggers disruption: *"Golconda Fort is closed tomorrow due to maintenance."*
2. Agent locates affected `ItineraryItem` on Day 2.
3. System calls `find_alternatives(destination_id, category='historical', max_distance=10km)`.
4. Alternative retrieved: *Qutb Shahi Tombs & Paigah Tombs*.
5. Deterministic engine checks schedule fit & travel time to next lunch reservation.
6. Generates Before/After Diff:
   - **Old:** 14:00 - 17:30 Golconda Fort (₹50)
   - **New:** 14:00 - 16:30 Qutb Shahi Tombs (₹40) + Paigah Tombs (₹25)
7. Presents visual diff and agent explanation to user with One-Click Confirmation.

### 4. "What-If" Simulation Workflow
1. User asks: *"What if I remove Goa and stay longer in Hampi?"* or *"What if my budget is cut to ₹20,000?"*
2. Backend creates an in-memory branch of the trip state.
3. Agent applies modifications and deterministic engine recalculates budget and timings.
4. Returns comparative analysis:
   - Budget saved: -₹12,500 (transport + hotel).
   - Relaxed pace: 4 days in Hampi exploring rural ruins and Anegundi.
5. User can choose to "Apply Changes" or "Discard Simulation".

---

## 8. Security, Error Handling & Reliability

1. **Deterministic Guardrails:** LLM outputs are never written directly to the database without Pydantic schema validation and business logic constraints (opening hours, positive budgets, non-overlapping timeslots).
2. **Graceful Fallbacks:** If the Gemini API experiences rate limits or latency spikes, the backend employs exponential backoff and structured algorithmic fallbacks based on indexed database records.
3. **Audit Trail (Observability):** Every step of the agent's thought process, tool execution, inputs, and outputs is persisted to `agent_events`, enabling full timeline playback in the UI.
4. **Data Isolation:** Supabase row-level security (RLS) policies and parameterized queries protect against injection and unauthorized access.
