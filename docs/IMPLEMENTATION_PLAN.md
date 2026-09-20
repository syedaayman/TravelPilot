# TravelPilot — Phase-by-Phase Implementation Plan

> **Structured build order for a production-grade hackathon prototype.**  
> *Follow each phase sequentially with automated tests and validation gates.*

---

## Phase 1: Foundation, Project Setup & Database Layer
- [ ] **1.1 Workspace & Virtual Environment Setup**
  - Initialize Python virtual environment with FastAPI, Uvicorn, Pydantic v2, `google-genai` / `google-generativeai`, `supabase-py`, `httpx`, `pytest`, `python-dotenv`.
  - Create standard `.env.example` with config keys (`GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `DATABASE_URL`).
- [ ] **1.2 Database Schema & Migrations**
  - Create Supabase PostgreSQL schema script in `backend/db/schema.sql` (Reference & Operational tables, foreign keys, indexes, constraints).
  - Create Supabase client wrapper in `backend/app/db/supabase_client.py` with mock/in-memory fallback mode for local testing without network blocks.
- [ ] **1.3 Rich Seed Data Generator**
  - Populate destination-agnostic reference data for key Indian destinations (Hyderabad, Hampi, Goa, Bengaluru, Jaipur, Munnar, Delhi, Varanasi).
  - Include 35+ verified attractions with real coordinates, opening/closing hours, closed days, entry fees, and categories.
  - Include verified hotels across 3 tiers (budget, mid-range, luxury).
  - Include curated restaurants with price levels and cuisines.
  - Include inter-city transport options (Vande Bharat trains, direct flights, express buses).

---

## Phase 2: Deterministic Backend Engines (Pure Python Core)
- [ ] **2.1 Budget Engine (`backend/app/core/budget_engine.py`)**
  - Calculate total estimated cost broken down into accommodation, intercity transport, local transit, entry tickets, and meals.
  - Compare against user budget limit; calculate variance, remaining surplus, or deficit alert.
- [ ] **2.2 Schedule & Conflict Validator (`backend/app/core/schedule_validator.py`)**
  - Validate that itinerary items do not have overlapping time slots.
  - Check opening and closing hours for every place and restaurant.
  - Check whether a place is scheduled on its closed day of the week (e.g. Salar Jung Museum closed on Fridays).
  - Ensure minimum transit buffers between consecutive attractions.
- [ ] **2.3 Geo & Routing Engine (`backend/app/core/geo_routing.py`)**
  - Calculate accurate Haversine distance and transit times based on urban traffic constants and transit modes.
  - Geographic clustering to prevent zig-zag travel across a city.
- [ ] **2.4 Plan Diff Engine (`backend/app/core/diff_engine.py`)**
  - Compare two itinerary versions (before disruption vs. after replanning) and produce structured item additions, removals, time shifts, and budget delta.
- [ ] **2.5 Unit Test Suite for Deterministic Core**
  - `tests/test_budget_engine.py`
  - `tests/test_schedule_validator.py`
  - `tests/test_geo_routing.py`
  - `tests/test_diff_engine.py`

---

## Phase 3: Gemini Agent & Tool Execution Architecture
- [ ] **3.1 Concrete Tool Implementations (`backend/app/agent/tools.py`)**
  - Implement and test all core tools:
    - `search_destinations(query)`
    - `search_places(destination_id, categories, max_budget)`
    - `get_place_details(place_id)`
    - `search_hotels(destination_id, tier, max_price)`
    - `search_restaurants(destination_id, cuisine, price_level)`
    - `search_transport(origin_id, dest_id, mode)`
    - `calculate_travel_time(lat1, lng1, lat2, lng2, mode)`
    - `validate_itinerary(items)`
    - `calculate_budget(trip_state)`
    - `find_alternatives(place_id, category, max_dist_km)`
- [ ] **3.2 Agent Orchestrator & Gemini ReAct Loop (`backend/app/agent/orchestrator.py`)**
  - Integrate Gemini tool-calling interface with multi-turn loop.
  - Handle tool call execution, parameter deserialization, and output feeding.
  - Maintain agent event audit log (`AgentEvent`) capturing thoughts, tool calls, and results.
- [ ] **3.3 System Prompts & Guardrails (`backend/app/agent/prompts.py`)**
  - Rigorous prompt defining the agent role: strict adherence to tool data, zero hallucination of prices/timings, deterministic verification before finalizing any plan.

---

## Phase 4: Disruption Management & What-If Simulation
- [ ] **4.1 Disruption Handler (`backend/app/core/disruption_engine.py`)**
  - Support pre-canned and dynamic disruptions:
    - Venue closure (e.g., maintenance, strike).
    - Transit delay / flight cancellation.
    - Weather alert (rain/storm closing beaches or outdoor monuments).
    - Sudden budget reduction.
  - Automated alternative search & schedule refitting.
- [ ] **4.2 "What-If" Branching Engine**
  - Fork existing trip state in-memory.
  - Execute hypothetical queries ("What if I stay 2 extra days in Hampi?", "What if I drop Goa?").
  - Return comparative metrics without altering original saved trip.

---

## Phase 5: FastAPI REST API & Integration
- [ ] **5.1 Endpoints Implementation**
  - `POST /api/trips/plan` — Create new trip from natural language prompt (Single or Multi-city).
  - `GET /api/trips/{trip_id}` — Retrieve full trip structure with stops, itinerary, transport legs, budget summary.
  - `POST /api/agent/chat` — Conversational interaction, specific time queries, on-the-fly itinerary edits.
  - `POST /api/disruptions/trigger` — Trigger disruption and generate replanned alternatives + diff.
  - `POST /api/simulations/what-if` — Run what-if simulations.
  - `GET /api/agent/events/{trip_id}` — Fetch chronological agent execution timeline for transparency.
  - `GET /api/destinations` — Search destinations & reference catalogue.
- [ ] **5.2 End-to-End API Integration Tests**
  - Test single-city planning flow (`tests/test_single_city_flow.py`).
  - Test multi-city planning flow (`tests/test_multi_city_flow.py`).
  - Test disruption & diff workflow (`tests/test_disruption_flow.py`).

---

## Phase 6: Frontend Development (React + Tailwind CSS + Lucide)
- [ ] **6.1 Frontend Setup & Design System**
  - Initialize React + Vite + Tailwind CSS + Lucide Icons.
  - Dark/Light modern theme with sleek glassmorphism, rich typography, and responsive layouts.
- [ ] **6.2 Hero & Trip Planner Input View**
  - Natural language prompt box with rich presets:
    - *"6 days in Hyderabad for ₹25,000 (History & Food)"*
    - *"8 days Hyderabad → Hampi → Goa for ₹40,000 (History & Beaches)"*
  - Advanced filters drawer (Dates, Travelers, Budget, Pace, Preferred transport).
- [ ] **6.3 Comprehensive Trip Dashboard**
  - **Overview Header:** Trip Title, Dates, Route badge (Single or Multi-City), Total Budget Progress Bar.
  - **Interactive Day-by-Day Timeline:** Cards showing activities, opening hours, cost, travel time between stops, categorized badges.
  - **Multi-City Route Stepper:** Visual inter-city transport cards (Train/Flight/Cab) connecting city stops.
  - **Interactive Budget Breakdown Widget:** Visual category charts (Accommodation, Transport, Food, Activities) and variance alert.
  - **Agent Live Reasoning & Timeline Drawer:** Collapsible stream showing tool calls, inputs, outputs, and execution duration.
- [ ] **6.4 Interactive Disruption & What-If Studio**
  - Disruption simulation panel with trigger buttons (*"Fort Closed"*, *"Flight Delayed 3h"*, *"Cut Budget by 20%"*).
  - **Before vs. After Visual Diff Modal:** Side-by-side comparison showing removed items in red, new alternatives in green, and budget delta.
  - One-click "Apply Replanned Itinerary" action.
- [ ] **6.5 Conversational Assistant Drawer**
  - Chat interface connected to `POST /api/agent/chat` for questions like:
    - *"Can I fit Golconda Fort into tomorrow afternoon?"*
    - *"Which restaurants are close to my hotel?"*
    - *"What happens if Day 2 morning is rained out?"*

---

## Phase 7: Verification, Polish & Hackathon Demo Readiness
- [ ] **7.1 E2E Demonstration Scenarios Validation**
  - Run Single-City Hyderabad 6-day scenario end-to-end.
  - Run Multi-City Hyderabad → Hampi → Goa 8-day scenario end-to-end.
  - Trigger venue closure disruption and verify automated alternative selection.
  - Run What-If simulation and verify diff generation.
- [ ] **7.2 Error Handling & Polish**
  - Loading skeletons, optimistic updates, tooltips, responsive mobile layout check.
  - Ensure zero console errors, clean logs, and quick response times.
