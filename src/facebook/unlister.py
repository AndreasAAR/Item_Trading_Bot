import time
import re
import json
import requests
from typing import Optional, List, Dict, Any
from playwright.sync_api import sync_playwright, Page
from config.settings import USER_AGENT
from src.facebook.session import FacebookSessionManager
from src.storage.dedupe import normalize_title


class FacebookUnlister:
    def __init__(self, session_manager: Optional[FacebookSessionManager] = None):
        self.session_manager = session_manager or FacebookSessionManager()

    def get_selling_snapshot(self, headless: bool = True, allow_browser_fallback: bool = False) -> Dict[str, List[str]]:
        """
        Fetches a snapshot of the user's Facebook Marketplace selling dashboard (/marketplace/you/selling).
        First attempts a lightweight HTTP GET with saved session cookies (extracting Relay/SSR JSON).
        Optionally falls back to headless Playwright if allow_browser_fallback=True.
        Returns: {"active_titles": [...], "sold_titles": [...]}
        """
        snapshot: Dict[str, List[str]] = {"active_titles": [], "sold_titles": []}
        if not self.session_manager.has_saved_session():
            return snapshot

        # 1. Fast HTTP SSR JSON extraction
        try:
            data = json.loads(self.session_manager.state_path.read_text(encoding="utf-8"))
            s = requests.Session()
            s.headers.update({
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "sv-SE,sv;q=0.9",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
            })
            for c in data.get("cookies", []):
                s.cookies.set(c["name"], c["value"], domain=c.get("domain", "").lstrip("."))

            resp = s.get("https://www.facebook.com/marketplace/you/selling", timeout=15)
            if resp.status_code == 200 and "login" not in resp.url.lower():
                # Parse embedded Relay listing nodes: marketplace_listing_title + is_sold / is_live
                for m in re.finditer(
                    r'"marketplace_listing_title"\s*:\s*"([^"]+)"(.{0,400})',
                    resp.text
                ):
                    raw_title = m.group(1)
                    context_tail = m.group(2)
                    try:
                        title = json.loads(f'"{raw_title}"').strip()
                    except Exception:
                        title = raw_title.strip()

                    if not title:
                        continue

                    if '"is_sold":true' in context_tail or '"is_pending":true' in context_tail or "Såld" in context_tail:
                        if title not in snapshot["sold_titles"]:
                            snapshot["sold_titles"].append(title)
                    else:
                        if title not in snapshot["active_titles"]:
                            snapshot["active_titles"].append(title)

                if snapshot["active_titles"] or snapshot["sold_titles"]:
                    return snapshot
        except Exception as e:
            print(f"Notice: HTTP snapshot for Facebook Marketplace failed ({e}).", flush=True)

        if not allow_browser_fallback:
            return snapshot

        # 2. Optional Playwright fallback
        try:
            with sync_playwright() as p:
                context = self.session_manager.get_context(p, headless=headless)
                page = context.new_page()
                page.goto("https://www.facebook.com/marketplace/you/selling", timeout=45000)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(3)

                if "login" not in page.url.lower():
                    parsed = page.evaluate("""() => {
                        const active = [];
                        const sold = [];
                        document.querySelectorAll('div[role="article"], a[href*="/marketplace/item/"]').forEach(el => {
                            const txt = el.innerText || '';
                            const lines = txt.split('\\n').map(l => l.trim()).filter(Boolean);
                            if (lines.length >= 2) {
                                const title = lines[0].includes('kr') && lines.length > 1 ? lines[1] : lines[0];
                                if (txt.includes('Såld') || txt.includes('Sold')) {
                                    if (!sold.includes(title)) sold.push(title);
                                } else {
                                    if (!active.includes(title)) active.push(title);
                                }
                            }
                        });
                        return { active_titles: active, sold_titles: sold };
                    }""")
                    snapshot["active_titles"] = parsed.get("active_titles", [])
                    snapshot["sold_titles"] = parsed.get("sold_titles", [])
                context.close()
        except Exception as e:
            print(f"Error fetching Facebook selling snapshot via browser: {e}", flush=True)

        return snapshot

    def get_ended_sold_titles(self, headless: bool = True, allow_browser_fallback: bool = False) -> List[str]:
        """Returns titles of listings marked as 'Såld'/'Sold' on Facebook Marketplace."""
        snap = self.get_selling_snapshot(headless=headless, allow_browser_fallback=allow_browser_fallback)
        return snap.get("sold_titles", [])

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
