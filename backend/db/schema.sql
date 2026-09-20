-- ============================================================================
-- TravelPilot: Intelligent Trip Planning & Disruption Management System
-- Database Schema (PostgreSQL / Supabase Compatible)
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. REFERENCE ENTITIES (Destination-Agnostic Knowledge Base)
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
    ideal_duration_days INT DEFAULT 3 CHECK (ideal_duration_days > 0),
    best_season VARCHAR(100),
    average_daily_cost NUMERIC(10, 2) DEFAULT 3000.00 CHECK (average_daily_cost >= 0),
    hero_image_url TEXT,
    source VARCHAR(100) NOT NULL DEFAULT 'curated_static',
    last_verified_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_destination_name_country UNIQUE (name, country)
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
    closed_days INT[] DEFAULT '{}', -- 0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday
    entry_fee NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (entry_fee >= 0),
    foreign_entry_fee NUMERIC(10, 2) DEFAULT 0.00 CHECK (foreign_entry_fee >= 0),
    typical_duration_minutes INT NOT NULL DEFAULT 120 CHECK (typical_duration_minutes > 0),
    rating NUMERIC(2, 1) DEFAULT 4.5 CHECK (rating >= 1.0 AND rating <= 5.0),
    tags TEXT[] DEFAULT '{}',
    image_url TEXT,
    source VARCHAR(100) NOT NULL DEFAULT 'curated_static',
    last_verified_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE hotels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    destination_id UUID NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    tier VARCHAR(50) NOT NULL CHECK (tier IN ('budget', 'mid-range', 'luxury', 'hostel')),
    price_per_night NUMERIC(10, 2) NOT NULL CHECK (price_per_night > 0),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    address TEXT,
    rating NUMERIC(2, 1) DEFAULT 4.2 CHECK (rating >= 1.0 AND rating <= 5.0),
    amenities TEXT[] DEFAULT '{}',
    image_url TEXT,
    source VARCHAR(100) NOT NULL DEFAULT 'curated_static',
    last_verified_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE restaurants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    destination_id UUID NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    name VARCHAR(150) NOT NULL,
    cuisine VARCHAR(100) NOT NULL,
    price_level VARCHAR(20) NOT NULL CHECK (price_level IN ('budget', 'mid-range', 'fine-dining')),
    average_cost_per_person NUMERIC(10, 2) NOT NULL DEFAULT 350.00 CHECK (average_cost_per_person >= 0),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    open_time TIME NOT NULL DEFAULT '11:00:00',
    close_time TIME NOT NULL DEFAULT '23:00:00',
    specialties TEXT[] DEFAULT '{}',
    rating NUMERIC(2, 1) DEFAULT 4.3 CHECK (rating >= 1.0 AND rating <= 5.0),
    image_url TEXT,
    source VARCHAR(100) NOT NULL DEFAULT 'curated_static',
    last_verified_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE transport_options (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    origin_destination_id UUID NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    dest_destination_id UUID NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    mode VARCHAR(50) NOT NULL CHECK (mode IN ('train', 'flight', 'bus', 'cab')),
    carrier VARCHAR(100),
    code VARCHAR(50), -- e.g., '12728 / Godavari Express'
    typical_duration_minutes INT NOT NULL CHECK (typical_duration_minutes > 0),
    estimated_cost NUMERIC(10, 2) NOT NULL CHECK (estimated_cost >= 0),
    frequency_per_day INT DEFAULT 2 CHECK (frequency_per_day >= 0),
    departure_schedules TIME[] DEFAULT '{}',
    source VARCHAR(100) NOT NULL DEFAULT 'curated_static',
    last_verified_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_different_destinations CHECK (origin_destination_id != dest_destination_id)
);

-- ============================================================================
-- 2. OPERATIONAL ENTITIES (User Trips, Itineraries, Disruptions, Agent Logs)
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
    total_budget NUMERIC(10, 2) NOT NULL CHECK (total_budget >= 0),
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    status VARCHAR(50) NOT NULL DEFAULT 'planning' CHECK (status IN ('planning', 'confirmed', 'in-progress', 'completed', 'disrupted')),
    traveler_count INT NOT NULL DEFAULT 1 CHECK (traveler_count > 0),
    interests TEXT[] DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_trip_dates CHECK (end_date >= start_date)
);

-- Unified Trip Stops: 1 stop for Single-City trip, N ordered stops for Multi-City trip
CREATE TABLE trip_stops (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    destination_id UUID NOT NULL REFERENCES destinations(id),
    order_index INT NOT NULL CHECK (order_index >= 0),
    arrival_date DATE NOT NULL,
    departure_date DATE NOT NULL,
    stop_budget NUMERIC(10, 2) DEFAULT 0.00 CHECK (stop_budget >= 0),
    hotel_id UUID REFERENCES hotels(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_trip_order UNIQUE (trip_id, order_index),
    CONSTRAINT chk_stop_dates CHECK (departure_date >= arrival_date)
);

-- Inter-city transport connecting Trip Stops
CREATE TABLE transport_legs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    origin_stop_id UUID NOT NULL REFERENCES trip_stops(id) ON DELETE CASCADE,
    destination_stop_id UUID NOT NULL REFERENCES trip_stops(id) ON DELETE CASCADE,
    mode VARCHAR(50) NOT NULL CHECK (mode IN ('train', 'flight', 'bus', 'cab', 'local_transit')),
    carrier VARCHAR(100),
    booking_reference VARCHAR(100),
    departure_time TIMESTAMPTZ NOT NULL,
    arrival_time TIMESTAMPTZ NOT NULL,
    cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (cost >= 0),
    status VARCHAR(50) NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'delayed', 'cancelled', 'completed')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_leg_times CHECK (arrival_time >= departure_time)
);

-- Itinerary items scheduled within a specific TripStop
CREATE TABLE itinerary_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_stop_id UUID NOT NULL REFERENCES trip_stops(id) ON DELETE CASCADE,
    item_type VARCHAR(50) NOT NULL CHECK (item_type IN ('place', 'restaurant', 'transport', 'custom', 'hotel_checkin', 'hotel_checkout')),
    place_id UUID REFERENCES places(id) ON DELETE SET NULL,
    restaurant_id UUID REFERENCES restaurants(id) ON DELETE SET NULL,
    custom_title VARCHAR(200),
    day_number INT NOT NULL CHECK (day_number > 0),
    scheduled_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    cost NUMERIC(10, 2) NOT NULL DEFAULT 0.00 CHECK (cost >= 0),
    status VARCHAR(50) NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'completed', 'cancelled', 'rescheduled', 'alternative_selected')),
    notes TEXT,
    is_backup BOOLEAN NOT NULL DEFAULT FALSE,
    travel_time_from_prev_minutes INT DEFAULT 0 CHECK (travel_time_from_prev_minutes >= 0),
    travel_distance_km NUMERIC(6, 2) DEFAULT 0.00 CHECK (travel_distance_km >= 0),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_item_time CHECK (end_time >= start_time)
);

CREATE TABLE disruptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    disruption_type VARCHAR(50) NOT NULL CHECK (disruption_type IN ('flight_delayed', 'flight_cancelled', 'place_closed', 'bad_weather', 'budget_overrun', 'user_request', 'train_delayed')),
    severity VARCHAR(20) NOT NULL DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    affected_item_id UUID REFERENCES itinerary_items(id) ON DELETE SET NULL,
    affected_leg_id UUID REFERENCES transport_legs(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'resolving', 'resolved', 'ignored')),
    suggested_action JSONB DEFAULT '{}',
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Structured Agent Observability Log (Strictly NO private chain-of-thought)
CREATE TABLE agent_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN (
        'request_received',
        'planning_started',
        'tool_call',
        'tool_result',
        'validation',
        'decision',
        'state_update',
        'disruption_detected',
        'alternative_found',
        'replan_started',
        'replan_completed',
        'simulation_started',
        'simulation_completed',
        'error'
    )),
    tool_name VARCHAR(100),
    input_summary TEXT,
    result_summary TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'success' CHECK (status IN ('success', 'warning', 'error', 'info')),
    duration_ms INT DEFAULT 0 CHECK (duration_ms >= 0),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 3. INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX idx_places_destination ON places(destination_id);
CREATE INDEX idx_places_category ON places(category);
CREATE INDEX idx_hotels_destination ON hotels(destination_id, tier);
CREATE INDEX idx_restaurants_destination ON restaurants(destination_id);
CREATE INDEX idx_transport_origin_dest ON transport_options(origin_destination_id, dest_destination_id);
CREATE INDEX idx_trip_stops_trip ON trip_stops(trip_id, order_index);
CREATE INDEX idx_itinerary_stop_day ON itinerary_items(trip_stop_id, day_number, start_time);
CREATE INDEX idx_disruptions_trip ON disruptions(trip_id, status);
CREATE INDEX idx_agent_events_trip ON agent_events(trip_id, created_at);
