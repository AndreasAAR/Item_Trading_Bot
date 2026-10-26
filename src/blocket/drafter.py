import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from playwright.sync_api import sync_playwright, Page
from config.settings import BLOCKET_NEW_AD_URL
from src.blocket.session import BlocketSessionManager
from src.mapper.category_mapper import guess_blocket_category, map_condition, map_color
from src.mapper.formatter import format_blocket_title, format_blocket_description
from src.mapper.image_downloader import download_item_images

class BlocketDrafter:
    def __init__(self, session_manager: BlocketSessionManager = None, default_postal_code: str = "11322"):
        self.session_manager = session_manager or BlocketSessionManager()
        self.default_postal_code = default_postal_code

    def _fill_ad_on_page(self, page: Page, item_data: Dict[str, Any], pause_for_user: bool = False, auto_save_to_cloud: bool = True, publish: bool = False) -> Dict[str, Any]:
        """Core automation logic on an active page."""
        item_id = item_data["item_id"]
        title = format_blocket_title(item_data["title"])
        price = str(item_data["target_price"])
        description = format_blocket_description(item_data)
        attributes = item_data.get("attributes", {})
        cat_hint = guess_blocket_category(
            title,
            category_path=attributes.get("category_path"),
            tradera_cat_id=item_data.get("category_id")
        )

        # Download and stage images locally (with visual rotation based on cover_image_index)
        from src.pricing.ladder import get_rotated_images
        image_urls = item_data.get("images", [])
        staged_image_paths = download_item_images(item_id, image_urls)
        cover_idx = item_data.get("cover_image_index", 0)
        staged_image_paths = get_rotated_images(staged_image_paths, cover_idx)
        print(f"Staged {len(staged_image_paths)} images for item {item_id} (cover index: #{cover_idx % len(staged_image_paths) if staged_image_paths else 0}).")


        print("Navigating to Blocket create item start...")
        page.goto(BLOCKET_NEW_AD_URL, timeout=45000)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(2)

        # Accept cookies if banner appears
        try:
            cookie_btn = page.locator('button:has-text("Acceptera"), button:has-text("Godkänn alla"), button:has-text("Tillåt alla")')
            if cookie_btn.first.is_visible(timeout=2000):
                cookie_btn.first.click()
        except Exception:
            pass

        # Close any promotional modal ("Säg hej till nya Blocket")
        try:
            promo_close = page.locator('button:has-text("Påminn mig senare"), button[aria-label="Stäng"], button:has-text("Stäng")')
            if promo_close.first.is_visible(timeout=2000):
                promo_close.first.click()
                time.sleep(0.5)
        except Exception:
            pass

        # Submit form to create fresh recommerce session if not already in editor
        if "recommerce/create" not in page.url:
            try:
                form = page.locator("form[action*='ad-insertion'], form").first
                if form.count() > 0:
                    form.evaluate("f => f.submit()")
                else:
                    page.locator('button:has-text("Välj"), a:has-text("Ny annons")').first.click()
                page.wait_for_url("**/recommerce/create/**", timeout=20000)
            except Exception as e:
                print(f"Notice launching editor session: {e}")

        print(f"Active Editor URL: {page.url}")

        # Step 2: Upload Images
        if staged_image_paths:
            try:
                file_input = page.locator('input[type="file"]')
                if file_input.count() > 0:
                    file_input.first.set_input_files([str(p.resolve()) for p in staged_image_paths])
                    print(f"Uploaded {len(staged_image_paths)} images.")
                    time.sleep(3)
            except Exception as e:
                print(f"Notice attaching images: {e}")

        # Step 3: Select Categories (Huvudkategori, Underkategori, Produktkategori)
        try:
            selects = page.locator("select").all()
            if len(selects) > 0 and cat_hint.get("main"):
                s0_opts = [o.strip() for o in selects[0].locator("option").all_inner_texts() if o.strip()]
                if cat_hint["main"] in s0_opts:
                    selects[0].select_option(label=cat_hint["main"])
                    time.sleep(0.5)

            selects = page.locator("select").all()
            if len(selects) > 1 and cat_hint.get("sub"):
                s1_opts = [o.strip() for o in selects[1].locator("option").all_inner_texts() if o.strip()]
                if cat_hint["sub"] in s1_opts:
                    selects[1].select_option(label=cat_hint["sub"])
                    time.sleep(0.5)

            selects = page.locator("select").all()
            if len(selects) > 2:
                s2_opts = [o.strip() for o in selects[2].locator("option").all_inner_texts() if o.strip()]
                chosen_prod = None
                if cat_hint.get("prod") and cat_hint["prod"] in s2_opts:
                    chosen_prod = cat_hint["prod"]
                else:
                    for opt in s2_opts:
                        if any(w in opt.lower() for w in ["övrigt", "övriga", "annat"]):
                            chosen_prod = opt
                            break
                    if not chosen_prod and len(s2_opts) > 1:
                        chosen_prod = s2_opts[1]
                if chosen_prod:
                    selects[2].select_option(label=chosen_prod)
                    print(f"Selected Produktkategori: {chosen_prod}")
                    time.sleep(0.8)
        except Exception as e:
            print(f"Notice setting categories: {e}")

        # Step 4: Fill Structured Attribute Selects (Skick, Färg, Passform)
        try:
            target_cond = map_condition(attributes.get("condition"))
            target_color = map_color(attributes.get("color"))
            target_fit = attributes.get("fit", "Normal i storleken")

            for s in page.locator("select").all():
                opts = [o.strip() for o in s.locator("option").all_inner_texts() if o.strip()]
                # Condition
                if target_cond and any("skick" in o.lower() for o in opts):
                    if target_cond in opts:
                        s.select_option(label=target_cond)
                    elif any("bra skick" in o.lower() for o in opts):
                        s.select_option(label="Bra skick - varsamt använd")

                # Color
                if target_color and "Svart" in opts and "Vit" in opts:
                    if target_color in opts:
                        s.select_option(label=target_color)

                # Fit
                if target_fit and "Normal i storleken" in opts:
                    if target_fit in opts:
                        s.select_option(label=target_fit)
        except Exception as e:
            print(f"Notice selecting attributes: {e}")

        # Step 5: Fill Text Attributes (Storlek, Varumärke, Material)
        try:
            text_inputs = [inp for inp in page.locator('input[type="text"]').all() if inp.get_attribute("name") != "title"]
            size_val = attributes.get("size")
            brand_val = attributes.get("brand")
            mat_val = attributes.get("material")

            if len(text_inputs) >= 1 and size_val:
                text_inputs[0].fill(size_val)
                print(f"Filled size: {size_val}")
            if len(text_inputs) >= 2 and brand_val:
                text_inputs[1].fill(brand_val)
                print(f"Filled brand: {brand_val}")
            if len(text_inputs) >= 3 and mat_val:
                text_inputs[2].fill(mat_val)
                print(f"Filled material: {mat_val}")
        except Exception as e:
            print(f"Notice filling text attributes: {e}")

        # Step 6: Fill Title
        try:
            title_inp = page.locator('input[name="title"]').first
            if title_inp.is_visible(timeout=3000):
                title_inp.fill(title)
                print(f"Filled title: {title}")
        except Exception as e:
            print(f"Notice filling title: {e}")

        time.sleep(1)

        # Step 4: Fill Description
        try:
            # Exclude the image caption textarea which has placeholder="Bildtext"
            desc_inp = page.locator('textarea:not([placeholder*="Bildtext"])').first
            if desc_inp.is_visible(timeout=3000):
                desc_inp.fill(description)
                print("Filled main ad description field.")
            else:
                # Fallback to last textarea on page if not found
                page.locator('textarea').last.fill(description)
                print("Filled ad description (last textarea fallback).")
        except Exception as e:
            print(f"Notice filling description: {e}")

        # Step 5: Fill Price & Postal Code
        try:
            num_inps = page.locator('input[type="number"]').all()
            if len(num_inps) > 0:
                num_inps[0].fill(price)
                print(f"Filled price: {price} SEK")
            if len(num_inps) > 1:
                post_inp = num_inps[1]
                post_inp.click()
                post_inp.fill("")
                post_inp.press_sequentially(self.default_postal_code, delay=80)
                post_inp.press("Tab")
                print(f"Filled postal code: {self.default_postal_code}")
        except Exception as e:
            print(f"Notice filling price/postcode: {e}")

        time.sleep(1.5)

        # Step 6: Direct Publish or Save as Cloud Draft
        final_status = "drafted"
        if publish:
            try:
                # 1. Click Fortsätt
                fortsatt_btn = page.locator('w-button:has-text("Fortsätt"), button:has-text("Fortsätt")').first
                if fortsatt_btn.is_visible(timeout=5000):
                    fortsatt_btn.scroll_into_view_if_needed()
                    fortsatt_btn.click()
                    print("Clicked 'Fortsätt' to proceed towards publishing...")
                    time.sleep(2.5)

                # 2. Check for BankID identity confirmation modal or Vend auth redirect
                bankid_btn = page.locator('w-button:has-text("Verifiera med BankID"), button:has-text("Verifiera med BankID")').first
                if bankid_btn.is_visible(timeout=3000):
                    print("Clicking 'Verifiera med BankID'...")
                    bankid_btn.click()
                    time.sleep(3)

                # Check if navigated to Vend/Schibsted auth page
                if "vend.se" in page.url or "schibsted.com" in page.url or "auth.blocket.se" in page.url:
                    print("Landed on Vend authentication page...")
                    cont = page.locator('#continue-button, w-button:has-text("Fortsätt"), button:has-text("Fortsätt")').first
                    if cont.is_visible(timeout=3000):
                        print("Clicking 'Fortsätt' on Vend login...")
                        cont.click()
                        time.sleep(3)

                    mbid = page.locator('button:has-text("Mobilt BankID"), w-button:has-text("Mobilt BankID"), [role="button"]:has-text("Mobilt BankID")').first
                    if mbid.is_visible(timeout=3000):
                        print("Clicking 'Mobilt BankID på annan enhet'...")
                        mbid.click()
                        time.sleep(2)

                    print("\n" + "="*65)
                    print(">>> [BANKID PROMPT ACTIVE] Please scan QR code or approve BankID on phone! <<<")
                    print("Waiting up to 120 seconds for verification to complete...")
                    print("="*65 + "\n")

                    for _ in range(24):
                        time.sleep(5)
                        if "blocket.se" in page.url and "auth" not in page.url and "login" not in page.url:
                            print("BankID verified! Returned to Blocket.")
                            break

                # 3. Wait up to 15s for checkout / payment-options screen
                try:
                    page.wait_for_url("**/order-and-payment/**", timeout=12000)
                except Exception:
                    pass

                # 4. Handle order-and-payment / payment-options funnel
                if "order-and-payment" in page.url or "payment-options" in page.url:
                    print(f"Landed on payment & options screen: {page.url}")
                    time.sleep(2)

                    # A. Frakt handling (shipping option)
                    try:
                        frakt_opt = page.locator('input[type="radio"][value*="frakt"], input[type="radio"][value*="shipping"], label:has-text("Frakt"), [role="radio"]:has-text("Frakt")').first
                        if frakt_opt.is_visible(timeout=2500):
                            frakt_opt.click()
                            print("Selected Frakt option.")
                            time.sleep(1)
                    except Exception as e:
                        print(f"Notice handling frakt: {e}")

                    # B. Select Gratis tier
                    try:
                        gratis_opt = page.locator('label:has-text("Gratis"), [role="radio"]:has-text("Gratis"), input[value*="free"], label:has-text("0 kr"), [role="radio"]:has-text("Bas")').first
                        if gratis_opt.is_visible(timeout=3000):
                            gratis_opt.click()
                            print("Selected 'Gratis' ad tier.")
                            time.sleep(1)
                        else:
                            card = page.locator('div:has-text("Gratis"), div:has-text("0 kr")').last
                            if card.is_visible(timeout=2000):
                                card.click()
                                print("Selected Gratis package card.")
                                time.sleep(1)
                    except Exception as e:
                        print(f"Notice selecting Gratis tier: {e}")

                    # C. Click Fortsätt / Publicera on checkout page
                    try:
                        checkout_next = page.locator('w-button:has-text("Fortsätt"), button:has-text("Fortsätt"), w-button:has-text("Publicera"), button:has-text("Publicera"), button:has-text("Slutför"), w-button:has-text("Slutför")').first
                        if checkout_next.is_visible(timeout=4000):
                            checkout_next.scroll_into_view_if_needed()
                            checkout_next.click()
                            print("Clicked Fortsätt/Publicera on payment page!")
                            time.sleep(3)
                    except Exception as e:
                        print(f"Notice advancing payment page: {e}")

                    # Wait for ad-receipt
                    try:
                        page.wait_for_url("**/ad-receipt**", timeout=15000)
                        print("Confirmation reached: Ad receipt confirmed!")
                    except Exception:
                        pass

                # 5. Check for any remaining Publicera button
                pub_btn = page.locator('w-button:has-text("Publicera annons"), w-button:has-text("Publicera"), button:has-text("Publicera annons"), button:has-text("Publicera")').first
                if pub_btn.is_visible(timeout=3000):
                    pub_btn.scroll_into_view_if_needed()
                    pub_btn.click()
                    print("Clicked 'Publicera annons'!")
                    time.sleep(4)

                final_status = "published"
                page.screenshot(path="data/blocket_last_publish.png")
            except Exception as e:
                print(f"Notice during publish: {e}")
        elif auto_save_to_cloud:
            try:
                save_btn = page.locator('w-button:has-text("Fortsätt"), button:has-text("Fortsätt"), button:has-text("Förhandsvisa"), button:has-text("Nästa")')
                if save_btn.count() > 0 and save_btn.first.is_visible(timeout=3000):
                    save_btn.first.scroll_into_view_if_needed()
                    save_btn.first.click()
                    print("Clicked 'Fortsätt' - draft saved to your Blocket account!")
                    time.sleep(3)
            except Exception as e:
                print(f"Notice saving draft: {e}")

        print("\n" + "="*60)
        print(f"Item #{item_id}: '{title}' {final_status} on Blocket.")
        print(f"Price: {price} SEK")
        print(f"Status: {final_status.capitalize()}")
        print("="*60)

        if pause_for_user:
            input("\n>>> [Review Mode] Review in browser, then press [ENTER] to continue... ")

        return {
            "item_id": item_id,
            "status": final_status,
            "blocket_url": page.url,
        }

    def draft_item(self, item_data: Dict[str, Any], pause_for_user: bool = False, auto_save_to_cloud: bool = True, publish: bool = False) -> Dict[str, Any]:
        """Drafts or publishes a single item in an isolated browser window."""
        with sync_playwright() as p:
            context = self.session_manager.get_context(p, headless=False)
            page = context.new_page()
            result = self._fill_ad_on_page(page, item_data, pause_for_user=pause_for_user, auto_save_to_cloud=auto_save_to_cloud, publish=publish)
            context.close()
            return result

    def draft_batch(self, items: List[Dict[str, Any]], headless: bool = False, delay_between: float = 30.0, publish: bool = False, on_success = None) -> List[Dict[str, Any]]:
        """Pipelined batch execution: drafts or publishes multiple items in a single persistent browser session with anti-suspicion delay."""
        import random
        results = []
        with sync_playwright() as p:
            context = self.session_manager.get_context(p, headless=headless)
            page = context.new_page()
            for idx, item in enumerate(items, 1):
                action_name = "Publishing" if publish else "Drafting"
                print(f"\n[Batch {idx}/{len(items)}] {action_name} Item #{item['item_id']} - '{item['title']}'...")
                try:
                    res = self._fill_ad_on_page(page, item, pause_for_user=False, auto_save_to_cloud=not publish, publish=publish)
                    results.append(res)
                    if on_success:
                        on_success(item["item_id"], res.get("blocket_url"), res.get("status", "drafted"))
                except Exception as e:
                    print(f"Error processing item #{item['item_id']}: {e}")

                if idx < len(items):
                    rest_secs = round(delay_between + random.uniform(3.0, 10.0), 1)
                    print(f"\n[Safe Rest Delay] Resting for {rest_secs} seconds to stay human-like and avoid detection...")
                    for s in range(int(rest_secs), 0, -5):
                        print(f"  ... {s}s remaining", flush=True)
                        time.sleep(min(5, s))
            try:
                context.storage_state(path=str(self.session_manager.state_path))
            except Exception:
                pass
            context.close()
        return results
