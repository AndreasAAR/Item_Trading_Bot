import time
import re
from difflib import SequenceMatcher
from typing import Optional, List, Dict, Any
from playwright.sync_api import sync_playwright, Page, BrowserContext

from src.blocket.session import BlocketSessionManager
from src.storage.dedupe import normalize_title


def is_title_match(target_title: str, candidate_title: str, threshold: float = 0.82) -> bool:
    """
    Checks if a target title matches a candidate title from Blocket,
    taking into account Blocket's truncation (ending in '...') and normalization.
    """
    t_clean = normalize_title(target_title)
    c_clean = normalize_title(candidate_title.rstrip(".").strip())

    # Exact or prefix match
    if t_clean == c_clean:
        return True
    if len(c_clean) >= 12 and t_clean.startswith(c_clean):
        return True
    if len(t_clean) >= 12 and c_clean.startswith(t_clean):
        return True

    # Fuzzy match
    ratio = SequenceMatcher(None, t_clean, c_clean).ratio()
    return ratio >= threshold


class BlocketUnlister:
    def __init__(self, session_manager: Optional[BlocketSessionManager] = None):
        self.session_manager = session_manager or BlocketSessionManager()

    def _delete_card_from_container(self, page: Page, container) -> bool:
        """
        Clicks the 3-dots menu on a card container, selects 'Ta bort',
        and confirms deletion in the Blocket modal.
        """
        try:
            # 1. Click 3-dots menu button
            dots_btn = container.locator(
                'w-button:has(w-icon[name="Dots"]), w-button[aria-label*="Meny"], w-button:has-text("Meny")'
            ).first
            if not dots_btn.is_visible(timeout=3000):
                # Fallback to any button with Dots icon inside container
                dots_btn = container.locator('w-button, button').filter(has=page.locator('w-icon[name="Dots"]')).first
            
            dots_btn.scroll_into_view_if_needed()
            time.sleep(0.3)
            dots_btn.click()
            time.sleep(0.6)

            # 2. Click 'Ta bort' in the opened dropdown menu
            # Scope to container or dropdown menu
            del_link = container.locator('a[title="Ta bort"], a:has-text("Ta bort")').first
            if not del_link.is_visible(timeout=2000):
                # Search on page level if dropdown rendered in portal
                del_link = page.locator('a[title="Ta bort"], a:has-text("Ta bort")').first
            
            del_link.click()
            time.sleep(0.8)

            # 3. Confirm in modal
            confirm_btn = page.locator('w-modal w-button:has-text("Ta bort"), div[role="dialog"] button:has-text("Ta bort"), w-button[variant="primary"]:has-text("Ta bort")').first
            if confirm_btn.is_visible(timeout=3000):
                confirm_btn.click()
                time.sleep(1.5)
                return True
            else:
                # Fallback confirm button search
                modal_btns = page.locator('button, w-button').filter(has_text=re.compile(r"^Ta bort$", re.I))
                if modal_btns.count() > 0:
                    modal_btns.last.click()
                    time.sleep(1.5)
                    return True

        except Exception as e:
            print(f"Error during card deletion: {e}", flush=True)

        return False

    def unlist_items(self, target_titles: List[str], headless: bool = True) -> Dict[str, Dict[str, bool]]:
        """
        Unlists specified titles from Blocket by checking BOTH:
          1. 'Aktiva' tab (live listings)
          2. 'Utkast' tab (saved drafts)
        
        Returns a dictionary mapping each title to its deletion status:
          { title: {"deleted_aktiva": bool, "deleted_utkast": bool, "removed": bool} }
        """
        results: Dict[str, Dict[str, bool]] = {
            t: {"deleted_aktiva": False, "deleted_utkast": False, "removed": False}
            for t in target_titles
        }

        if not target_titles:
            return results

        with sync_playwright() as p:
            context = self.session_manager.get_context(p, headless=headless)
            page = context.new_page()

            print("Navigating to Blocket My Items...", flush=True)
            page.goto("https://www.blocket.se/my-items", timeout=45000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2)

            # Dismiss cookie banner if present
            try:
                cookie_btn = page.locator('button:has-text("Acceptera"), button:has-text("Godkänn alla")')
                if cookie_btn.first.is_visible(timeout=2000):
                    cookie_btn.first.click()
                    time.sleep(0.5)
            except Exception:
                pass

            # ==========================================
            # PHASE 1: Check and Unlist from 'Aktiva' tab
            # ==========================================
            aktiva_label = page.locator("label").filter(has_text="Aktiva").first
            if aktiva_label.is_visible(timeout=3000):
                try:
                    aktiva_label.click()
                    time.sleep(1.5)
                except Exception:
                    pass

                print(f"Checking 'Aktiva' tab for {len(target_titles)} target item(s)...", flush=True)
                for title in target_titles:
                    try:
                        # Find all card headings on the page
                        headings = page.locator("h2, h3").all()
                        for h in headings:
                            text = h.inner_text().strip()
                            if is_title_match(title, text):
                                print(f"Found active listing matching '{title}': '{text}'", flush=True)
                                container = h.locator("xpath=./ancestor::*[.//w-button or .//button][last()-1]")
                                if self._delete_card_from_container(page, container):
                                    print(f"Successfully deleted active listing '{title}' from Blocket Aktiva!", flush=True)
                                    results[title]["deleted_aktiva"] = True
                                    results[title]["removed"] = True
                                    time.sleep(1)
                                break
                    except Exception as e:
                        print(f"Error checking active listings for '{title}': {e}", flush=True)

            # ==========================================
            # PHASE 2: Check and Unlist from 'Utkast' tab
            # ==========================================
            utkast_label = page.locator("label").filter(has_text="Utkast").first
            if utkast_label.is_visible(timeout=3000):
                try:
                    utkast_label.click()
                    time.sleep(1.5)
                    print(f"Checking 'Utkast' tab for target item(s)...", flush=True)

                    for title in target_titles:
                        try:
                            headings = page.locator("h2, h3").all()
                            for h in headings:
                                text = h.inner_text().strip()
                                if is_title_match(title, text):
                                    print(f"Found draft matching '{title}': '{text}'", flush=True)
                                    container = h.locator("xpath=./ancestor::*[.//w-button or .//button][last()-1]")
                                    if self._delete_card_from_container(page, container):
                                        print(f"Successfully deleted draft '{title}' from Blocket Utkast!", flush=True)
                                        results[title]["deleted_utkast"] = True
                                        results[title]["removed"] = True
                                        time.sleep(1)
                                    break
                        except Exception as e:
                            print(f"Error checking drafts for '{title}': {e}", flush=True)

                except Exception as e:
                    print(f"Notice: could not open Utkast tab ({e})", flush=True)

            context.close()

        return results

    def unlist_item(self, title: str, headless: bool = True) -> Dict[str, bool]:
        """Convenience method to unlist a single item by title."""
        res = self.unlist_items([title], headless=headless)
        return res.get(title, {"deleted_aktiva": False, "deleted_utkast": False, "removed": False})

    def get_ended_sold_titles(self, headless: bool = True) -> List[str]:
        """
        Navigates to Blocket 'Avslutade' tab and returns titles of ads marked as 'Såld'.
        """
        sold_titles: List[str] = []
        try:
            with sync_playwright() as p:
                context = self.session_manager.get_context(p, headless=headless)
                page = context.new_page()
                page.goto("https://www.blocket.se/my-items", timeout=45000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(2)

                avslutade = page.locator("label").filter(has_text="Avslutade").first
                if avslutade.is_visible(timeout=4000):
                    avslutade.click()
                    time.sleep(2)
                    cards_data = page.evaluate("""() => {
                        const titles = [];
                        document.querySelectorAll('h2, h3').forEach(h => {
                            const t = h.innerText.trim();
                            if (t.length > 3 && !t.includes('Mina annonser')) {
                                const container = h.closest('article') || h.parentElement.parentElement;
                                const text = container ? container.innerText : '';
                                if (text.includes('Såld') || text.includes('Sald')) {
                                    titles.push(t);
                                }
                            }
                        });
                        return titles;
                    }""")
                    sold_titles.extend(cards_data)
                context.close()
        except Exception as e:
            print(f"Error fetching Blocket Avslutade sold titles: {e}", flush=True)

        return sold_titles
