import time
import re
from typing import Optional
from playwright.sync_api import sync_playwright, Page
from config.settings import BLOCKET_AUTH_STATE_PATH
from src.blocket.session import BlocketSessionManager

class BlocketDraftCleaner:
    def __init__(self, session_manager: Optional[BlocketSessionManager] = None):
        self.session_manager = session_manager or BlocketSessionManager()

    def clean_all_drafts(self, headless: bool = True, max_deletions: int = 150) -> int:
        """Deletes all drafts from Blocket cloud account."""
        deleted_count = 0
        with sync_playwright() as p:
            context = self.session_manager.get_context(p, headless=headless)
            page = context.new_page()

            print("Navigating to Blocket My Items...", flush=True)
            page.goto("https://www.blocket.se/my-items", timeout=45000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(3)
            page.screenshot(path="data/cleaner_debug.png")
            print(f"Landed on: {page.url} ({page.title()})", flush=True)

            # Accept cookies if banner appears
            try:
                cookie_btn = page.locator('button:has-text("Acceptera"), button:has-text("Godkänn alla"), button:has-text("Tillåt alla")')
                if cookie_btn.first.is_visible(timeout=2000):
                    cookie_btn.first.click()
            except Exception:
                pass

            # Select Utkast tab (only displayed if drafts > 0)
            utkast_label = page.locator("label").filter(has_text="Utkast").first
            time.sleep(2)
            try:
                if not utkast_label.is_visible():
                    print("Utkast tab is not present - 0 drafts exist on Blocket account.", flush=True)
                    context.close()
                    return 0
                utkast_label.click(timeout=5000)
            except Exception as e:
                print(f"Utkast tab not found or not clickable ({e}) - 0 drafts exist.", flush=True)
                context.close()
                return 0

            time.sleep(2)
            label_text = utkast_label.inner_text()
            print(f"Initial status: {label_text}", flush=True)

            m = re.search(r'\((\d+)\)', label_text)
            total_drafts = int(m.group(1)) if m else 0

            if total_drafts == 0:
                print("No drafts to delete.", flush=True)
                context.close()
                return 0

            print(f"Starting deletion of {total_drafts} drafts...", flush=True)

            while deleted_count < max_deletions:
                # Find first dots button on current page
                dots_buttons = page.locator('w-button:has(w-icon[name="Dots"])').all()
                if not dots_buttons:
                    # Try reload page and re-click Utkast
                    page.goto("https://www.blocket.se/my-items", timeout=30000)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(2)
                    utkast_label = page.locator("label").filter(has_text="Utkast").first
                    utkast_label.click()
                    time.sleep(2)
                    dots_buttons = page.locator('w-button:has(w-icon[name="Dots"])').all()
                    if not dots_buttons:
                        print("No more drafts found.", flush=True)
                        break

                try:
                    dots_buttons[0].click()
                    time.sleep(0.5)

                    del_link = page.locator('a[title="Ta bort"]').first
                    if not del_link.is_visible():
                        dots_buttons[0].click()
                        time.sleep(0.5)

                    del_link.click()
                    time.sleep(0.8)

                    confirm_btn = page.locator('w-modal w-button:has-text("Ta bort"), w-button[variant="primary"]:has-text("Ta bort")').first
                    confirm_btn.click()
                    deleted_count += 1
                    time.sleep(1.2)

                    if deleted_count % 5 == 0:
                        cur_text = page.locator("label").filter(has_text="Utkast").first.inner_text()
                        print(f"Deleted {deleted_count} drafts. Current: {cur_text}", flush=True)

                except Exception as e:
                    print(f"Notice during draft delete: {e}", flush=True)
                    time.sleep(1)
                    # refresh to restore clean state
                    page.goto("https://www.blocket.se/my-items", timeout=30000)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(2)
                    lbl = page.locator("label").filter(has_text="Utkast").first
                    if not lbl.is_visible():
                        print("Utkast tab no longer visible - all drafts deleted!", flush=True)
                        break
                    lbl.click()
                    time.sleep(2)

            try:
                final_text = page.locator("label").filter(has_text="Utkast").first.inner_text()
            except Exception:
                final_text = "0 drafts remaining"
            print(f"\nCompleted! Total deleted: {deleted_count}. Final status: {final_text}", flush=True)
            context.close()

        return deleted_count
