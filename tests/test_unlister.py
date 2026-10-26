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
