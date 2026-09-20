"""
TravelPilot Deterministic Plan Diff Engine
Compares two versions of a trip plan (e.g., Before Disruption vs After Replanning)
and produces structured additions, removals, field-level modifications, budget delta, and summary.
"""

from typing import List, Optional, Dict, Any
from backend.app.models.entities import ItineraryItem, TransportLeg
from backend.app.core.models import (
    PlanDiffResult,
    ItemModification,
    LegModification,
    FieldChange,
)


class PlanDiffEngine:
    @staticmethod
    def compare(
        before_items: List[ItineraryItem],
        after_items: List[ItineraryItem],
        before_legs: Optional[List[TransportLeg]] = None,
        after_legs: Optional[List[TransportLeg]] = None,
        before_budget_total: float = 0.0,
        after_budget_total: float = 0.0,
    ) -> PlanDiffResult:
        """
        Deterministically compares Before vs After trip plans.
        """
        before_items = before_items or []
        after_items = after_items or []
        before_legs = before_legs or []
        after_legs = after_legs or []

        before_items_map = {item.id: item for item in before_items}
        after_items_map = {item.id: item for item in after_items}

        added_items: List[Dict[str, Any]] = []
        removed_items: List[Dict[str, Any]] = []
        modified_items: List[ItemModification] = []
        unchanged_items: List[Dict[str, Any]] = []

        before_travel_dist = sum(item.travel_distance_km or 0.0 for item in before_items)
        after_travel_dist = sum(item.travel_distance_km or 0.0 for item in after_items)

        # 1. Added & Modified Items
        for item_id, after_item in after_items_map.items():
            if item_id not in before_items_map:
                added_items.append(after_item.model_dump())
            else:
                before_item = before_items_map[item_id]
                field_changes: Dict[str, FieldChange] = {}

                # Check monitored fields
                fields_to_check = [
                    "start_time",
                    "end_time",
                    "scheduled_date",
                    "day_number",
                    "cost",
                    "status",
                    "notes",
                    "place_id",
                    "restaurant_id",
                    "custom_title",
                ]

                for f in fields_to_check:
                    b_val = getattr(before_item, f, None)
                    a_val = getattr(after_item, f, None)
                    if b_val != a_val:
                        field_changes[f] = FieldChange(before=b_val, after=a_val)

                if field_changes:
                    modified_items.append(
                        ItemModification(
                            item_id=item_id,
                            title=after_item.custom_title or before_item.custom_title,
                            field_changes=field_changes,
                        )
                    )
                else:
                    unchanged_items.append(after_item.model_dump())

        # 2. Removed Items
        for item_id, before_item in before_items_map.items():
            if item_id not in after_items_map:
                removed_items.append(before_item.model_dump())

        # 3. Transport Legs Diff
        before_legs_map = {leg.id: leg for leg in before_legs}
        after_legs_map = {leg.id: leg for leg in after_legs}

        added_legs: List[Dict[str, Any]] = []
        removed_legs: List[Dict[str, Any]] = []
        modified_legs: List[LegModification] = []

        for leg_id, after_leg in after_legs_map.items():
            if leg_id not in before_legs_map:
                added_legs.append(after_leg.model_dump())
            else:
                before_leg = before_legs_map[leg_id]
                leg_field_changes: Dict[str, FieldChange] = {}
                for f in ["departure_time", "arrival_time", "mode", "carrier", "cost", "status"]:
                    b_val = getattr(before_leg, f, None)
                    a_val = getattr(after_leg, f, None)
                    if b_val != a_val:
                        leg_field_changes[f] = FieldChange(before=b_val, after=a_val)

                if leg_field_changes:
                    modified_legs.append(
                        LegModification(leg_id=leg_id, field_changes=leg_field_changes)
                    )

        for leg_id, before_leg in before_legs_map.items():
            if leg_id not in after_legs_map:
                removed_legs.append(before_leg.model_dump())

        # 4. Budget & Distance Delta
        budget_delta = after_budget_total - before_budget_total
        distance_delta = round(after_travel_dist - before_travel_dist, 2)

        # 5. Generate Summary
        summary_parts = []
        if added_items:
            summary_parts.append(f"{len(added_items)} activity added")
        if removed_items:
            summary_parts.append(f"{len(removed_items)} activity removed")
        if modified_items:
            summary_parts.append(f"{len(modified_items)} activity modified")
        if added_legs or removed_legs or modified_legs:
            summary_parts.append("transport legs updated")
        if budget_delta != 0.0:
            if budget_delta > 0:
                summary_parts.append(f"budget increased by ₹{abs(budget_delta):,.2f}")
            else:
                summary_parts.append(f"budget decreased by ₹{abs(budget_delta):,.2f}")

        summary = ", ".join(summary_parts) if summary_parts else "No changes detected."

        return PlanDiffResult(
            added_items=added_items,
            removed_items=removed_items,
            modified_items=modified_items,
            unchanged_items=unchanged_items,
            added_legs=added_legs,
            removed_legs=removed_legs,
            modified_legs=modified_legs,
            budget_before=round(before_budget_total, 2),
            budget_after=round(after_budget_total, 2),
            budget_delta=round(budget_delta, 2),
            travel_distance_delta_km=distance_delta,
            summary=summary,
        )


diff_engine = PlanDiffEngine()
