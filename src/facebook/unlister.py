import time
import re
from typing import Optional, List, Dict, Any
from playwright.sync_api import sync_playwright, Page
from src.facebook.session import FacebookSessionManager
from src.storage.dedupe import normalize_title


class FacebookUnlister:
    def __init__(self, session_manager: Optional[FacebookSessionManager] = None):
        self.session_manager = session_manager or FacebookSessionManager()

    def unlist_items(self, target_titles: List[str], headless: bool = True) -> Dict[str, bool]:
        """
        Unlists specified titles from Facebook Marketplace (Your Listings / you/selling).
        Returns a dictionary mapping each title to bool (True if removed, False otherwise).
        """
        results: Dict[str, bool] = {t: False for t in target_titles}

        if not target_titles:
            return results

        if not self.session_manager.has_saved_session():
            print("Notice: No saved Facebook session found. Run 'python -m src.cli fb-login' to authenticate.", flush=True)
            return results

        try:
            with sync_playwright() as p:
                context = self.session_manager.get_context(p, headless=headless)
                page = context.new_page()

                print("Navigating to Facebook Marketplace: Your Listings...", flush=True)
                page.goto("https://www.facebook.com/marketplace/you/selling", timeout=45000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(3)

                # Check if redirected to login
                if "login" in page.url.lower():
                    print("Facebook session expired. Interactive login needed.", flush=True)
                    context.close()
                    return results

                # For each title, attempt to find and delete listing
                for title in target_titles:
                    try:
                        clean_target = normalize_title(title)
                        # Find link or heading containing key title words
                        words = [w for w in clean_target.split() if len(w) > 3][:3]
                        search_term = " ".join(words) if words else clean_target

                        locator = page.locator(f':text-matches("{re.escape(search_term)}", "i")').first
                        if locator.is_visible(timeout=3000):
                            print(f"Found Facebook listing for '{title}'", flush=True)
                            locator.scroll_into_view_if_needed()
                            time.sleep(0.5)

                            # Locate card container
                            container = locator.locator("xpath=./ancestor::div[@role='article' or contains(@class, 'x1')]").first
                            
                            # Click ... menu
                            more_btn = container.locator('div[aria-label*="Mer"], div[aria-label*="More"], div[role="button"]:has(svg)').first
                            if more_btn.is_visible(timeout=2000):
                                more_btn.click()
                                time.sleep(1)

                                # Click Delete listing
                                del_opt = page.locator('div[role="menuitem"]:has-text("Ta bort annons"), div[role="menuitem"]:has-text("Delete listing")').first
                                if del_opt.is_visible(timeout=2000):
                                    del_opt.click()
                                    time.sleep(1)

                                    # Reason: Sold elsewhere / Sålde någon annanstans
                                    reason_opt = page.locator('div[role="radio"]:has-text("annanstans"), div[role="radio"]:has-text("elsewhere")').first
                                    if reason_opt.is_visible(timeout=2000):
                                        reason_opt.click()
                                        time.sleep(0.5)

                                    # Confirm button
                                    confirm_btn = page.locator('div[aria-label="Ta bort"], div[aria-label="Delete"], button:has-text("Ta bort")').first
                                    if confirm_btn.is_visible(timeout=2000):
                                        confirm_btn.click()
                                        print(f"Successfully deleted Facebook listing for '{title}'!", flush=True)
                                        results[title] = True
                                        time.sleep(2)

                    except Exception as e:
                        print(f"Error unlisting '{title}' on Facebook: {e}", flush=True)

                context.close()
        except Exception as e:
            print(f"Error during Facebook unlisting: {e}", flush=True)

        return results

    def unlist_item(self, title: str, headless: bool = True) -> bool:
        res = self.unlist_items([title], headless=headless)
        return res.get(title, False)
