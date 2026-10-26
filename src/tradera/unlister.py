import time
import re
from typing import Optional, List, Dict, Any
from playwright.sync_api import sync_playwright, Page

from src.tradera.session import TraderaSessionManager
from config.settings import TRADERA_MY_PAGES_URL


class TraderaUnlister:
    def __init__(self, session_manager: Optional[TraderaSessionManager] = None):
        self.session_manager = session_manager or TraderaSessionManager()

    def end_listing(self, item_url: str, item_id: str, headless: bool = True) -> bool:
        """
        Ends an active listing on Tradera early (e.g. because it was sold on Blocket or Facebook).
        Requires an authenticated Tradera session ('python -m src.cli tradera-login').
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

                print(f"Navigating to Tradera listing #{item_id}...", flush=True)
                page.goto(item_url, timeout=35000, wait_until="domcontentloaded")
                time.sleep(2)

                # Check if item is already ended or sold
                page_text = page.content().lower()
                if any(k in page_text for k in ["annonsen är avslutad", "såld med köp nu", "avslutades utan bud"]):
                    print(f"Item #{item_id} is already ended on Tradera.", flush=True)
                    context.close()
                    return True

                # Look for seller action controls on item page
                # In Tradera, sellers see 'Hantera annons', 'Avsluta i förtid', or 'Avsluta annons'
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

                # Fallback: Navigate to seller dashboard (Mina Tradera -> Säljer)
                if not end_btn.is_visible(timeout=2000):
                    print("Checking Tradera seller dashboard for listing controls...", flush=True)
                    page.goto(TRADERA_MY_PAGES_URL, timeout=35000)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(2)

                    # Search for card with item ID or title
                    item_card = page.locator(f':text("{item_id}")').first
                    if item_card.count() > 0:
                        container = item_card.locator("xpath=./ancestor::*[.//button or .//a][last()-1]")
                        end_btn = container.locator('button:has-text("Avsluta"), a:has-text("Avsluta"), button[aria-label*="Avsluta"]').first

                if end_btn and end_btn.is_visible(timeout=3000):
                    print(f"Clicking 'Avsluta' for Tradera item #{item_id}...", flush=True)
                    end_btn.click()
                    time.sleep(1.5)

                    # Confirmation modal/prompt
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
                        context.close()
                        return True
                    else:
                        print("Confirmation button not found in modal.", flush=True)
                else:
                    print(f"Could not find 'Avsluta' control for item #{item_id} (verify Tradera login).", flush=True)

                context.close()
        except Exception as e:
            print(f"Error ending listing on Tradera: {e}", flush=True)

        return False

    def end_listings(self, items: List[Dict[str, Any]], headless: bool = True) -> Dict[str, bool]:
        """Ends multiple active Tradera listings in sequence."""
        results = {}
        for it in items:
            item_id = it.get("item_id")
            url = it.get("url") or f"https://www.tradera.com/item/0/{item_id}/item"
            res = self.end_listing(item_url=url, item_id=item_id, headless=headless)
            results[item_id] = res
            time.sleep(1)
        return results
