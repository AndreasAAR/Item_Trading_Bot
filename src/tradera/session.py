import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, BrowserContext, Playwright

from config.settings import (
    TRADERA_AUTH_STATE_PATH,
    TRADERA_LOGIN_URL,
    USER_AGENT
)


class TraderaSessionManager:
    def __init__(self, state_path: Path = TRADERA_AUTH_STATE_PATH):
        self.state_path = state_path

    def has_saved_session(self) -> bool:
        """Checks if a valid saved Tradera session exists."""
        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cookies = data.get("cookies", [])
                if any("tradera" in c.get("domain", "").lower() for c in cookies):
                    return True
            except Exception:
                pass
        return False

    def save_manual_cookies(self, trd_at: str, trd_rt: str = "") -> bool:
        """Saves session directly from manual trd_at and optional trd_rt cookies."""
        trd_at = trd_at.strip()
        trd_rt = trd_rt.strip() if trd_rt else ""
        if not trd_at:
            print("[ERROR] 'trd_at' cookie/token is required.", flush=True)
            return False

        cookies = [
            {
                "name": "trd_at",
                "value": trd_at,
                "domain": ".tradera.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            }
        ]
        if trd_rt:
            cookies.append({
                "name": "trd_rt",
                "value": trd_rt,
                "domain": ".tradera.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            })

        state = {
            "cookies": cookies,
            "origins": [{"origin": "https://www.tradera.com", "localStorage": []}]
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        print(f"\n[SUCCESS] Tradera session cookies saved to {self.state_path}!", flush=True)
        return True

    def save_cookie_string(self, cookie_str: str) -> bool:
        """Parses a raw Cookie header string from tradera.com and saves all Tradera cookies."""
        import http.cookies
        cookie_str = cookie_str.strip()
        if not cookie_str:
            print("[ERROR] Empty cookie string provided.", flush=True)
            return False

        cookies = []
        # Support semicolon-separated cookies
        parts = [p.strip() for p in cookie_str.split(";") if "=" in p]
        for p in parts:
            name, val = p.split("=", 1)
            name = name.strip()
            val = val.strip()
            cookies.append({
                "name": name,
                "value": val,
                "domain": ".tradera.com",
                "path": "/",
                "httpOnly": name in ("trd_at", "trd_rt"),
                "secure": True,
                "sameSite": "Lax",
            })

        if not cookies:
            print("[ERROR] No cookies parsed from cookie string.", flush=True)
            return False

        state = {
            "cookies": cookies,
            "origins": [{"origin": "https://www.tradera.com", "localStorage": []}]
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        print(f"\n[SUCCESS] Saved {len(cookies)} Tradera cookies to {self.state_path}!", flush=True)
        return True

    def get_context(self, p: Playwright, headless: bool = True) -> BrowserContext:
        """Returns a Playwright BrowserContext with Tradera credentials injected."""
        browser = p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )

        storage_state = str(self.state_path) if self.has_saved_session() else None
        context = browser.new_context(
            storage_state=storage_state,
            user_agent=USER_AGENT,
            locale="sv-SE",
            viewport={"width": 1280, "height": 900}
        )
        return context

    def interactive_login(self) -> bool:
        """
        Opens a visible browser for the user to log in once via BankID or password.
        Saves authenticated session cookies to disk upon successful login.
        """
        print("\nOpening Tradera login in visible browser...", flush=True)
        print("Please complete the login in the browser window (BankID or password).\n", flush=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="sv-SE",
                viewport={"width": 1280, "height": 900}
            )
            page = context.new_page()
            page.goto(TRADERA_LOGIN_URL)

            # Wait for user to log in
            max_wait_seconds = 300
            start_time = time.time()
            logged_in = False

            while time.time() - start_time < max_wait_seconds:
                cur_url = page.url.lower()
                # Check if redirected away from login page to logged-in destination
                if "tradera.com" in cur_url and "/login" not in cur_url and "auth" not in cur_url:
                    # Verify by checking if user avatar, 'mitt tradera', or logout button is visible
                    try:
                        mitt_tradera = page.locator('text=Mitt Tradera, a[href*="my-tradera"], button:has-text("Konto")')
                        if mitt_tradera.count() > 0 or not cur_url.endswith("/login"):
                            logged_in = True
                            break
                    except Exception:
                        logged_in = True
                        break
                time.sleep(1.5)

            if logged_in:
                time.sleep(2)  # Allow tokens/cookies to settle
                self.state_path.parent.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(self.state_path))
                print(f"[OK] Tradera login successful! Session saved to: {self.state_path}", flush=True)
                context.close()
                return True
            else:
                print("[ERROR] Login timed out after 5 minutes.", flush=True)
                context.close()
                return False
