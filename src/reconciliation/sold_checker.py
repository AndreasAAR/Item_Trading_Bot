import time
import requests
from typing import List, Dict, Any, Optional

from src.storage.repository import SyncRepository
from src.tradera.client import TraderaClient
from src.tradera.unlister import TraderaUnlister
from src.blocket.unlister import BlocketUnlister, is_title_match
from src.facebook.unlister import FacebookUnlister


class SoldReconciler:
    def __init__(
        self,
        repository: Optional[SyncRepository] = None,
        tradera_client: Optional[TraderaClient] = None,
        tradera_unlister: Optional[TraderaUnlister] = None,
        blocket_unlister: Optional[BlocketUnlister] = None,
        facebook_unlister: Optional[FacebookUnlister] = None,
    ):
        self.repo = repository or SyncRepository()
        self.tradera_client = tradera_client or TraderaClient()
        self.tradera_unlister = tradera_unlister or TraderaUnlister()
        self.blocket_unlister = blocket_unlister or BlocketUnlister()
        self.facebook_unlister = facebook_unlister or FacebookUnlister()
        self.http_session = requests.Session()
        self.http_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "sv,en;q=0.9",
        })

    def is_item_sold_on_tradera(self, item_url: str) -> bool:
        """
        Fetches an item's Tradera URL and checks whether it ended with a sale.
        Returns True if item was bought (Buy Now or winning auction bidder).
        """
        try:
            resp = self.http_session.get(item_url, timeout=15)
            if resp.status_code != 200:
                return False
            text_lower = resp.text.lower()
            
            # Positive sold indicators on Tradera
            sold_signals = [
                "såld med köp nu",
                "sald med kop nu",
                "vann auktionen",
                "slutpris",
                "vinnande bud",
            ]
            return any(sig in text_lower for sig in sold_signals)
        except Exception as e:
            print(f"Error checking Tradera sold status for {item_url}: {e}", flush=True)
            return False

    def find_sold_tradera_items(self) -> List[Dict[str, Any]]:
        """
        Identifies items in our repository that are now sold on Tradera.
        Uses active profile comparison first, then verifies missing items via item URL.
        """
        # 1. Fetch currently active Tradera items from seller profile
        try:
            profile_cards = self.tradera_client.get_profile_items()
            active_tradera_ids = {c.item_id for c in profile_cards}
            print(f"Found {len(active_tradera_ids)} active listings on Tradera profile.", flush=True)
        except Exception as e:
            print(f"Warning: Failed to fetch Tradera profile items ({e}). Checking all non-sold items...", flush=True)
            active_tradera_ids = set()

        # 2. Get all non-sold items from local repository
        all_items = self.repo.list_items()
        non_sold_items = [it for it in all_items if it.get("status") != "sold"]
        print(f"Found {len(non_sold_items)} non-sold items in local database.", flush=True)

        sold_items = []
        for it in non_sold_items:
            item_id = it["item_id"]
            # If item is still active on profile, it is not sold
            if item_id in active_tradera_ids:
                continue

            # Item is not active on profile -> check item page directly
            item_url = it.get("url") or f"https://www.tradera.com/item/0/{item_id}/item"
            print(f"Checking item #{item_id} ('{it.get('title', '')}')...", flush=True)
            if self.is_item_sold_on_tradera(item_url):
                print(f"-> CONFIRMED SOLD on Tradera: #{item_id} ('{it.get('title')}')", flush=True)
                sold_items.append(it)
            else:
                print(f"-> Not sold (ended without bids or relisted): #{item_id}", flush=True)
            time.sleep(0.3)

        return sold_items

    def reconcile_sold_items(
        self,
        dry_run: bool = False,
        headless: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Forward reconciliation workflow (Tradera ➔ Blocket & Facebook):
          1. Detects all items sold on Tradera.
          2. Unlists sold items from Blocket (checking both 'Aktiva' and 'Utkast').
          3. Unlists sold items from Facebook Marketplace.
          4. Updates local DB status to 'sold'.
        """
        sold_items = self.find_sold_tradera_items()
        if not sold_items:
            print("No new sold Tradera items detected.", flush=True)
            return []

        print(f"\nProcessing {len(sold_items)} sold item(s)...", flush=True)
        results = []

        sold_titles = [it["title"] for it in sold_items]

        if dry_run:
            print("[DRY-RUN] Would unlist the following items from Blocket and Facebook:")
            for it in sold_items:
                print(f"  - #{it['item_id']}: {it['title']}")
            return sold_items

        # 1. Unlist from Blocket (both Aktiva listings and Utkast drafts)
        print("\n--- Unlisting from Blocket (Aktiva & Utkast) ---", flush=True)
        blocket_results = self.blocket_unlister.unlist_items(sold_titles, headless=headless)

        # 2. Unlist from Facebook Marketplace
        print("\n--- Unlisting from Facebook Marketplace ---", flush=True)
        fb_results = self.facebook_unlister.unlist_items(sold_titles, headless=headless)

        # 3. Update database status
        print("\n--- Updating Local Database Status ---", flush=True)
        for it in sold_items:
            item_id = it["item_id"]
            title = it["title"]
            b_info = blocket_results.get(title, {})
            fb_info = fb_results.get(title, False)

            # Mark item as sold in repo
            self.repo.update_status(item_id, "sold")
            self.repo.update_facebook_status(item_id, "sold")

            results.append({
                "item_id": item_id,
                "title": title,
                "blocket_aktiva_deleted": b_info.get("deleted_aktiva", False),
                "blocket_utkast_deleted": b_info.get("deleted_utkast", False),
                "facebook_deleted": fb_info,
            })
            print(f"Updated item #{item_id} ('{title}') to status='sold'.", flush=True)

        return results

    def reconcile_external_sales(
        self,
        dry_run: bool = False,
        headless: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Reverse reconciliation workflow (Blocket & Facebook ➔ Tradera):
          1. Scans Blocket 'Avslutade' tab for items marked as 'Såld'.
          2. Matches against non-sold database inventory.
          3. For any item found sold on Blocket that is still active on Tradera:
             - Ends the listing early on Tradera.
             - Unlists the ad on Facebook Marketplace.
             - Updates local DB status to 'sold'.
        """
        print("\nChecking for items sold on Blocket (Avslutade tab)...", flush=True)
        blocket_sold_titles = self.blocket_unlister.get_ended_sold_titles(headless=headless)
        print(f"Found {len(blocket_sold_titles)} sold item(s) in Blocket Avslutade tab.", flush=True)

        if not blocket_sold_titles:
            return []

        # Find non-sold items in DB
        all_items = self.repo.list_items()
        non_sold_db = [it for it in all_items if it.get("status") != "sold"]

        matched_sales = []
        for b_title in blocket_sold_titles:
            for it in non_sold_db:
                if is_title_match(it["title"], b_title):
                    print(f"-> Item #{it['item_id']} ('{it['title']}') was marked as SOLD on Blocket!", flush=True)
                    matched_sales.append(it)
                    break

        if not matched_sales:
            print("No active database items need reverse reconciliation.", flush=True)
            return []

        print(f"\nProcessing {len(matched_sales)} externally sold item(s)...", flush=True)
        results = []

        if dry_run:
            print("[DRY-RUN] Would end the following listings on Tradera & Facebook:")
            for it in matched_sales:
                print(f"  - #{it['item_id']}: {it['title']} (URL: {it.get('url')})")
            return matched_sales

        # 1. Unlist from Tradera
        print("\n--- Ending Listings on Tradera ---", flush=True)
        for it in matched_sales:
            item_id = it["item_id"]
            url = it.get("url") or f"https://www.tradera.com/item/0/{item_id}/item"
            t_ended = self.tradera_unlister.end_listing(
                item_url=url,
                item_id=item_id,
                title=it.get("title"),
                headless=headless
            )

            # 2. Unlist from Facebook Marketplace
            fb_ended = self.facebook_unlister.unlist_item(it["title"], headless=headless)

            # 3. Update database status
            self.repo.update_status(item_id, "sold")
            self.repo.update_facebook_status(item_id, "sold")

            results.append({
                "item_id": item_id,
                "title": it["title"],
                "tradera_ended": t_ended,
                "facebook_deleted": fb_ended,
                "source": "blocket",
            })
            print(f"Reconciled external sale for item #{item_id} ('{it['title']}') -> status='sold'.", flush=True)

        return results

    def reconcile_all(
        self,
        dry_run: bool = False,
        headless: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Bidirectional reconciliation:
          1. Tradera ➔ Blocket & Facebook
          2. Blocket & Facebook ➔ Tradera
        """
        tradera_sales = self.reconcile_sold_items(dry_run=dry_run, headless=headless)
        external_sales = self.reconcile_external_sales(dry_run=dry_run, headless=headless)
        return {
            "tradera_sales": tradera_sales,
            "external_sales": external_sales,
        }
