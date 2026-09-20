"""
Unit Tests for Deterministic Geo & Routing Engine
Covers all 9 required test scenarios with strongly typed assertions.
"""

import pytest
from backend.app.core.geo_routing import (
    haversine_distance,
    geo_routing_engine,
    GeoPoint,
    RoutingMode,
)


@pytest.fixture
def charminar():
    return GeoPoint(id="p1", name="Charminar", latitude=17.3616, longitude=78.4747)


@pytest.fixture
def golconda():
    return GeoPoint(id="p2", name="Golconda Fort", latitude=17.3833, longitude=78.4011)


@pytest.fixture
def salar_jung():
    return GeoPoint(id="p3", name="Salar Jung Museum", latitude=17.3713, longitude=78.4804)


@pytest.fixture
def hampi_bazaar():
    return GeoPoint(id="p4", name="Hampi Bazaar", latitude=15.3350, longitude=76.4600)


# 1. Known Coordinate Distance
def test_known_coordinate_distance(charminar: GeoPoint, golconda: GeoPoint):
    # Charminar to Golconda Fort is ~8.1 km straight-line distance
    dist = haversine_distance(charminar.latitude, charminar.longitude, golconda.latitude, golconda.longitude)
    assert 7.8 <= dist <= 8.5
    engine_dist = geo_routing_engine.calculate_distance(charminar, golconda)
    assert engine_dist == dist


# 2. Same-Coordinate Distance = 0
def test_same_coordinate_distance_zero(charminar: GeoPoint):
    dist = haversine_distance(charminar.latitude, charminar.longitude, charminar.latitude, charminar.longitude)
    assert dist == 0.0
    engine_dist = geo_routing_engine.calculate_distance(charminar, charminar)
    assert engine_dist == 0.0


# 3. Invalid Coordinates Validation
def test_invalid_coordinates_raises():
    with pytest.raises(ValueError):
        haversine_distance(95.0, 78.0, 17.0, 78.0) # Lat > 90

    with pytest.raises(ValueError):
        haversine_distance(17.0, -190.0, 17.0, 78.0) # Lon < -180


# 4. Different Transport Modes Comparison
def test_different_transport_modes(charminar: GeoPoint, golconda: GeoPoint):
    walk_est = geo_routing_engine.estimate_travel_time(charminar, golconda, mode=RoutingMode.WALK)
    car_est = geo_routing_engine.estimate_travel_time(charminar, golconda, mode=RoutingMode.CAR)
    flight_est = geo_routing_engine.estimate_travel_time(charminar, golconda, mode=RoutingMode.FLIGHT)

    # Walking takes much longer than car
    assert walk_est.duration_minutes > car_est.duration_minutes
    assert walk_est.mode == RoutingMode.WALK
    assert car_est.mode == RoutingMode.CAR
    # Flight includes check-in buffer
    assert flight_est.duration_minutes >= 120


# 5. Travel-Time Calculation Integrity
def test_travel_time_calculation(charminar: GeoPoint, salar_jung: GeoPoint):
    # Charminar to Salar Jung is ~1.2 km straight-line
    est = geo_routing_engine.estimate_travel_time(charminar, salar_jung, mode=RoutingMode.CAB)
    assert est.distance_km > 1.0
    assert est.duration_minutes > 0
    assert est.is_estimate is True
    assert "Cab" in est.notes or "cab" in est.notes


# 6. Nearby Clustering
def test_nearby_clustering(charminar: GeoPoint, salar_jung: GeoPoint, golconda: GeoPoint, hampi_bazaar: GeoPoint):
    # Charminar & Salar Jung are ~1.2km apart (Cluster 1)
    # Golconda is ~8km away (Cluster 2 if radius = 3km)
    # Hampi is ~300km away (Cluster 3)
    points = [charminar, salar_jung, golconda, hampi_bazaar]
    clusters = geo_routing_engine.cluster_nearby_places(points, radius_km=3.0)

    # Should form 3 clusters: [Charminar, Salar Jung], [Golconda], [Hampi]
    assert len(clusters) == 3
    # Check that Charminar and Salar Jung are grouped together
    old_city_cluster = next((c for c in clusters if charminar in c), None)
    assert old_city_cluster is not None
    assert salar_jung in old_city_cluster


# 7. Route Ordering (Optimization Heuristic)
def test_route_ordering_reduces_zigzag(charminar: GeoPoint, salar_jung: GeoPoint, golconda: GeoPoint):
    # Sub-optimal ordering: Old City -> Golconda (8km) -> Old City (8km) = 16km
    zigzag_points = [charminar, golconda, salar_jung]
    unoptimized_route = geo_routing_engine.calculate_route(zigzag_points, mode=RoutingMode.CAR)

    optimized_points = geo_routing_engine.optimize_visit_order(zigzag_points, start_point=charminar)
    optimized_route = geo_routing_engine.calculate_route(optimized_points, mode=RoutingMode.CAR)

    # Optimized route (Charminar -> Salar Jung -> Golconda) must have less or equal distance
    assert optimized_route.total_distance_km <= unoptimized_route.total_distance_km
    assert optimized_points[0] == charminar
    assert optimized_points[1] == salar_jung
    assert optimized_points[2] == golconda


# 8. Empty Route
def test_empty_route():
    summary = geo_routing_engine.calculate_route([])
    assert summary.total_distance_km == 0.0
    assert summary.total_duration_minutes == 0
    assert len(summary.segments) == 0


# 9. Single-Point Route
def test_single_point_route(charminar: GeoPoint):
    summary = geo_routing_engine.calculate_route([charminar])
    assert summary.total_distance_km == 0.0
    assert summary.total_duration_minutes == 0
    assert len(summary.segments) == 0
    assert len(summary.ordered_points) == 1
