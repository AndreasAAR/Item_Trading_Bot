import pytest
from unittest.mock import MagicMock, patch
from src.blocket.unlister import is_title_match, BlocketUnlister
from src.facebook.unlister import FacebookUnlister
from src.reconciliation.sold_checker import SoldReconciler


class TestTitleMatching:
    def test_exact_match(self):
        assert is_title_match("COS svart kofta, storlek M", "COS svart kofta, storlek M")

    def test_case_insensitive_match(self):
        assert is_title_match("uniqlo vit skjorta, storlek m", "UNIQLO Vit Skjorta, Storlek M")

    def test_blocket_truncated_title(self):
        # Blocket truncates long titles with '...' on my-items overview
        full_title = "ARKET svart merino pullover tröja, storlek M bra skick"
        truncated_blocket_title = "ARKET svart merino pullover tröja, storlek M br..."
        assert is_title_match(full_title, truncated_blocket_title)

    def test_different_titles_do_not_match(self):
        assert not is_title_match("IKEA HOPPVALS rullgardin 120x155 cm", "Maxi Climber träningsmaskin")

    def test_minor_punctuation_differences(self):
        assert is_title_match("Nike Pegasus Trail 5 Gore-Tex - svarta 43", "Nike Pegasus Trail 5 Gore-Tex, svarta, 43")

    def test_distinct_same_brand_titles_do_not_false_match(self):
        assert not is_title_match("Massimo Dutti navy trenchcoat, storlek M", "Massimo Dutti navy kofta, storlek M")
        assert not is_title_match("UNIQLO vit skjorta, storlek M", "Uniqlo ljusblå skjorta, storlek M")


class TestSoldReconciler:
    def test_is_item_sold_positive_cases(self):
        reconciler = SoldReconciler(
            repository=MagicMock(),
            tradera_client=MagicMock(),
            blocket_unlister=MagicMock(),
            facebook_unlister=MagicMock()
        )
        with patch.object(reconciler.http_session, "get") as mock_get:
            # 1. Buy Now sale
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = "<html><body>Annonsen är avslutad. Såld med Köp nu.</body></html>"
            assert reconciler.is_item_sold_on_tradera("https://fake.tradera.com/item/1") is True

            # 2. Winning bidder
            mock_get.return_value.text = "<html><body>Slutpris 350 kr | user123 vann auktionen</body></html>"
            assert reconciler.is_item_sold_on_tradera("https://fake.tradera.com/item/2") is True

    def test_is_item_sold_negative_cases(self):
        reconciler = SoldReconciler(
            repository=MagicMock(),
            tradera_client=MagicMock(),
            blocket_unlister=MagicMock(),
            facebook_unlister=MagicMock()
        )
        with patch.object(reconciler.http_session, "get") as mock_get:
            # Expired without bids
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = "<html><body>Auktionen avslutades utan bud.</body></html>"
            assert reconciler.is_item_sold_on_tradera("https://fake.tradera.com/item/3") is False

            # Active item
            mock_get.return_value.text = "<html><body>Ledande bud: 120 kr. Lägg bud nu.</body></html>"
            assert reconciler.is_item_sold_on_tradera("https://fake.tradera.com/item/4") is False

    def test_reconcile_sold_items_end_to_end(self):
        mock_repo = MagicMock()
        mock_tradera = MagicMock()
        mock_blocket = MagicMock()
        mock_fb = MagicMock()

        # Tradera profile has item 100
        card = MagicMock()
        card.item_id = "100"
        mock_tradera.get_profile_items.return_value = [card]

        # DB has items 100 (active) and 200 (sold on Tradera)
        mock_repo.list_items.return_value = [
            {"item_id": "100", "title": "Active item", "status": "published", "url": "http://tradera/100"},
            {"item_id": "200", "title": "Sold item", "status": "published", "url": "http://tradera/200"},
        ]

        mock_blocket.unlist_items.return_value = {
            "Sold item": {"deleted_aktiva": True, "deleted_utkast": False, "removed": True}
        }
        mock_fb.unlist_items.return_value = {"Sold item": True}

        reconciler = SoldReconciler(
            repository=mock_repo,
            tradera_client=mock_tradera,
            blocket_unlister=mock_blocket,
            facebook_unlister=mock_fb
        )

        with patch.object(reconciler, "is_item_sold_on_tradera", return_value=True):
            results = reconciler.reconcile_sold_items(dry_run=False)

        assert len(results) == 1
        assert results[0]["item_id"] == "200"
        assert results[0]["blocket_aktiva_deleted"] is True
        assert results[0]["facebook_deleted"] is True

        mock_repo.update_status.assert_called_once_with("200", "sold")
        mock_repo.update_facebook_status.assert_called_once_with("200", "sold")

    def test_reconcile_external_sales_blocket_to_tradera(self):
        mock_repo = MagicMock()
        mock_tradera_client = MagicMock()
        mock_tradera_unlister = MagicMock()
        mock_blocket = MagicMock()
        mock_fb = MagicMock()

        # Blocket Avslutade tab reports an item sold
        mock_blocket.get_ended_sold_titles.return_value = ["COS svart kofta, storlek M"]
        mock_fb.get_ended_sold_titles.return_value = []

        # Local DB has item 300 active
        mock_repo.list_items.return_value = [
            {"item_id": "300", "title": "COS svart kofta, storlek M", "status": "published", "url": "http://tradera/300"},
        ]
        mock_tradera_unlister.end_listing.return_value = True
        mock_fb.unlist_item.return_value = True

        reconciler = SoldReconciler(
            repository=mock_repo,
            tradera_client=mock_tradera_client,
            tradera_unlister=mock_tradera_unlister,
            blocket_unlister=mock_blocket,
            facebook_unlister=mock_fb
        )

        results = reconciler.reconcile_external_sales(dry_run=False)
        assert len(results) == 1
        assert results[0]["item_id"] == "300"
        assert results[0]["tradera_ended"] is True
        assert results[0]["facebook_deleted"] is True
        assert results[0]["source"] == "blocket"

        mock_tradera_unlister.end_listing.assert_called_once()
        mock_repo.mark_item_sold.assert_called_once_with("300", reason="sold_on_blocket")

    def test_reconcile_external_sales_facebook_to_tradera_and_blocket(self):
        mock_repo = MagicMock()
        mock_tradera_client = MagicMock()
        mock_tradera_unlister = MagicMock()
        mock_blocket = MagicMock()
        mock_fb = MagicMock()

        mock_blocket.get_ended_sold_titles.return_value = []
        mock_fb.get_ended_sold_titles.return_value = ["IKEA HOPPVALS rullgardin 120x155 cm"]

        mock_repo.list_items.return_value = [
            {"item_id": "400", "title": "IKEA HOPPVALS rullgardin 120x155 cm", "status": "published", "facebook_status": "published", "url": "http://tradera/400"},
        ]
        mock_tradera_unlister.end_listing.return_value = True
        mock_blocket.unlist_item.return_value = {"deleted_aktiva": True, "deleted_utkast": False, "removed": True}

        reconciler = SoldReconciler(
            repository=mock_repo,
            tradera_client=mock_tradera_client,
            tradera_unlister=mock_tradera_unlister,
            blocket_unlister=mock_blocket,
            facebook_unlister=mock_fb
        )

        results = reconciler.reconcile_external_sales(dry_run=False)
        assert len(results) == 1
        assert results[0]["item_id"] == "400"
        assert results[0]["tradera_ended"] is True
        assert results[0]["blocket_deleted"] is True
        assert results[0]["source"] == "facebook"

        mock_tradera_unlister.end_listing.assert_called_once()
        mock_blocket.unlist_item.assert_called_once_with("IKEA HOPPVALS rullgardin 120x155 cm", headless=True)
        mock_repo.mark_item_sold.assert_called_once_with("400", reason="sold_on_facebook")

    def test_multi_platform_watcher_check_once(self):
        from src.reconciliation.watcher import MultiPlatformWatcher

        mock_repo = MagicMock()
        mock_tradera_client = MagicMock()
        mock_tradera_unlister = MagicMock()
        mock_blocket = MagicMock()
        mock_fb = MagicMock()
        mock_reconciler = MagicMock()

        # Tradera profile currently has item 101 (existing)
        card101 = MagicMock()
        card101.item_id = "101"
        mock_tradera_client.get_profile_items.return_value = [card101]

        # Local DB has item 101 in 'drafted' status and item 102 that disappeared & sold on Tradera
        mock_repo.list_items.side_effect = lambda status=None, platform="blocket": (
            [{"item_id": "101", "title": "Haglöfs grön väst, storlek M", "status": "drafted"}]
            if status == "drafted"
            else [
                {"item_id": "101", "title": "Haglöfs grön väst, storlek M", "status": "drafted", "url": "http://tradera/101"},
                {"item_id": "102", "title": "Ukulele", "status": "published", "url": "http://tradera/102"},
            ]
        )

        # Item 102 is confirmed sold on Tradera
        mock_reconciler.is_item_sold_on_tradera.return_value = True
        mock_blocket.unlist_items.return_value = {"Ukulele": {"removed": True}}
        mock_fb.unlist_items.return_value = {"Ukulele": True}

        # Blocket active summaries show item 101 is now LIVE on Blocket!
        mock_blocket.get_active_summaries.return_value = [
            {"id": "27637426", "title": "Haglöfs grön väst, storlek M", "url": "https://www.blocket.se/recommerce/forsale/item/27637426"}
        ]
        mock_reconciler.reconcile_external_sales.return_value = []

        watcher = MultiPlatformWatcher(
            repository=mock_repo,
            tradera_client=mock_tradera_client,
            tradera_unlister=mock_tradera_unlister,
            blocket_unlister=mock_blocket,
            facebook_unlister=mock_fb,
            reconciler=mock_reconciler,
        )

        summary = watcher.check_once(auto_draft=False, dry_run=False)
        assert len(summary["tradera_sold"]) == 1
        assert summary["tradera_sold"][0]["item_id"] == "102"
        assert len(summary["blocket_promoted"]) == 1
        assert summary["blocket_promoted"][0]["item_id"] == "101"
        mock_repo.update_status.assert_called_once_with(
            "101",
            "published",
            blocket_ad_id="27637426",
            blocket_ad_url="https://www.blocket.se/recommerce/forsale/item/27637426",
        )
        mock_repo.mark_item_sold.assert_called_once_with("102", reason="sold_on_tradera")

    def test_tradera_unlister_notice_without_session(self):
        from src.tradera.unlister import TraderaUnlister
        mock_session_mgr = MagicMock()
        mock_session_mgr.has_saved_session.return_value = False
        unlister = TraderaUnlister(session_manager=mock_session_mgr)
        assert unlister.end_listing("http://tradera/1", "1") is False

    def test_tradera_session_manager_cookies(self, tmp_path):
        from src.tradera.session import TraderaSessionManager
        import json

        state_file = tmp_path / "tradera_auth_state.json"
        mgr = TraderaSessionManager(state_path=state_file)

        # 1. Manual cookies
        mgr.save_manual_cookies(trd_at="jwt_token_123", trd_rt="refresh_token_456")
        assert state_file.exists()
        assert mgr.has_saved_session() is True

        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        names = [c["name"] for c in data["cookies"]]
        assert "trd_at" in names
        assert "trd_rt" in names

        # 2. Cookie string
        mgr.save_cookie_string("trd_at=abc; trd_rt=xyz; other=123")
        with open(state_file, "r", encoding="utf-8") as f:
            data2 = json.load(f)
        names2 = [c["name"] for c in data2["cookies"]]
        assert set(names2) == {"trd_at", "trd_rt", "other"}

    def test_reconcile_hidden_items_end_to_end(self):
        mock_repo = MagicMock()
        mock_tradera_client = MagicMock()
        mock_tradera_unlister = MagicMock()
        mock_blocket = MagicMock()
        mock_fb = MagicMock()

        # Tradera Dolda returns item 500
        mock_tradera_unlister.get_hidden_listings.return_value = [
            {"item_id": "500", "title": "Arket wool sweater, size M"}
        ]

        # Local DB has item 500 active
        mock_repo.list_items.return_value = [
            {"item_id": "500", "title": "Arket wool sweater, size M", "status": "published", "facebook_status": "published"},
            {"item_id": "600", "title": "Uniqlo shirt", "status": "published", "facebook_status": "discovered"}
        ]
        mock_blocket.unlist_item.return_value = True
        mock_fb.unlist_item.return_value = True

        reconciler = SoldReconciler(
            repository=mock_repo,
            tradera_client=mock_tradera_client,
            tradera_unlister=mock_tradera_unlister,
            blocket_unlister=mock_blocket,
            facebook_unlister=mock_fb
        )

        results = reconciler.reconcile_hidden_items(dry_run=False)
        assert len(results) == 1
        assert results[0]["item_id"] == "500"
        assert results[0]["blocket_unlisted"] is True
        assert results[0]["facebook_unlisted"] is True
        assert results[0]["source"] == "tradera_hidden"

        mock_blocket.unlist_item.assert_called_once_with("Arket wool sweater, size M", headless=True)
        mock_fb.unlist_item.assert_called_once_with("Arket wool sweater, size M", headless=True)
        mock_repo.mark_item_sold.assert_called_once_with("500", reason="tradera_hidden_list")

    def test_prevent_restart_sold_items_in_repository(self, tmp_path):
        from src.storage.repository import SyncRepository
        from src.tradera.models import TraderaItemDetail

        db_path = tmp_path / "test_sold_guard.db"
        repo = SyncRepository(db_path=db_path)

        # 1. Create and mark item as sold
        item1 = TraderaItemDetail(
            item_id="7001",
            title="Vintage Ralph Lauren Polo",
            url="https://tradera.com/item/7001",
            description="Classic polo shirt",
            images=["1.jpg"],
            buy_now_price=300
        )
        repo.upsert_item_detailed(item1)
        repo.mark_item_sold("7001", reason="tradera_hidden")

        saved = repo.get_item("7001")
        assert saved["status"] == "sold"

        # 2. Ladder advance must be rejected
        adv = repo.advance_item_ladder("7001")
        assert adv is None

        # 3. Relist attempt with same title must be ignored and not restarted!
        item2 = TraderaItemDetail(
            item_id="8002",
            title="Vintage Ralph Lauren Polo",
            url="https://tradera.com/item/8002",
            description="Restarted polo shirt",
            images=["1.jpg"],
            buy_now_price=250
        )
        outcome, matched, reason = repo.upsert_item_detailed(item2)
        assert outcome == "ignored_sold"
        assert matched["item_id"] == "7001"
        assert reason == "item_already_sold"

        # 4. Old item still exists and is still sold
        assert repo.get_item("7001")["status"] == "sold"
        # 5. New item_id was not inserted into database
        assert repo.get_item("8002") is None


