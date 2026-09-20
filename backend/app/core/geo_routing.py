"""
TravelPilot Deterministic Geo & Routing Engine
Provides Haversine distance calculations, mode-specific transit time estimations,
spatial clustering, and 2-opt route optimization to prevent zig-zag travel.
"""

import math
from typing import List, Optional, Tuple, Dict, Any
from abc import ABC, abstractmethod

from backend.app.core.models import (
    GeoPoint,
    RoutingMode,
    TravelEstimate,
    RouteSegment,
    RouteSummary,
)

EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes exact spherical great-circle distance between two coordinates in km.
    Validates lat/lon bounds and returns 0.0 for identical coordinates.
    """
    if not (-90.0 <= lat1 <= 90.0 and -90.0 <= lat2 <= 90.0):
        raise ValueError(f"Latitude out of valid range [-90, 90]: {lat1}, {lat2}")
    if not (-180.0 <= lon1 <= 180.0 and -180.0 <= lon2 <= 180.0):
        raise ValueError(f"Longitude out of valid range [-180, 180]: {lon1}, {lon2}")

    if abs(lat1 - lat2) < 1e-9 and abs(lon1 - lon2) < 1e-9:
        return 0.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    # Clip numerical floating noise
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(EARTH_RADIUS_KM * c, 3)


# Mode parameters: (assumed_speed_kmh, detour_factor, fixed_buffer_minutes)
MODE_PARAMETERS: Dict[RoutingMode, Tuple[float, float, int]] = {
    RoutingMode.WALK: (4.5, 1.25, 3),        # 4.5 km/h, road factor 1.25, 3 min buffer
    RoutingMode.BICYCLE: (14.0, 1.25, 5),    # 14 km/h, 5 min buffer
    RoutingMode.CAR: (32.0, 1.35, 8),        # 32 km/h urban, road detour 1.35x, 8 min parking
    RoutingMode.CAB: (30.0, 1.35, 10),       # 30 km/h, 10 min pickup wait
    RoutingMode.BUS: (20.0, 1.40, 15),       # 20 km/h, stops & 15 min wait
    RoutingMode.METRO: (35.0, 1.15, 10),     # 35 km/h, station entry/exit
    RoutingMode.TRAIN: (65.0, 1.20, 30),     # 65 km/h intercity, 30 min station buffer
    RoutingMode.FLIGHT: (500.0, 1.05, 120),  # 500 km/h cruising, 120 min check-in/security/boarding
}


class BaseRoutingProvider(ABC):
    @abstractmethod
    def calculate_distance(self, origin: GeoPoint, destination: GeoPoint) -> float:
        pass

    @abstractmethod
    def estimate_travel_time(
        self, origin: GeoPoint, destination: GeoPoint, mode: RoutingMode
    ) -> TravelEstimate:
        pass


class HaversineFallbackProvider(BaseRoutingProvider):
    """
    Deterministic fallback provider using Haversine great-circle distance
    adjusted by mode-specific detour coefficients and urban overheads.
    """
    def calculate_distance(self, origin: GeoPoint, destination: GeoPoint) -> float:
        return haversine_distance(origin.latitude, origin.longitude, destination.latitude, destination.longitude)

    def estimate_travel_time(
        self, origin: GeoPoint, destination: GeoPoint, mode: RoutingMode = RoutingMode.CAB
    ) -> TravelEstimate:
        straight_dist = self.calculate_distance(origin, destination)
        speed_kmh, detour, buffer_mins = MODE_PARAMETERS.get(mode, (30.0, 1.35, 10))

        if straight_dist == 0.0:
            return TravelEstimate(
                origin=origin,
                destination=destination,
                mode=mode,
                distance_km=0.0,
                duration_minutes=0,
                is_estimate=True,
                assumed_speed_kmh=speed_kmh,
                notes="Same location",
            )

        # Apply highway speed increase for long road distances
        effective_speed = speed_kmh
        if mode in {RoutingMode.CAR, RoutingMode.CAB} and straight_dist > 40.0:
            effective_speed = 60.0

        road_dist = straight_dist * detour
        transit_hours = road_dist / effective_speed
        duration_minutes = max(3, int(math.ceil(transit_hours * 60.0 + buffer_mins)))

        return TravelEstimate(
            origin=origin,
            destination=destination,
            mode=mode,
            distance_km=round(road_dist, 2),
            duration_minutes=duration_minutes,
            is_estimate=True,
            assumed_speed_kmh=effective_speed,
            notes=f"Estimated with {mode.value} at ~{effective_speed} km/h (detour factor {detour})",
        )


class GeoRoutingEngine:
    def __init__(self, provider: Optional[BaseRoutingProvider] = None):
        self.provider: BaseRoutingProvider = provider or HaversineFallbackProvider()

    def calculate_distance(self, origin: GeoPoint, destination: GeoPoint) -> float:
        return self.provider.calculate_distance(origin, destination)

    def estimate_travel_time(
        self, origin: GeoPoint, destination: GeoPoint, mode: RoutingMode = RoutingMode.CAB
    ) -> TravelEstimate:
        return self.provider.estimate_travel_time(origin, destination, mode)

    def calculate_route(self, points: List[GeoPoint], mode: RoutingMode = RoutingMode.CAB) -> RouteSummary:
        """Computes end-to-end route distance and travel time along a sequence of points."""
        if not points:
            return RouteSummary(
                ordered_points=[],
                total_distance_km=0.0,
                total_duration_minutes=0,
                mode=mode,
                segments=[],
            )

        if len(points) == 1:
            return RouteSummary(
                ordered_points=points,
                total_distance_km=0.0,
                total_duration_minutes=0,
                mode=mode,
                segments=[],
            )

        total_distance = 0.0
        total_duration = 0
        segments: List[RouteSegment] = []

        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            est = self.estimate_travel_time(p1, p2, mode)
            total_distance += est.distance_km
            total_duration += est.duration_minutes
            segments.append(
                RouteSegment(
                    origin=p1,
                    destination=p2,
                    distance_km=est.distance_km,
                    duration_minutes=est.duration_minutes,
                    mode=mode,
                )
            )

        return RouteSummary(
            ordered_points=points,
            total_distance_km=round(total_distance, 2),
            total_duration_minutes=total_duration,
            mode=mode,
            segments=segments,
        )

    def cluster_nearby_places(self, points: List[GeoPoint], radius_km: float = 5.0) -> List[List[GeoPoint]]:
        """
        Greedy spatial clustering of geographic points within radius_km.
        Useful for assigning daily sightseeing zones without criss-crossing the city.
        """
        if not points:
            return []

        remaining = list(points)
        clusters: List[List[GeoPoint]] = []

        while remaining:
            seed = remaining.pop(0)
            cluster = [seed]
            to_remove = []

            for p in remaining:
                dist = self.calculate_distance(seed, p)
                if dist <= radius_km:
                    cluster.append(p)
                    to_remove.append(p)

            for p in to_remove:
                remaining.remove(p)

            clusters.append(cluster)

        return clusters

    def optimize_visit_order(
        self,
        points: List[GeoPoint],
        start_point: Optional[GeoPoint] = None,
        end_point: Optional[GeoPoint] = None,
    ) -> List[GeoPoint]:
        """
        Heuristic Traveling Salesperson / Tour Optimizer using Nearest Neighbour + 2-Opt local search.
        Significantly reduces zig-zag travel across a city.
        """
        if len(points) <= 2:
            result = list(points)
            if start_point and start_point in result:
                result.remove(start_point)
                result.insert(0, start_point)
            if end_point and end_point in result and len(result) > 1:
                result.remove(end_point)
                result.append(end_point)
            return result

        unvisited = list(points)
        current = start_point if (start_point and start_point in unvisited) else unvisited[0]
        unvisited.remove(current)
        route: List[GeoPoint] = [current]

        # 1. Greedy Nearest Neighbour Construction
        while unvisited:
            next_p = min(unvisited, key=lambda p: self.calculate_distance(current, p))
            unvisited.remove(next_p)
            route.append(next_p)
            current = next_p

        # If explicit end_point requested and not at end, shift to end
        if end_point and end_point in route:
            route.remove(end_point)
            route.append(end_point)

        # 2. 2-Opt Local Search Improvement
        improved = True
        iterations = 0
        max_iterations = 25

        def calculate_total_route_dist(r: List[GeoPoint]) -> float:
            return sum(self.calculate_distance(r[i], r[i + 1]) for i in range(len(r) - 1))

        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            best_dist = calculate_total_route_dist(route)

            # Start index: 1 if start_point is fixed, else 0
            start_i = 1 if start_point else 0
            end_k = len(route) - 1 if end_point else len(route)

            for i in range(start_i, end_k - 1):
                for k in range(i + 1, end_k):
                    # 2-opt swap: reverse segment between i and k
                    new_route = route[:i] + route[i:k + 1][::-1] + route[k + 1:]
                    new_dist = calculate_total_route_dist(new_route)
                    if new_dist < best_dist - 1e-4:
                        route = new_route
                        best_dist = new_dist
                        improved = True
                        break
                if improved:
                    break

        return route


geo_routing_engine = GeoRoutingEngine()
