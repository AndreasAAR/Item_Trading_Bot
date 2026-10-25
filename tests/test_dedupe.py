import tempfile
from pathlib import Path
from src.storage.dedupe import (
    normalize_title,
    title_similarity,
    extract_image_signatures,
    is_same_listing,
    find_matching_existing_item
)
from src.storage.repository import SyncRepository
from src.tradera.models import TraderaItemDetail

def test_normalize_title():
    assert normalize_title("COS svart kofta, storlek M") == "cos svart kofta storlek m"
    assert normalize_title("Tiger of Sweden - Kostym (Str 50)!") == "tiger of sweden kostym str 50"
    assert normalize_title("  Sharp Mikrovågsugn  R-612  ") == "sharp mikrovågsugn r 612"

def test_title_similarity():
    # Exact normalized
    assert title_similarity("COS svart kofta, storlek M", "cos svart kofta! storlek M") == 1.0

    # Minor typo/variation
    ratio = title_similarity("COS svart kofta, storlek M", "COS svart kofta, stl M")
    assert ratio > 0.90

    # Distinct items
    diff_ratio = title_similarity(
        "ARKET svart merino pullover tröja, storlek M bra skick",
        "ARKET mörkgrå merinopullover tröja, storlek M bra skick"
    )
    assert diff_ratio < 0.91

def test_extract_image_signatures():
    imgs = [
        "https://img.tradera.net/large-fit/630/664381630_6b9bdde2.jpg",
        "https://img.tradera.net/large-fit/630/664381630_2a5a575e.jpg?v=1"
    ]
    sigs = extract_image_signatures(imgs)
    assert "664381630_6b9bdde2.jpg" in sigs
    assert "664381630_2a5a575e.jpg" in sigs

def test_is_same_listing():
    # 1. Exact normalized match
    match, reason = is_same_listing(
        "COS svart kofta, storlek M", [],
        "COS svart kofta storlek M", []
    )
    assert match is True
    assert reason == "exact_title_match"

    # 2. Shared images match
    match, reason = is_same_listing(
        "Vintage Wool Coat", ["https://img.tradera.net/large/12345_abc.jpg"],
        "Very Nice Wool Coat", ["https://img.tradera.net/large/12345_abc.jpg"]
    )
    assert match is True
    assert "shared_image_match" in reason

    # 3. Distinct items
    match, reason = is_same_listing(
        "Apple iPhone 13 Pro 128GB", [],
        "Apple iPhone 15 Pro 256GB", []
    )
    assert match is False

def test_relist_detection_and_status_preservation():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_relist.db"
        repo = SyncRepository(db_path=db_path)

        # Initial listing
        item_v1 = TraderaItemDetail(
            item_id="1001",
            title="Vintage Leather Jacket, Brown Size L",
            url="https://tradera.com/item/1001",
            description="Classic leather jacket",
            images=["https://img.tradera.net/large/img_jacket_1.jpg"],
            buy_now_price=800,
            starting_price=500
        )
        outcome, _, _ = repo.upsert_item_detailed(item_v1)
        assert outcome == "new"

        # Update its status as drafted on Blocket and published on Facebook
        repo.update_status("1001", "drafted", blocket_ad_url="https://blocket.se/recommerce/create/1234")
        repo.update_facebook_status("1001", "published", facebook_ad_url="https://facebook.com/marketplace/1234")

        # Seller relists item on Tradera with NEW item_id '2002' but same title
        item_v2 = TraderaItemDetail(
            item_id="2002",
            title="Vintage Leather Jacket, Brown Size L!",  # punctuation variation
            url="https://tradera.com/item/2002",
            description="Classic leather jacket fresh relist",
            images=["https://img.tradera.net/large/img_jacket_1.jpg"],
            buy_now_price=750,
            starting_price=450
        )

        outcome, matched, reason = repo.upsert_item_detailed(item_v2)
        assert outcome == "relisted"
        assert matched["item_id"] == "1001"

        # Verify new item_id inherited previous sync states!
        updated_item = repo.get_item("2002")
        assert updated_item is not None
        assert updated_item["status"] == "drafted"
        assert updated_item["facebook_status"] == "published"
        assert updated_item["blocket_ad_url"] == "https://blocket.se/recommerce/create/1234"
        assert updated_item["facebook_ad_url"] == "https://facebook.com/marketplace/1234"
        assert updated_item["target_price"] == 750

        # Verify old item_id 1001 was replaced
        assert repo.get_item("1001") is None
