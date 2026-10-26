import math
from typing import List, Dict, Any, Tuple, Optional

# The 5-Phase Full-Spectrum Pricing Ladder
# Stage 0: Premium Anchor (+30%)
# Stage 1: Premium Buffer (No change - zero spam)
# Stage 2: Baseline Drop (Drop #1 - triggers Prissänkt push alert)
# Stage 3: Baseline Buffer (No change - zero spam)
# Stage 4: Bargain Floor (Drop #2 - triggers clearance Prissänkt alert)
# (Wraps back to Stage 0 on next relist to restart the FOMO cycle)

LADDER_STAGES = [
    {
        "step": 0,
        "name": "premium",
        "multiplier": 1.30,
        "is_drop_event": False,
        "description": "Premium Anchor (+30%)"
    },
    {
        "step": 1,
        "name": "premium_buffer",
        "multiplier": 1.30,
        "is_drop_event": False,
        "description": "Premium Buffer (No change - 0% spam)"
    },
    {
        "step": 2,
        "name": "baseline",
        "multiplier": 1.00,
        "is_drop_event": True,
        "description": "Baseline Drop (Drop #1 - Prissänkt alert)"
    },
    {
        "step": 3,
        "name": "baseline_buffer",
        "multiplier": 1.00,
        "is_drop_event": False,
        "description": "Baseline Buffer (No change - 0% spam)"
    },
    {
        "step": 4,
        "name": "bargain_floor",
        "multiplier": 0.70,
        "is_drop_event": True,
        "description": "Bargain Floor (-30% Drop #2 - Prissänkt alert)"
    },
]

def round_to_nine(val: float, min_floor: int = 59) -> int:
    """
    Rounds a price down to the nearest integer ending in 9.
    E.g. 455 -> 449, 350 -> 349, 245 -> 239, 139.3 -> 139, 70 -> 69.
    Enforces a hard minimum floor (default 59 kr) so items are never given away.
    """
    p = int(round(val))
    if p < min_floor:
        return min_floor

    remainder = p % 10
    if remainder == 9:
        res = p
    else:
        # Step down to previous multiple of 10 minus 1
        res = (p // 10) * 10 - 1

    return max(res, min_floor)

def get_ladder_stage_info(step: int) -> Dict[str, Any]:
    """Returns stage metadata for a given ladder step (0 to 4)."""
    normalized_step = step % len(LADDER_STAGES)
    return LADDER_STAGES[normalized_step]

def calculate_ladder_price(
    base_price: int,
    step: int,
    custom_floor: Optional[int] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    Calculates the target price for an item at a specific ladder step.
    Returns (price, stage_info).
    Guarantees price never falls below custom_floor (or 70% floor).
    """
    stage = get_ladder_stage_info(step)
    mult = stage["multiplier"]
    raw_target = base_price * mult

    # Floor boundary
    calculated_floor = round_to_nine(base_price * 0.70)
    effective_floor = custom_floor if custom_floor is not None else calculated_floor

    price = round_to_nine(raw_target)
    price = max(price, effective_floor)

    return price, stage

def get_rotated_images(images: List[str], cover_image_index: int = 0) -> List[str]:
    """
    Returns the list of image paths/URLs rotated so that images[cover_image_index]
    is the primary cover photo, without altering the canonical database records.
    """
    if not images:
        return []
    idx = cover_image_index % len(images)
    return images[idx:] + images[:idx]

def advance_item_ladder(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes the next ladder transition for an item:
    - Increments ladder_step (mod 5)
    - Increments cover_image_index
    - Increments relist_count
    - Calculates the new target price
    Returns a dictionary of updated fields ready for database persistence.
    """
    base_price = item.get("base_price") or item.get("target_price") or 100
    custom_floor = item.get("floor_price")
    curr_step = item.get("ladder_step", 0)
    curr_cover = item.get("cover_image_index", 0)
    curr_relist = item.get("relist_count", 0)

    next_step = (curr_step + 1) % len(LADDER_STAGES)
    next_cover = curr_cover + 1
    next_relist = curr_relist + 1

    new_price, stage = calculate_ladder_price(base_price, next_step, custom_floor)

    return {
        "item_id": item.get("item_id"),
        "base_price": base_price,
        "floor_price": custom_floor or round_to_nine(base_price * 0.70),
        "ladder_step": next_step,
        "stage_name": stage["name"],
        "stage_desc": stage["description"],
        "is_drop_event": stage["is_drop_event"],
        "target_price": new_price,
        "cover_image_index": next_cover,
        "relist_count": next_relist,
    }
