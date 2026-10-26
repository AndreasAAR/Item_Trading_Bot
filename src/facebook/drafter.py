import time
from typing import Dict, Any, List, Optional
from playwright.sync_api import sync_playwright, Page
from config.settings import FB_MARKETPLACE_CREATE_URL, FB_DEFAULT_LOCATION
from src.facebook.session import FacebookSessionManager
from src.mapper.image_downloader import download_item_images
from src.mapper.fb_category_mapper import (
    guess_fb_category,
    map_fb_condition,
    format_fb_title,
    format_fb_description
)

class FacebookDrafter:
    def __init__(self, session_manager: Optional[FacebookSessionManager] = None):
        self.session_manager = session_manager or FacebookSessionManager()

    def _fill_item_on_page(self, page: Page, item_data: Dict[str, Any], publish: bool = False, pause_for_user: bool = False) -> Dict[str, Any]:
        """Fills the Facebook Marketplace listing form with item data."""
        item_id = item_data.get("item_id", "unknown")
        raw_title = item_data.get("title", "")
        title = format_fb_title(raw_title)
        price = str(item_data.get("target_price") or item_data.get("buy_now_price") or 100)
        description = format_fb_description(item_data)
        attributes = item_data.get("attributes", {})
        category_name = guess_fb_category(title, attributes.get("category_path"))
        condition = map_fb_condition(attributes.get("condition"))
        images = item_data.get("images", [])

        print(f"\nDrafting Item #{item_id} on Facebook Marketplace...")
        print(f"Title: {title}")
        print(f"Category: {category_name} | Condition: {condition} | Price: {price} SEK")

        # Step 1: Navigate to Marketplace create item page
        page.goto(FB_MARKETPLACE_CREATE_URL, timeout=45000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(3)

        # Dismiss cookies modal if present
        try:
            cookie_btn = page.locator('div[role="button"]:has-text("Tillåt alla cookies"), button:has-text("Tillåt alla cookies"), div[role="button"]:has-text("Allow all cookies")').first
            if cookie_btn.is_visible(timeout=3000):
                cookie_btn.click()
                time.sleep(1.5)
        except Exception:
            pass

        # Check if redirected to login
        if "login" in page.url.lower():
            raise RuntimeError("Not logged into Facebook. Please run 'python -m src.cli fb-login' first.")

        # Step 2: Upload Images (with visual rotation based on cover_image_index)
        if images:
            from src.pricing.ladder import get_rotated_images
            image_paths = download_item_images(str(item_id), images)
            cover_idx = item_data.get("cover_image_index", 0)
            image_paths = get_rotated_images(image_paths, cover_idx)
            valid_paths = [str(p) for p in image_paths if p.exists()]

            if valid_paths:
                try:
                    file_input = page.locator('input[type="file"][accept*="image"]').first
                    if file_input.count() > 0:
                        file_input.set_input_files(valid_paths)
                        print(f"Uploaded {len(valid_paths)} images.")
                        time.sleep(3)
                except Exception as e:
                    print(f"Notice uploading images: {e}")

        # Step 3: Fill Title
        try:
            title_input = page.locator('label:has-text("Titel") input, label:has-text("Title") input, input[aria-label="Titel"], input[aria-label="Title"]').first
            title_input.wait_for(state="visible", timeout=10000)
            title_input.fill(title)
            print(f"Filled title: {title}")
        except Exception as e:
            print(f"Notice filling title: {e}")

        # Step 4: Fill Price
        try:
            price_input = page.locator('label:has-text("Pris") input, label:has-text("Price") input, input[aria-label="Pris"], input[aria-label="Price"]').first
            price_input.wait_for(state="visible", timeout=5000)
            price_input.fill(price)
            print(f"Filled price: {price} SEK")
        except Exception as e:
            print(f"Notice filling price: {e}")

        # Step 5: Select Category
        try:
            cat_trigger = page.locator('label:has-text("Category") [role="combobox"], label:has-text("Kategori") [role="combobox"], [aria-label="Category"], [aria-label="Kategori"], label:has-text("Category"), label:has-text("Kategori")').first
            if cat_trigger.is_visible(timeout=5000):
                cat_trigger.click(force=True)
                time.sleep(1.5)

                category_options = {
                    "Skor för män": ["Men's Shoes", "Skor för män", "Men's Clothing & Shoes", "Shoes"],
                    "Sport och friluftsliv": ["Sporting Goods", "Sport och friluftsliv", "Sports & Outdoors", "Sports"],
                    "Möbler och heminredning": ["Furniture", "Möbler", "Home Goods", "Home & Kitchen"],
                    "Leksaker och spel": ["Toys & Games", "Leksaker och spel", "Baby & Kids", "Toys"],
                    "Kläder för män": ["Men's Clothing", "Kläder för män", "Clothing, Shoes & Accessories", "Men's Clothing & Shoes", "Clothing"]
                }
                candidates = category_options.get(category_name, [category_name, "Clothing", "Kläder"])
                matched = False
                for c_text in candidates:
                    cat_opt = page.locator(f'span:has-text("{c_text}"), div[role="button"]:has-text("{c_text}"), div[role="menuitem"]:has-text("{c_text}"), div[role="option"]:has-text("{c_text}")').first
                    if cat_opt.is_visible(timeout=1000):
                        cat_opt.click(force=True)
                        print(f"Selected category: {c_text}")
                        matched = True
                        break
                if not matched:
                    fallback = page.locator('span:has-text("Clothing"), span:has-text("Kläder"), div[role="option"]:has-text("Clothing")').first
                    if fallback.is_visible(timeout=1500):
                        fallback.click(force=True)
                        print("Selected fallback category: Clothing")
                time.sleep(1)
        except Exception as e:
            print(f"Notice selecting category: {e}")

        # Step 6: Select Condition
        try:
            cond_trigger = page.locator('label:has-text("Condition") [role="combobox"], label:has-text("Skick") [role="combobox"], [aria-label="Condition"], [aria-label="Skick"], label:has-text("Condition"), label:has-text("Skick")').first
            if cond_trigger.is_visible(timeout=5000):
                cond_trigger.click(force=True)
                time.sleep(1)

                condition_options = {
                    "Ny": ["New", "Ny", "Brand New"],
                    "Som ny": ["Used - Like New", "Used – Like new", "Like new", "Like New", "Som ny"],
                    "Bra skick": ["Used - Good", "Used – Good", "Good", "Bra skick"],
                    "Okej skick": ["Used - Fair", "Used – Fair", "Fair", "Okej skick"]
                }
                candidates = condition_options.get(condition, ["Used - Good", "Good", "Bra skick"])
                matched = False
                for c_text in candidates:
                    cond_opt = page.locator(f'div[role="option"]:has-text("{c_text}"), span:has-text("{c_text}"), div[role="menuitem"]:has-text("{c_text}")').first
                    if cond_opt.is_visible(timeout=1000):
                        cond_opt.click(force=True)
                        print(f"Selected condition: {c_text}")
                        matched = True
                        break
                if not matched:
                    fb_opt = page.locator('div[role="option"]:has-text("Good"), span:has-text("Good"), div[role="option"]:has-text("Bra skick")').first
                    if fb_opt.is_visible(timeout=1500):
                        fb_opt.click(force=True)
                        print("Selected fallback condition: Good")
                time.sleep(1)
        except Exception as e:
            print(f"Notice selecting condition: {e}")

        # Step 7: Fill Description
        try:
            desc_input = page.locator('label:has-text("Beskrivning") textarea, label:has-text("Description") textarea, textarea[aria-label="Beskrivning"], textarea[aria-label="Description"]').first
            if desc_input.is_visible(timeout=5000):
                desc_input.fill(description)
                print("Filled description.")
        except Exception as e:
            print(f"Notice filling description: {e}")

        time.sleep(2)
        try:
            page.screenshot(path="data/fb_filled_draft_test.png")
            print("Captured draft screenshot to data/fb_filled_draft_test.png")
        except Exception:
            pass

        final_status = "drafted"

        if publish:
            print("\nPublishing item to Facebook Marketplace...")
            try:
                next_btn = page.locator('div[aria-label="Nästa"], div[aria-label="Next"], div[role="button"]:has-text("Nästa"), div[role="button"]:has-text("Next")').first
                if next_btn.is_visible(timeout=5000):
                    next_btn.click(force=True)
                    print("Clicked 'Nästa'...")
                    time.sleep(2)

                    pub_btn = page.locator('div[aria-label="Publicera"], div[aria-label="Publish"], div[role="button"]:has-text("Publicera"), div[role="button"]:has-text("Publish")').first
                    if pub_btn.is_visible(timeout=5000):
                        pub_btn.click(force=True)
                        print("Clicked 'Publicera' (Published to Facebook Marketplace)!")
                        time.sleep(4)
                        final_status = "published"
            except Exception as e:
                print(f"Notice during publish: {e}")
        else:
            # Check for Save Draft button
            try:
                save_btn = page.locator('span:has-text("Save Draft"), span:has-text("Save draft"), div[role="button"]:has-text("Save Draft"), div:has-text("Save Draft"), span:has-text("Spara utkast"), div[role="button"]:has-text("Spara utkast"), div[role="button"]:has-text("Spara som utkast"), button:has-text("Save Draft")').first
                if save_btn.is_visible(timeout=4000):
                    save_btn.click(force=True)
                    print("Clicked 'Save Draft' (Successfully saved draft to Facebook Marketplace!).")
                    time.sleep(3)
                else:
                    print("Notice: 'Save Draft' button was not visible, leaving draft in editor.")
            except Exception as e:
                print(f"Notice saving draft: {e}")

        print("\n" + "="*60)
        print(f"Facebook Marketplace ad processed for Item #{item_id}: '{title}' ({final_status})")
        print(f"Price: {price} SEK")
        print("="*60)

        if pause_for_user:
            input("\n>>> [Review Mode] Review draft in browser, then press [ENTER] to continue... ")

        return {
            "item_id": item_id,
            "status": final_status,
            "facebook_url": page.url,
        }

    def draft_item(self, item_data: Dict[str, Any], publish: bool = False, pause_for_user: bool = False) -> Dict[str, Any]:
        """Drafts or publishes a single item on Facebook Marketplace in a browser window."""
        with sync_playwright() as p:
            context = self.session_manager.get_context(p, headless=False)
            page = context.pages[0] if context.pages else context.new_page()
            result = self._fill_item_on_page(page, item_data, publish=publish, pause_for_user=pause_for_user)
            context.close()
            return result

    def draft_batch(self, items: List[Dict[str, Any]], headless: bool = False, delay_between: float = 15.0, publish: bool = False, on_success = None) -> List[Dict[str, Any]]:
        """Pipelined batch execution: drafts or publishes multiple items with safe pacing."""
        results = []
        with sync_playwright() as p:
            context = self.session_manager.get_context(p, headless=headless)
            page = context.pages[0] if context.pages else context.new_page()
            for idx, item in enumerate(items, 1):
                print(f"\n[Facebook Batch {idx}/{len(items)}] Processing Item #{item['item_id']}...")
                try:
                    res = self._fill_item_on_page(page, item, publish=publish, pause_for_user=False)
                    results.append(res)
                    if on_success:
                        on_success(item["item_id"], res.get("facebook_url"), status=res.get("status", "drafted"))
                except Exception as e:
                    print(f"Error drafting item #{item['item_id']} on Facebook: {e}")
                time.sleep(delay_between)
            context.close()
        return results
