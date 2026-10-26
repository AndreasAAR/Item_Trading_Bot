# Facebook Marketplace Automation Subsystem

The `src/facebook/` package automates cross-listing and unlisting on Facebook Marketplace using Playwright with anti-detection evasions.

---

## Architecture & Modules

```
src/facebook/
├── __init__.py
├── session.py    # Persistent profile & stealth bypass context
├── drafter.py    # Automated listing creation on /marketplace/create/item
└── unlister.py   # Deletes or marks sold listings on /marketplace/you/selling
```

### 1. `session.py` (`FacebookSessionManager`)
- **Anti-Detection Configuration**: Uses persistent Chromium storage (`data/fb_chrome_profile`), `--disable-blink-features=AutomationControlled`, and mock navigator properties (`webdriver=undefined`, `plugins`, `languages`) to bypass Arkose Labs MatchKey bot challenges.
- **`interactive_login()`**: Launches a visible browser for one-time login and saves authenticated session cookies (`data/fb_auth_state.json`).
- **`import_cookies_from_chrome()`**: Allows direct export/import of cookies using CDP on port 9222.

### 2. `drafter.py` (`FacebookDrafter`)
- **`draft_item(item, publish=True)`**: Navigates to `https://www.facebook.com/marketplace/create/item`.
  - Attaches multi-image photo sets via file input.
  - Fills Title, Price, Category chip, Condition dropdown, and formatted description.
  - Clicks `Next` -> selects Marketplace audience -> submits or saves draft.
- **`draft_batch(items, delay_between=15.0)`**: Executes paced batch publishing with safe 15-second rest delays.

### 3. `unlister.py` (`FacebookUnlister`)
- **`unlist_items(target_titles)`**: Navigates to `https://www.facebook.com/marketplace/you/selling`, searches for the listing card by title, clicks `...` -> selects `Ta bort annons` (*Delete listing*) -> chooses reason *"Sålde någon annanstans"* (*Sold elsewhere*) -> confirms deletion.

---

## Usage Example

```python
from src.facebook.session import FacebookSessionManager
from src.facebook.unlister import FacebookUnlister

# Unlist sold item from Facebook Marketplace
unlister = FacebookUnlister()
success = unlister.unlist_item("Uniqlo x Theory svart kavaj, storlek M", headless=True)
print(f"Removed from Facebook: {success}")
```
