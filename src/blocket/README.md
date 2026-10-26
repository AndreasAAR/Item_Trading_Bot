# Blocket.se Automation Subsystem

The `src/blocket/` package automates browser interactions on Blocket.se using Playwright, handling session persistence, drafting, active ad unlisting, and cloud cleanup.

---

## Architecture & Modules

```
src/blocket/
├── __init__.py
├── session.py    # Persistent browser context, cookies & BankID login helper
├── drafter.py    # Form population for cloud drafts ('Utkast') & direct publishing
├── unlister.py   # Dual-tab unlisting engine for sold items ('Aktiva' & 'Utkast')
└── cleaner.py    # Bulk cleaner tool to purge cloud drafts
```

### 1. `session.py` (`BlocketSessionManager`)
- **`has_saved_session()`**: Checks if `data/blocket_auth_state.json` exists with valid authentication tokens.
- **`get_context(p, headless)`**: Creates a Chromium browser context pre-loaded with saved storage state, Swedish locale (`sv-SE`), and standard viewport.
- **`interactive_login()`**: Launches a visible head browser allowing the user to log in once via Schibsted / BankID and exports session tokens.

### 2. `drafter.py` (`BlocketDrafter`)
- **`draft_item(item, publish=False)`**: Navigates to the Blocket recommerce creation wizard (`/recommerce/create/<id>`).
  - Uploads multi-image photo sets.
  - Automatically selects 3-level category chips (`Huvudkategori` -> `Underkategori` -> `Produktkategori`).
  - Fills structured attribute fields: *Skick*, *Färg*, *Passform*, *Storlek*, *Varumärke*, *Material*, *Titel*, *Beskrivning*, *Pris*, and *Postnummer*.
  - Advances past step 1 to trigger server-side persistence in **Mitt Blocket -> Mina annonser -> Utkast**.
- **`draft_batch(items, publish=False)`**: Batch-drafts multiple listings with human-like rest delays.

### 3. `unlister.py` (`BlocketUnlister`)
- **`unlist_items(target_titles)`**: Unlists specified items by inspecting both:
  1. **`Aktiva` Tab (Live ads)**: Bypasses the broken "Markera som såld" flow (which fails if no Blocket chat thread exists) by clicking the 3-dots menu button (`...` / *"Meny till genvägar för annonsen"*) -> selects `Ta bort` (*Delete ad*) -> confirms in `<w-modal>`.
  2. **`Utkast` Tab (Drafts)**: Locates draft cards matching the title, opens `...`, clicks `Ta bort`, and confirms.
- **Fuzzy & Prefix Matching**: Handles Blocket's truncated headings (e.g., titles ending in `...`) via `is_title_match`.

### 4. `cleaner.py` (`BlocketDraftCleaner`)
- **`clean_all_drafts()`**: Automatically clicks through and purges all drafts from the Blocket account when a clean reset is needed.

---

## Usage Example

```python
from src.blocket.session import BlocketSessionManager
from src.blocket.unlister import BlocketUnlister

# Unlist a sold item from Blocket (checks both Aktiva and Utkast)
unlister = BlocketUnlister()
res = unlister.unlist_item("Uniqlo x Theory svart kavaj, storlek M", headless=True)
print(f"Removed from Blocket: {res['removed']}")
```
