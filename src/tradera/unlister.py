import time
import re
from typing import Optional, List, Dict, Any
from playwright.sync_api import sync_playwright, Page

from src.tradera.session import TraderaSessionManager
from config.settings import TRADERA_MY_PAGES_URL


class TraderaUnlister:
    def __init__(self, session_manager: Optional[TraderaSessionManager] = None):
        self.session_manager = session_manager or TraderaSessionManager()

    def end_listing(
        self,
        item_url: str,
        item_id: str,
        title: Optional[str] = None,
        headless: bool = True
    ) -> bool:
        """
        Ends an active listing on Tradera early (e.g. because it was sold on Blocket or Facebook).
        Prioritizes the 'Aktiva annonser' dashboard (Mer -> Avsluta annons), with fallback to item URL.
        """
        if not self.session_manager.has_saved_session():
            print(
                "[NOTICE] No saved Tradera session found. "
                "Run 'python -m src.cli tradera-login' once to enable automatic Tradera unlisting.",
                flush=True
            )
            return False

        try:
            with sync_playwright() as p:
                context = self.session_manager.get_context(p, headless=headless)
                page = context.new_page()
                res = self._end_listing_with_page(page, item_url, item_id, title=title)
                context.close()
                return res
        except Exception as e:
            print(f"Error ending listing on Tradera: {e}", flush=True)

        return False

    def _end_listing_with_page(
        self,
        page: Page,
        item_url: str,
        item_id: str,
        title: Optional[str] = None
    ) -> bool:
        """Internal helper to end a listing using an active Playwright page."""
        # 1. Primary Strategy: Check 'Aktiva annonser' (/my/listings) via 'Mer' -> 'Avsluta annons'
        try:
            if "my/listings" not in page.url:
                print(f"Navigating to Tradera Aktiva annonser ({TRADERA_MY_PAGES_URL})...", flush=True)
                page.goto(TRADERA_MY_PAGES_URL, timeout=30000, wait_until="domcontentloaded")
                time.sleep(2)

            # Tradera formats 9-digit item IDs with spaces (e.g. '756 817 913')
            clean_id = re.sub(r"\D", "", item_id)
            formatted_id = f"{clean_id[:3]} {clean_id[3:6]} {clean_id[6:]}" if len(clean_id) == 9 else clean_id

            item_elem = page.locator(f':text("{formatted_id}")').first
            if item_elem.count() == 0 and clean_id:
                item_elem = page.locator(f':text("{clean_id}")').first
            if item_elem.count() == 0 and title:
                item_elem = page.locator(f':text("{title[:30]}")').first

            if item_elem.count() > 0:
                print(f"Found item #{item_id} on Aktiva dashboard. Locating 'Mer' button...", flush=True)
                row = item_elem.locator('xpath=./ancestor::*[.//button[contains(., "Mer")]][1]')
                mer_btn = row.locator('button:has-text("Mer")').first
                if mer_btn.is_visible(timeout=2000):
                    mer_btn.click()
                    time.sleep(1)

                    avsluta_action = page.locator('text=Avsluta annons, [role="button"]:has-text("Avsluta annons"), button:has-text("Avsluta annons")').first
                    if avsluta_action.is_visible(timeout=3000):
                        print(f"Clicking 'Avsluta annons' for item #{item_id}...", flush=True)
                        avsluta_action.click()
                        time.sleep(2)

                        # Check for success toast or prompt
                        toast = page.locator('text="Annonsen är avbruten", text="avslutad"')
                        if toast.count() > 0 or not page.locator('text=Fler åtgärder').is_visible():
                            print(f"[OK] Successfully ended Tradera listing #{item_id} via Aktiva dashboard!", flush=True)
                            return True

            print(f"Item #{item_id} not ended from Aktiva dashboard; attempting direct item page...", flush=True)
        except Exception as e:
            print(f"Notice on Aktiva dashboard attempt ({e}); falling back to item page...", flush=True)

        # 2. Secondary Strategy: Direct item page (/item/...) with 'Visa alternativ' or 'Avsluta'
        try:
            print(f"Navigating to Tradera listing #{item_id}...", flush=True)
            page.goto(item_url, timeout=35000, wait_until="domcontentloaded")
            time.sleep(2)

            # Check if item is already ended or sold
            page_text = page.content().lower()
            if any(k in page_text for k in ["annonsen är avslutad", "såld med köp nu", "avslutades utan bud"]):
                print(f"Item #{item_id} is already ended on Tradera.", flush=True)
                return True

            end_btn = page.locator(
                'button:has-text("Avsluta i förtid"), '
                'a:has-text("Avsluta i förtid"), '
                'button:has-text("Avsluta annons"), '
                'button:has-text("Avsluta"), '
                'a[href*="end-early"]'
            ).first

            if not end_btn.is_visible(timeout=2000):
                # Check under 'Visa alternativ' banner at the top of the item page
                alt_menu = page.locator('text=Visa alternativ, button:has-text("Visa alternativ")').first
                if alt_menu.is_visible(timeout=2000):
                    alt_menu.click()
                    time.sleep(1)
                    end_btn = page.locator('button:has-text("Avsluta"), a:has-text("Avsluta"), li:has-text("Avsluta"), [role="menuitem"]:has-text("Avsluta")').first

            if not end_btn.is_visible(timeout=2000):
                # Check under 'Hantera' / 3-dots action menu on the listing
                manage_btn = page.locator('button:has-text("Hantera"), [aria-label*="Hantera"], button:has-text("Meny")').first
                if manage_btn.is_visible(timeout=2000):
                    manage_btn.click()
                    time.sleep(1)
                    end_btn = page.locator('button:has-text("Avsluta"), a:has-text("Avsluta")').first

            if end_btn and end_btn.is_visible(timeout=3000):
                print(f"Clicking 'Avsluta' for Tradera item #{item_id}...", flush=True)
                end_btn.click()
                time.sleep(1.5)

                confirm_btn = page.locator(
                    'button:has-text("Ja, avsluta"), '
                    'button:has-text("Bekräfta"), '
                    'button[variant="primary"]:has-text("Avsluta"), '
                    'button:has-text("Avsluta annons")'
                ).first

                if confirm_btn.is_visible(timeout=3000):
                    confirm_btn.click()
                    time.sleep(2)
                    print(f"[OK] Successfully ended Tradera listing #{item_id} in advance!", flush=True)
                    return True
                else:
                    print(f"[OK] Tradera listing #{item_id} action executed.", flush=True)
                    return True
        except Exception as e:
            print(f"Error ending listing on item page: {e}", flush=True)

        return False

    def end_listings(self, items: List[Dict[str, Any]], headless: bool = True) -> Dict[str, bool]:
        """Ends multiple active Tradera listings in sequence using a shared browser session."""
        if not self.session_manager.has_saved_session():
            print("[NOTICE] No saved Tradera session found.", flush=True)
            return {it.get("item_id"): False for it in items}

        results = {}
        with sync_playwright() as p:
            context = self.session_manager.get_context(p, headless=headless)
            page = context.new_page()
            for it in items:
                item_id = it.get("item_id")
                url = it.get("url") or f"https://www.tradera.com/item/0/{item_id}/item"
                title = it.get("title")
                res = self._end_listing_with_page(page, item_url=url, item_id=item_id, title=title)
                results[item_id] = res
                time.sleep(1)
            context.close()
        return results

