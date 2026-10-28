import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.storage.repository import SyncRepository
from src.tradera.client import TraderaClient
from src.tradera.unlister import TraderaUnlister
from src.blocket.session import BlocketSessionManager
from src.blocket.drafter import BlocketDrafter
from src.blocket.unlister import BlocketUnlister, is_title_match
from src.facebook.session import FacebookSessionManager
from src.facebook.drafter import FacebookDrafter
from src.facebook.unlister import FacebookUnlister
from src.reconciliation.sold_checker import SoldReconciler


class MultiPlatformWatcher:
    """
    Lightweight HTTP Profile Diff Listener across Tradera, Blocket, and Facebook Marketplace.
    Monitors all three platforms for state changes (new listings, published drafts, and sales)
    using fast HTTP requests (~200-500ms) and only launches Playwright browsers when an
    actionable diff is detected on one platform that requires updating the other two.
    """

    def __init__(
        self,
        repository: Optional[SyncRepository] = None,
        tradera_client: Optional[TraderaClient] = None,
        tradera_unlister: Optional[TraderaUnlister] = None,
        blocket_unlister: Optional[BlocketUnlister] = None,
        facebook_unlister: Optional[FacebookUnlister] = None,
        reconciler: Optional[SoldReconciler] = None,
    ):
        self.repo = repository or SyncRepository()
        self.tradera_client = tradera_client or TraderaClient()
        self.tradera_unlister = tradera_unlister or TraderaUnlister()
        self.blocket_unlister = blocket_unlister or BlocketUnlister()
        self.facebook_unlister = facebook_unlister or FacebookUnlister()
        self.reconciler = reconciler or SoldReconciler(
            repository=self.repo,
            tradera_client=self.tradera_client,
            tradera_unlister=self.tradera_unlister,
            blocket_unlister=self.blocket_unlister,
            facebook_unlister=self.facebook_unlister,
        )

    def _sync_bl_published_promotions(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        """
        Checks Blocket 'ACTIVE' summary via fast HTTP API.
        If an item locally in status='drafted' is now live in Blocket 'Aktiva',
        promotes its local status to 'published'.
        """
        promoted: List[Dict[str, Any]] = []
        active_ads = self.blocket_unlister.get_active_summaries()
        if not active_ads:
            return promoted

        used_ad_ids = set()
        drafted_items = self.repo.list_items(status="drafted", platform="blocket")
        for db_item in drafted_items:
            for ad in active_ads:
                if ad["id"] in used_ad_ids:
                    continue
                if is_title_match(db_item["title"], ad["title"]):
                    used_ad_ids.add(ad["id"])
                    print(
                        f"[Diff: Blocket] Drafted item #{db_item['item_id']} ('{db_item['title']}') "
                        f"is now LIVE on Blocket (Ad #{ad['id']})!",
                        flush=True
                    )
                    if not dry_run:
                        self.repo.update_status(
                            db_item["item_id"],
                            "published",
                            blocket_ad_id=ad["id"],
                            blocket_ad_url=ad["url"],
                        )
                    promoted.append({
                        "item_id": db_item["item_id"],
                        "title": db_item["title"],
                        "blocket_ad_id": ad["id"],
                    })
                    break
        return promoted

    def _check_tradera_diff(
        self,
        auto_draft: bool = True,
        target: str = "all",
        dry_run: bool = False,
        headless: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Performs a fast HTTP diff of the Tradera seller profile against local DB state:
          1. New items on Tradera -> Ingests & cross-posts to Blocket / Facebook.
          2. Disappeared items from Tradera -> Checks if sold and unlists from Blocket & Facebook.
        """
        new_items: List[Dict[str, Any]] = []
        relisted_items: List[Dict[str, Any]] = []
        sold_items: List[Dict[str, Any]] = []

        try:
            cards = self.tradera_client.get_profile_items()
        except Exception as e:
            print(f"[Diff: Tradera] Warning fetching profile: {e}", flush=True)
            return {"new_items": [], "relisted_items": [], "sold_items": []}

        active_profile_ids = {c.item_id for c in cards}
        all_db_items = self.repo.list_items()
        known_db_ids = {it["item_id"] for it in all_db_items}
        non_sold_db = [it for it in all_db_items if it.get("status") != "sold"]

        # A. Check for brand-new or relisted item IDs on Tradera profile
        new_cards = [c for c in cards if c.item_id not in known_db_ids]
        for card in new_cards:
            try:
                detail = self.tradera_client.get_item_detail(card.url, delay_seconds=0.2)
                if detail.buy_now_price is None and card.buy_now_price is not None:
                    detail.buy_now_price = card.buy_now_price
                if detail.starting_price is None and card.starting_price is not None:
                    detail.starting_price = card.starting_price

                if dry_run:
                    print(f"[DRY-RUN][Diff: Tradera] Detected unseen listing #{detail.item_id}: '{detail.title}'", flush=True)
                    new_items.append({"item_id": detail.item_id, "title": detail.title})
                    continue

                outcome, matched_item, reason = self.repo.upsert_item_detailed(detail)
                if outcome == "new":
                    print(f"[Diff: Tradera] New listing discovered: #{detail.item_id} ('{detail.title}')", flush=True)
                    db_record = self.repo.get_item(detail.item_id)
                    if db_record:
                        new_items.append(db_record)
                elif outcome == "relisted":
                    old_id = matched_item["item_id"] if matched_item else "?"
                    print(
                        f"[Diff: Tradera] Relisted item recognized: '{detail.title}' "
                        f"(#{old_id} -> #{detail.item_id}) [{reason}]",
                        flush=True
                    )
                    relisted_items.append({"item_id": detail.item_id, "title": detail.title, "old_id": old_id})
            except Exception as e:
                print(f"[Diff: Tradera] Error inspecting card {card.url}: {e}", flush=True)

        # Cross-draft newly discovered Tradera items to Blocket and/or Facebook
        if new_items and auto_draft and not dry_run:
            if target in ("blocket", "all"):
                b_mgr = BlocketSessionManager()
                if b_mgr.has_saved_session():
                    print(f"[Diff: Tradera -> Blocket] Auto-drafting {len(new_items)} new item(s) to Blocket...", flush=True)
                    drafter = BlocketDrafter(b_mgr)
                    drafter.draft_batch(
                        new_items,
                        headless=headless,
                        delay_between=1.5,
                        on_success=lambda i_id, url, status="drafted": self.repo.update_status(i_id, status, blocket_ad_url=url),
                    )
            if target in ("facebook", "all"):
                fb_mgr = FacebookSessionManager()
                if fb_mgr.has_saved_session():
                    print(f"[Diff: Tradera -> Facebook] Auto-publishing {len(new_items)} new item(s) to Facebook...", flush=True)
                    fb_drafter = FacebookDrafter(fb_mgr)
                    fb_drafter.draft_batch(
                        new_items,
                        headless=headless,
                        delay_between=10.0,
                        publish=True,
                        on_success=lambda i_id, url, status="published": self.repo.update_facebook_status(i_id, status, facebook_ad_url=url),
                    )

        # B. Check for non-sold DB items that disappeared from the active Tradera profile
        missing_from_profile = [it for it in non_sold_db if it["item_id"] not in active_profile_ids]
        confirmed_sold_tradera: List[Dict[str, Any]] = []
        for it in missing_from_profile:
            item_url = it.get("url") or f"https://www.tradera.com/item/0/{it['item_id']}/item"
            if self.reconciler.is_item_sold_on_tradera(item_url):
                print(f"[Diff: Tradera] Item #{it['item_id']} ('{it['title']}') SOLD on Tradera!", flush=True)
                confirmed_sold_tradera.append(it)

        if confirmed_sold_tradera:
            if dry_run:
                sold_items.extend(confirmed_sold_tradera)
            else:
                titles = [it["title"] for it in confirmed_sold_tradera]
                b_res = self.blocket_unlister.unlist_items(titles, headless=headless)
                fb_res = self.facebook_unlister.unlist_items(titles, headless=headless)
                for it in confirmed_sold_tradera:
                    self.repo.mark_item_sold(it["item_id"], reason="sold_on_tradera")
                    sold_items.append({
                        "item_id": it["item_id"],
                        "title": it["title"],
                        "blocket_removed": b_res.get(it["title"], {}).get("removed", False),
                        "facebook_removed": fb_res.get(it["title"], False),
                    })

        return {
            "new_items": new_items,
            "relisted_items": relisted_items,
            "sold_items": sold_items,
        }

    def check_once(
        self,
        auto_draft: bool = True,
        target: str = "all",
        dry_run: bool = False,
        headless: bool = True,
    ) -> Dict[str, Any]:
        """
        Runs a single lightweight diff pass across all 3 platforms (Tradera, Blocket, Facebook)
        and reconciles any detected changes across the other two platforms.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] Running Multi-Platform Profile Diff Check...", flush=True)

        # 1. Tradera Profile Diff (New listings & Tradera sales -> update Blocket & Facebook)
        tradera_diff = self._check_tradera_diff(
            auto_draft=auto_draft,
            target=target,
            dry_run=dry_run,
            headless=headless,
        )

        # 2. Blocket Active Promotions (Draft -> Published status sync via HTTP JSON API)
        blocket_promoted = self._sync_bl_published_promotions(dry_run=dry_run)

        # 3. Blocket & Facebook External Sales Diff (Blocket DISPOSED / FB Sold -> update Tradera & the other platform)
        external_sales = self.reconciler.reconcile_external_sales(
            dry_run=dry_run,
            headless=headless,
        )

        browser_needed = bool(
            (tradera_diff["new_items"] and auto_draft)
            or tradera_diff["sold_items"]
            or external_sales
        )

        return {
            "timestamp": timestamp,
            "tradera_new": tradera_diff["new_items"],
            "tradera_relisted": tradera_diff["relisted_items"],
            "tradera_sold": tradera_diff["sold_items"],
            "blocket_promoted": blocket_promoted,
            "external_sales": external_sales,
            "browser_needed": browser_needed,
        }

    def watch(
        self,
        interval_seconds: int = 180,
        auto_draft: bool = True,
        target: str = "all",
        dry_run: bool = False,
        headless: bool = True,
    ) -> None:
        """
        Continuously monitors Tradera, Blocket, and Facebook Marketplace profiles at `interval_seconds`.
        Only launches Playwright when a cross-platform update is required.
        """
        print(
            f"Starting Multi-Platform Profile Diff Listener (interval={interval_seconds}s, "
            f"target={target}, auto_draft={auto_draft}, dry_run={dry_run})...",
            flush=True
        )
        print("Press Ctrl+C to stop watching.\n", flush=True)
        try:
            while True:
                self.check_once(
                    auto_draft=auto_draft,
                    target=target,
                    dry_run=dry_run,
                    headless=headless,
                )
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\nStopped Multi-Platform Profile Diff Listener.", flush=True)
