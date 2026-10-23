import json
from pathlib import Path
from playwright.sync_api import sync_playwright, BrowserContext
from config.settings import BLOCKET_AUTH_STATE_PATH, BLOCKET_BASE_URL

class BlocketSessionManager:
    def __init__(self, state_path: Path = BLOCKET_AUTH_STATE_PATH):
        self.state_path = state_path

    def has_saved_session(self) -> bool:
        return self.state_path.exists() and self.state_path.stat().st_size > 50

    def interactive_login(self, email: str = "andreas.ahrlund@gmail.com") -> bool:
        """Opens a visible browser for the user to log in with Schibsted/BankID, then saves storage state."""
        print(f"\nOpening browser to log into Blocket as {email}...")
        print("Please complete the login in the browser window.")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                locale="sv-SE",
            )
            page = context.new_page()
            login_url = "https://www.blocket.se/auth/login?redirectUrl=https%3A%2F%2Fwww.blocket.se"
            page.goto(login_url)

            input("\n>>> Once you are fully logged in and see your Blocket account page, press [ENTER] here to save session: ")


            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(self.state_path))
            print(f"Session saved successfully to {self.state_path}!")
            browser.close()
            return True

    def get_context(self, playwright_instance, headless: bool = False) -> BrowserContext:
        """Creates a browser context with restored session state if available."""
        browser = playwright_instance.chromium.launch(headless=headless)
        if self.has_saved_session():
            return browser.new_context(
                storage_state=str(self.state_path),
                viewport={"width": 1280, "height": 900},
                locale="sv-SE",
            )
        return browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="sv-SE",
        )
