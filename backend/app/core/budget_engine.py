"""
TravelPilot Deterministic Budget Engine
Calculates itemized and daily trip costs across accommodation, inter-city transport,
local transit, activities, meals, and miscellaneous expenses.
"""

from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from backend.app.models.entities import (
    Trip,
    TripStop,
    TransportLeg,
    ItineraryItem,
    Hotel,
    Destination,
    ItemType,
)
from backend.app.core.models import (
    BudgetCalculationResult,
    DailyBudgetBreakdown,
)


class BudgetEngine:
    @staticmethod
    def calculate(
        total_budget: float,
        traveler_count: int = 1,
        trip_stops: Optional[List[TripStop]] = None,
        hotels_by_stop: Optional[Dict[str, Hotel]] = None,
        transport_legs: Optional[List[TransportLeg]] = None,
        itinerary_items: Optional[List[ItineraryItem]] = None,
        destinations_by_stop: Optional[Dict[str, Destination]] = None,
        daily_food_estimate_per_person: Optional[float] = None,
        daily_local_transit_estimate_per_person: float = 250.0,
        miscellaneous_cost: float = 0.0,
    ) -> BudgetCalculationResult:
        """
        Deterministically computes trip budget breakdown and variance.
        All inputs are structured Pydantic models.
        """
        traveler_count = max(1, traveler_count)
        trip_stops = trip_stops or []
        hotels_by_stop = hotels_by_stop or {}
        transport_legs = transport_legs or []
        itinerary_items = itinerary_items or []
        destinations_by_stop = destinations_by_stop or {}

        # 1. Accommodation Costs
        accommodation_total = 0.0
        stop_nights: Dict[str, int] = {}
        for stop in trip_stops:
            nights = max(1, (stop.departure_date - stop.arrival_date).days)
            stop_nights[stop.id] = nights
            hotel = hotels_by_stop.get(stop.id)
            if hotel is not None and hotel.price_per_night > 0:
                # 1 room per 2 travelers assumption
                rooms = (traveler_count + 1) // 2
                accommodation_total += hotel.price_per_night * nights * rooms

        # 2. Inter-city Transport Costs
        intercity_transport_total = 0.0
        for leg in transport_legs:
            # Leg cost per traveler
            intercity_transport_total += (leg.cost or 0.0) * traveler_count

        # 3. Activities & Itinerary Direct Costs (Entry Fees, Local Bookings, etc.)
        activities_total = 0.0
        local_transit_from_items = 0.0
        meals_from_items = 0.0

        # Group items by (trip_stop_id, day_number, scheduled_date)
        daily_activity_costs: Dict[date, float] = {}
        daily_item_transit: Dict[date, float] = {}
        daily_item_meals: Dict[date, float] = {}

        for item in itinerary_items:
            # Multiply activity / meal costs by travelers if applicable
            item_cost = (item.cost or 0.0) * traveler_count
            d = item.scheduled_date

            if item.item_type == ItemType.PLACE:
                activities_total += item_cost
                daily_activity_costs[d] = daily_activity_costs.get(d, 0.0) + item_cost
            elif item.item_type == ItemType.RESTAURANT:
                meals_from_items += item_cost
                daily_item_meals[d] = daily_item_meals.get(d, 0.0) + item_cost
            elif item.item_type == ItemType.TRANSPORT:
                local_transit_from_items += item_cost
                daily_item_transit[d] = daily_item_transit.get(d, 0.0) + item_cost
            else: # custom or other
                activities_total += item_cost
                daily_activity_costs[d] = daily_activity_costs.get(d, 0.0) + item_cost

        # 4. Meals / Food Estimates
        # If no direct restaurant items scheduled for a day, apply destination daily food estimate
        food_total = 0.0
        daily_food_allocated: Dict[date, float] = {}

        # 5. Local Transport Allocation
        local_transport_total = 0.0
        daily_local_transit_allocated: Dict[date, float] = {}

        # Generate daily breakdown calendar across all stops
        daily_breakdowns: List[DailyBudgetBreakdown] = []
        overall_day_counter = 1

        for stop in trip_stops:
            dest = destinations_by_stop.get(stop.id)
            dest_name = dest.name if dest else "Destination"
            default_food_day = (
                daily_food_estimate_per_person
                if daily_food_estimate_per_person is not None
                else (dest.average_daily_cost * 0.35 if dest else 700.0)
            )

            hotel = hotels_by_stop.get(stop.id)
            rooms = (traveler_count + 1) // 2
            daily_hotel_cost = (hotel.price_per_night * rooms) if hotel else 0.0

            # Iterate days for this stop
            current_date = stop.arrival_date
            while current_date <= stop.departure_date:
                # Food for the day: max of scheduled meal items or baseline estimate
                day_food = daily_item_meals.get(current_date, default_food_day * traveler_count)
                food_total += day_food
                daily_food_allocated[current_date] = day_food

                # Local transit for the day: item transit + baseline local transit
                day_transit = daily_item_transit.get(
                    current_date, daily_local_transit_estimate_per_person * traveler_count
                )
                local_transport_total += day_transit
                daily_local_transit_allocated[current_date] = day_transit

                day_activities = daily_activity_costs.get(current_date, 0.0)

                # Intercity leg on this day?
                day_intercity = 0.0
                for leg in transport_legs:
                    if leg.departure_time.date() == current_date:
                        day_intercity += (leg.cost or 0.0) * traveler_count

                day_total = (
                    daily_hotel_cost
                    + day_intercity
                    + day_transit
                    + day_activities
                    + day_food
                )

                daily_breakdowns.append(
                    DailyBudgetBreakdown(
                        day_number=overall_day_counter,
                        scheduled_date=current_date,
                        destination_name=dest_name,
                        accommodation_cost=round(daily_hotel_cost, 2),
                        intercity_transport_cost=round(day_intercity, 2),
                        local_transport_cost=round(day_transit, 2),
                        activities_cost=round(day_activities, 2),
                        food_cost=round(day_food, 2),
                        miscellaneous_cost=0.0,
                        total_cost=round(day_total, 2),
                    )
                )

                overall_day_counter += 1
                current_date += timedelta(days=1)

        total_cost = (
            accommodation_total
            + intercity_transport_total
            + local_transport_total
            + activities_total
            + food_total
            + miscellaneous_cost
        )

        remaining = total_budget - total_cost
        variance = total_cost - total_budget
        percentage_used = (total_cost / total_budget * 100.0) if total_budget > 0 else 0.0
        within_budget = total_cost <= total_budget

        return BudgetCalculationResult(
            accommodation=round(accommodation_total, 2),
            intercity_transport=round(intercity_transport_total, 2),
            local_transport=round(local_transport_total, 2),
            activities=round(activities_total, 2),
            food=round(food_total, 2),
            miscellaneous=round(miscellaneous_cost, 2),
            total=round(total_cost, 2),
            budget=round(total_budget, 2),
            remaining=round(remaining, 2),
            variance=round(variance, 2),
            percentage_used=round(percentage_used, 2),
            within_budget=within_budget,
            traveler_count=traveler_count,
            cost_per_traveler=round(total_cost / traveler_count, 2),
            daily_breakdowns=daily_breakdowns,
        )


budget_engine = BudgetEngine()
