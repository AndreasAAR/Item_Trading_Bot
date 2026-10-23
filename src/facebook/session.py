import json
from pathlib import Path
from playwright.sync_api import sync_playwright, BrowserContext
from config.settings import FB_AUTH_STATE_PATH, FB_BASE_URL, USER_AGENT, DATA_DIR

FB_PROFILE_DIR = DATA_DIR / "fb_chrome_profile"

STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-infobars",
]

STEALTH_INIT_SCRIPT = """
// 1. Hide webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// 2. Mock chrome runtime
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

// 3. Mock plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
});

// 4. Mock languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['sv-SE', 'sv', 'en-US', 'en']
});
"""

class FacebookSessionManager:
    def __init__(self, state_path: Path = FB_AUTH_STATE_PATH, profile_dir: Path = FB_PROFILE_DIR):
        self.state_path = state_path
        self.profile_dir = profile_dir

    def has_saved_session(self) -> bool:
        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cookies = data.get("cookies", [])
                if any(c.get("name") == "c_user" for c in cookies):
                    return True
            except Exception:
                pass
        return False

    def interactive_login(self) -> bool:
        """
        Opens a visible, persistent real Chrome profile.
        Uses persistent storage (non-incognito) + stealth overrides to enable Arkose Labs MatchKey.
        """
        print(f"\n" + "="*60)
        print("Launching Real Google Chrome (Persistent Profile + Stealth)")
        print("Bypassing Arkose Labs bot detection for 2FA/MatchKey...")
        print("="*60)
        
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    channel="chrome",
                    headless=False,
                    args=STEALTH_ARGS,
                    ignore_default_args=["--enable-automation"],
                    viewport={"width": 1280, "height": 900},
                    locale="sv-SE",
                    user_agent=USER_AGENT,
                )
            except Exception as e:
                print(f"Notice launching Chrome channel ({e}), falling back to default Chromium...")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    headless=False,
                    args=STEALTH_ARGS,
                    ignore_default_args=["--enable-automation"],
                    viewport={"width": 1280, "height": 900},
                    locale="sv-SE",
                    user_agent=USER_AGENT,
                )

            context.add_init_script(STEALTH_INIT_SCRIPT)
            page = context.pages[0] if context.pages else context.new_page()

            print("Navigating to Facebook login...")
            page.goto("https://www.facebook.com/login.php", timeout=60000)

            # Auto dismiss cookies banner if present
            try:
                time.sleep(2)
                cookie_btn = page.locator('div[role="button"]:has-text("Tillåt alla cookies"), button:has-text("Tillåt alla cookies"), div[role="button"]:has-text("Allow all cookies")').first
                if cookie_btn.is_visible(timeout=3000):
                    cookie_btn.click()
            except Exception:
                pass

            print("\n>>> Please complete your login and 2FA in the browser window.")
            print(">>> Take your time. Arkose Labs MatchKey bot detection is masked.")
            
            has_c_user = False
            while True:
                input(">>> Once you are logged in and see Facebook Marketplace or Feed, press [ENTER] here: ")
                cookies = context.cookies()
                has_c_user = any(c.get("name") == "c_user" for c in cookies)
                if has_c_user:
                    print("\n[SUCCESS] Detected authenticated Facebook session ('c_user')!")
                    break
                print("\n[WARNING] Logged-in user cookie ('c_user') was not detected yet.")
                print("If you are still completing 2FA or SMS verification, please finish that first.")
                retry = input("Press [ENTER] to check again, or type 'q' to abort: ")
                if retry.strip().lower() == "q":
                    break

            if has_c_user:
                try:
                    context.storage_state(path=str(self.state_path))
                    print(f"Facebook session saved to {self.state_path}!")

                    print("Verifying Marketplace access...")
                    page.goto("https://www.facebook.com/marketplace", timeout=30000)
                    time.sleep(2)
                    page.screenshot(path="data/fb_login_verified.png")
                    print("Verification screenshot saved to data/fb_login_verified.png")
                except Exception as e:
                    print(f"Notice during verification ({e}), persistent profile saved in {self.profile_dir}.")

            context.close()
            return has_c_user

    def save_manual_cookies(self, c_user: str, xs: str) -> bool:
        """
        Saves session directly from manual c_user and xs cookies.
        Fastest and bypasses all browser bot detection / 2FA issues.
        """
        c_user = c_user.strip()
        xs = xs.strip()
        if not c_user or not xs:
            print("[ERROR] Both c_user and xs cookies are required.")
            return False

        cookies = [
            {"name": "c_user", "value": c_user, "domain": ".facebook.com", "path": "/", "httpOnly": False, "secure": True, "sameSite": "None"},
            {"name": "xs", "value": xs, "domain": ".facebook.com", "path": "/", "httpOnly": True, "secure": True, "sameSite": "None"},
            {"name": "wd", "value": "1280x900", "domain": ".facebook.com", "path": "/", "httpOnly": False, "secure": True, "sameSite": "Lax"},
        ]
        state = {
            "cookies": cookies,
            "origins": [{"origin": "https://www.facebook.com", "localStorage": []}]
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        print(f"\n[SUCCESS] Facebook session with User ID {c_user} saved to {self.state_path}!")
        return True

    def save_cookie_string(self, cookie_str: str) -> bool:
        """Parses a cookie header string (e.g. from Chrome DevTools) and extracts c_user and xs."""
        import re
        c_user_match = re.search(r'c_user=([^;]+)', cookie_str)
        xs_match = re.search(r'xs=([^;]+)', cookie_str)
        if not c_user_match or not xs_match:
            print("[ERROR] Could not find both 'c_user' and 'xs' in cookie string.")
            return False
        return self.save_manual_cookies(c_user_match.group(1), xs_match.group(1))

    def login_via_cdp(self, cdp_url: str = "http://localhost:9222") -> bool:
        """Connects to an existing Chrome browser running with --remote-debugging-port=9222 and exports storage state."""
        print(f"\nConnecting to Chrome at {cdp_url}...")
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(cdp_url)
            except Exception as e:
                print(f"[ERROR] Could not connect to Chrome on port 9222: {e}")
                print("Make sure you started Chrome with: start chrome --remote-debugging-port=9222")
                return False

            context = browser.contexts[0] if browser.contexts else None
            if not context:
                print("[ERROR] No browser contexts found in connected Chrome.")
                return False

            cookies = context.cookies()
            has_c_user = any(c.get("name") == "c_user" for c in cookies)

            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(self.state_path))

            if has_c_user:
                print(f"\n[SUCCESS] Connected to Chrome and saved authenticated Facebook session to {self.state_path}!")
            else:
                print(f"\n[WARNING] Cookies saved to {self.state_path}, but 'c_user' cookie was not found.")
                print("Make sure you are logged in to facebook.com in that Chrome window.")

            return has_c_user

    def import_chrome_cookies(self) -> bool:
        """Directly imports active Facebook session cookies from the local Google Chrome profile on Windows."""
        import os, sqlite3, shutil, base64, tempfile, ctypes
        from ctypes import wintypes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]

        def dpapi_decrypt(encrypted_bytes):
            blob_in = DATA_BLOB(len(encrypted_bytes), ctypes.create_string_buffer(encrypted_bytes, len(encrypted_bytes)))
            blob_out = DATA_BLOB()
            if ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
                data = ctypes.string_at(blob_out.pbData, blob_out.cbData)
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)
                return data
            return None

        local_app_data = os.environ.get("LOCALAPPDATA", "")
        local_state_path = Path(local_app_data) / "Google" / "Chrome" / "User Data" / "Local State"
        cookie_path = Path(local_app_data) / "Google" / "Chrome" / "User Data" / "Default" / "Network" / "Cookies"

        if not local_state_path.exists() or not cookie_path.exists():
            print("[ERROR] Chrome cookies file or Local State not found.")
            return False

        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                local_state = json.load(f)
            key_bytes = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
            master_key = dpapi_decrypt(key_bytes)
            aesgcm = AESGCM(master_key)

            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name
            shutil.copy2(cookie_path, tmp_path)

            conn = sqlite3.connect(tmp_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name, encrypted_value, host_key, path, is_secure, is_httponly, samesite, expires_utc "
                "FROM cookies WHERE host_key LIKE '%facebook.com%'"
            )
            rows = cursor.fetchall()
            conn.close()
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

            decrypted_cookies = []
            same_site_map = {-1: "None", 0: "None", 1: "Lax", 2: "Strict"}
            for name, enc_val, host_key, path, is_secure, is_httponly, samesite, expires_utc in rows:
                try:
                    if enc_val.startswith(b"v10") or enc_val.startswith(b"v11"):
                        nonce = enc_val[3:15]
                        ciphertext = enc_val[15:]
                        val = aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8", errors="ignore")
                    else:
                        val = dpapi_decrypt(enc_val).decode("utf-8", errors="ignore")

                    expires = (expires_utc / 1000000) - 11644473600 if expires_utc > 0 else -1
                    decrypted_cookies.append({
                        "name": name,
                        "value": val,
                        "domain": host_key,
                        "path": path,
                        "expires": expires,
                        "httpOnly": bool(is_httponly),
                        "secure": bool(is_secure),
                        "sameSite": same_site_map.get(samesite, "None"),
                    })
                except Exception:
                    pass

            has_c_user = any(c["name"] == "c_user" for c in decrypted_cookies)
            if not has_c_user:
                print("[WARNING] Could not find 'c_user' cookie in Chrome profile. Are you logged in on facebook.com?")
                return False

            state = {
                "cookies": decrypted_cookies,
                "origins": [{"origin": "https://www.facebook.com", "localStorage": []}]
            }
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

            c_user_val = [c["value"] for c in decrypted_cookies if c["name"] == "c_user"][0]
            print(f"[SUCCESS] Successfully imported {len(decrypted_cookies)} Facebook cookies directly from Chrome!")
            print(f"Logged in Facebook User ID: {c_user_val}")
            print(f"Session saved to {self.state_path}!")
            return True
        except Exception as e:
            print(f"[ERROR] Failed importing cookies from Chrome: {e}")
            return False

    def get_context(self, playwright_instance, headless: bool = False) -> BrowserContext:
        """Creates a browser context with restored session state or persistent profile."""
        if self.state_path.exists():
            try:
                browser = playwright_instance.chromium.launch(
                    channel="chrome",
                    headless=headless,
                    args=STEALTH_ARGS,
                    ignore_default_args=["--enable-automation"]
                )
            except Exception:
                browser = playwright_instance.chromium.launch(
                    headless=headless,
                    args=STEALTH_ARGS,
                    ignore_default_args=["--enable-automation"]
                )

            context = browser.new_context(
                storage_state=str(self.state_path),
                viewport={"width": 1280, "height": 900},
                locale="sv-SE",
                user_agent=USER_AGENT,
            )
            context.add_init_script(STEALTH_INIT_SCRIPT)
            return context

        # Fallback to persistent profile if no saved state file
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        try:
            context = playwright_instance.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                channel="chrome",
                headless=headless,
                args=STEALTH_ARGS,
                ignore_default_args=["--enable-automation"],
                viewport={"width": 1280, "height": 900},
                locale="sv-SE",
                user_agent=USER_AGENT,
            )
        except Exception:
            context = playwright_instance.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=headless,
                args=STEALTH_ARGS,
                ignore_default_args=["--enable-automation"],
                viewport={"width": 1280, "height": 900},
                locale="sv-SE",
                user_agent=USER_AGENT,
            )

        context.add_init_script(STEALTH_INIT_SCRIPT)
        return context
