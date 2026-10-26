import tempfile
from pathlib import Path
import pytest

from src.pricing.ladder import (
    round_to_nine,
    get_ladder_stage_info,
    calculate_ladder_price,
    get_rotated_images,
    advance_item_ladder,
    LADDER_STAGES,
)
from src.storage.repository import SyncRepository
from src.tradera.models import TraderaItemDetail

def test_round_to_nine():
    # Already ending in 9
    assert round_to_nine(249) == 249
    assert round_to_nine(99) == 99
    assert round_to_nine(59) == 59

    # Standard rounding down
    assert round_to_nine(455) == 449
    assert round_to_nine(350) == 349
    assert round_to_nine(245) == 239
    assert round_to_nine(70) == 69

    # Floats from percentage calculations
    assert round_to_nine(648.7) == 649
    assert round_to_nine(258.7) == 259
    assert round_to_nine(139.3) == 139
    assert round_to_nine(104.3) == 99

    # Hard minimum floor (default 59 kr)
    assert round_to_nine(50) == 59
    assert round_to_nine(10) == 59
    assert round_to_nine(-20) == 59

    # Custom minimum floor
    assert round_to_nine(25, min_floor=29) == 29

def test_ladder_stages_structure():
    assert len(LADDER_STAGES) == 5

    # Check multipliers
    assert LADDER_STAGES[0]["multiplier"] == 1.30
    assert LADDER_STAGES[1]["multiplier"] == 1.30
    assert LADDER_STAGES[2]["multiplier"] == 1.00
    assert LADDER_STAGES[3]["multiplier"] == 1.00
    assert LADDER_STAGES[4]["multiplier"] == 0.70

    # Check drop event flags (only S2 and S4 trigger price-reduction alerts)
    assert LADDER_STAGES[0]["is_drop_event"] is False
    assert LADDER_STAGES[1]["is_drop_event"] is False
    assert LADDER_STAGES[2]["is_drop_event"] is True
    assert LADDER_STAGES[3]["is_drop_event"] is False
    assert LADDER_STAGES[4]["is_drop_event"] is True

def test_calculate_ladder_price_full_cycle():
    base = 350  # 350 kr baseline

    # Step 0: Premium Anchor (+30% -> 455 -> 449)
    p0, s0 = calculate_ladder_price(base, step=0)
    assert p0 == 449
    assert s0["name"] == "premium"
    assert s0["is_drop_event"] is False

    # Step 1: Premium Buffer (No change -> 449)
    p1, s1 = calculate_ladder_price(base, step=1)
    assert p1 == 449
    assert s1["name"] == "premium_buffer"
    assert s1["is_drop_event"] is False

    # Step 2: Baseline Drop (Drop #1 -> 350 -> 349)
    p2, s2 = calculate_ladder_price(base, step=2)
    assert p2 == 349
    assert s2["name"] == "baseline"
    assert s2["is_drop_event"] is True

    # Step 3: Baseline Buffer (No change -> 349)
    p3, s3 = calculate_ladder_price(base, step=3)
    assert p3 == 349
    assert s3["name"] == "baseline_buffer"
    assert s3["is_drop_event"] is False

    # Step 4: Bargain Floor (-30% -> 245 -> 239)
    p4, s4 = calculate_ladder_price(base, step=4)
    assert p4 == 239
    assert s4["name"] == "bargain_floor"
    assert s4["is_drop_event"] is True

    # Step 5: Wrap around back to Step 0 (+30% -> 449)
    p5, s5 = calculate_ladder_price(base, step=5)
    assert p5 == 449
    assert s5["name"] == "premium"

def test_calculate_ladder_price_custom_floor():
    base = 350
    custom_floor = 299

    # Even at Step 4 (-30% which is 239 kr), it must not drop below custom_floor 299 kr
    p4, _ = calculate_ladder_price(base, step=4, custom_floor=custom_floor)
    assert p4 == 299

def test_get_rotated_images():
    assert get_rotated_images([]) == []

    imgs = ["img_a.jpg", "img_b.jpg", "img_c.jpg"]

    # Cover 0: [a, b, c]
    assert get_rotated_images(imgs, 0) == ["img_a.jpg", "img_b.jpg", "img_c.jpg"]

    # Cover 1: [b, c, a]
    assert get_rotated_images(imgs, 1) == ["img_b.jpg", "img_c.jpg", "img_a.jpg"]

    # Cover 2: [c, a, b]
    assert get_rotated_images(imgs, 2) == ["img_c.jpg", "img_a.jpg", "img_b.jpg"]

    # Cover 3 (wrap-around): [a, b, c]
    assert get_rotated_images(imgs, 3) == ["img_a.jpg", "img_b.jpg", "img_c.jpg"]

    # Cover 4: [b, c, a]
    assert get_rotated_images(imgs, 4) == ["img_b.jpg", "img_c.jpg", "img_a.jpg"]

def test_advance_item_ladder_function():
    item = {
        "item_id": "999",
        "base_price": 499,
        "floor_price": 349,
        "ladder_step": 0,
        "cover_image_index": 0,
        "relist_count": 0,
    }

    # Step 0 -> Step 1 (Buffer)
    adv1 = advance_item_ladder(item)
    assert adv1["ladder_step"] == 1
    assert adv1["cover_image_index"] == 1
    assert adv1["relist_count"] == 1
    assert adv1["target_price"] == 649
    assert adv1["is_drop_event"] is False

    # Step 1 -> Step 2 (Baseline Drop #1)
    item.update(adv1)
    adv2 = advance_item_ladder(item)
    assert adv2["ladder_step"] == 2
    assert adv2["cover_image_index"] == 2
    assert adv2["relist_count"] == 2
    assert adv2["target_price"] == 499
    assert adv2["is_drop_event"] is True

    # Step 2 -> Step 3 (Baseline Buffer)
    item.update(adv2)
    adv3 = advance_item_ladder(item)
    assert adv3["ladder_step"] == 3
    assert adv3["cover_image_index"] == 3
    assert adv3["relist_count"] == 3
    assert adv3["target_price"] == 499
    assert adv3["is_drop_event"] is False

    # Step 3 -> Step 4 (Bargain Floor Drop #2)
    item.update(adv3)
    adv4 = advance_item_ladder(item)
    assert adv4["ladder_step"] == 4
    assert adv4["cover_image_index"] == 4
    assert adv4["relist_count"] == 4
    assert adv4["target_price"] == 349
    assert adv4["is_drop_event"] is True

    # Step 4 -> Step 0 (Restart Ladder FOMO)
    item.update(adv4)
    adv5 = advance_item_ladder(item)
    assert adv5["ladder_step"] == 0
    assert adv5["cover_image_index"] == 5
    assert adv5["relist_count"] == 5
    assert adv5["target_price"] == 649
    assert adv5["is_drop_event"] is False

def test_sync_repository_ladder_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_ladder.db"
        repo = SyncRepository(db_path=db_path)

        detail = TraderaItemDetail(
            item_id="1001",
            title="Premium Wool Blazer",
            url="https://tradera.com/item/1001",
            description="Warm wool blazer",
            images=["1.jpg", "2.jpg", "3.jpg"],
            buy_now_price=500,
            starting_price=250,
            attributes={"Size": "50"}
        )

        outcome, matched, reason = repo.upsert_item_detailed(detail)
        assert outcome == "new"

        item = repo.get_item("1001")
        assert item is not None
        assert item["base_price"] == 500
        # Step 0 price: 500 * 1.30 = 650 -> 649 kr
        assert item["target_price"] == 649
        # Floor price: 500 * 0.70 = 350 -> 349 kr
        assert item["floor_price"] == 349
        assert item["ladder_step"] == 0
        assert item["cover_image_index"] == 0
        assert item["relist_count"] == 0

        # Advance item along ladder
        adv = repo.advance_item_ladder("1001")
        assert adv["ladder_step"] == 1
        assert adv["target_price"] == 649
        assert adv["cover_image_index"] == 1

        updated = repo.get_item("1001")
        assert updated["ladder_step"] == 1
        assert updated["cover_image_index"] == 1
        assert updated["relist_count"] == 1

        # Advance to step 2 (Drop #1)
        adv2 = repo.advance_item_ladder("1001")
        assert adv2["ladder_step"] == 2
        assert adv2["target_price"] == 499
        assert adv2["is_drop_event"] is True

        # Custom floor adjustment
        repo.set_floor_price("1001", 399)
        refetched = repo.get_item("1001")
        assert refetched["floor_price"] == 399

        # Custom base price adjustment
        repo.set_base_price("1001", 600, floor_price=419)
        refetched2 = repo.get_item("1001")
        assert refetched2["base_price"] == 600
        assert refetched2["floor_price"] == 419

        # Enriched listing
        ladder_items = repo.list_ladder_items()
        assert len(ladder_items) == 1
        enriched = ladder_items[0]
        assert enriched["item_id"] == "1001"
        assert "stage_name" in enriched
        assert "next_step" in enriched
        assert "next_price" in enriched
