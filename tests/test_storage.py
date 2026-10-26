import tempfile
from pathlib import Path
from src.storage.repository import SyncRepository
from src.tradera.models import TraderaItemDetail

def test_sync_repository_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_sync.db"
        repo = SyncRepository(db_path=db_path)

        item = TraderaItemDetail(
            item_id="12345",
            title="Sample Jacket",
            url="https://tradera.com/item/1/12345/sample",
            description="Warm winter jacket",
            images=["https://img.tradera.net/large-fit/1.jpg"],
            buy_now_price=450,
            starting_price=200,
            attributes={"Size": "L", "Brand": "Peak Performance"}
        )

        is_new = repo.upsert_item(item)
        assert is_new is True

        # Check retrieval
        saved = repo.get_item("12345")
        assert saved is not None
        assert saved["title"] == "Sample Jacket"
        assert saved["base_price"] == 450
        assert saved["target_price"] == 579  # Step 0 anchor (+30%): 450 * 1.30 = 585 -> 579
        assert saved["status"] == "discovered"
        assert len(saved["images"]) == 1

        # Check status update
        repo.update_status("12345", "drafted", blocket_ad_url="https://blocket.se/annons/999")
        updated = repo.get_item("12345")
        assert updated["status"] == "drafted"
        assert updated["blocket_ad_url"] == "https://blocket.se/annons/999"

        # Update again with upsert - status should NOT revert to discovered
        repo.upsert_item(item)
        rechecked = repo.get_item("12345")
        assert rechecked["status"] == "drafted"
