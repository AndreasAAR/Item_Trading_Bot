# Diagnostic & Discovery Scratch Scripts

This directory houses the one-off diagnostic, inspection, and reverse-engineering scripts used during development to probe marketplace DOMs, verify session states, and test individual automation steps.

All stable, production-ready logic has been refactored into the primary `src/` modules.

---

## Directory Overview

### 1. `blocket/` (Blocket Automation Research)
- **`scratch_inspect_aktiva.py`**: Scans and parses active listing cards under the `Aktiva` tab on `https://www.blocket.se/my-items`.
- **`scratch_inspect_utkast.py`**: Scans and parses draft listing cards under the `Utkast` tab.
- **`scratch_inspect_my_items.py`**: General inspector for the Blocket `my-items` overview page and tab structures.
- **`scratch_inspect_menu_button.py`**: Analyzes the 3-dots action menu button structure (`w-button:has(w-icon[name="Dots"])`).
- **`scratch_inspect_modal_dom.py`**: Inspects the `<w-modal>` confirmation dialog DOM tree for deletion actions.
- **`scratch_inspect_blocket_fields.py` / `scratch_inspect_input_dom.py` / `scratch_inspect_textareas.py`**: Tests and validates form field selectors, input types, and textarea targets on the listing creation page.
- **`scratch_inspect_other_cats.py`**: Probes category-specific field requirements (e.g. clothing, furniture, electronics).
- **`scratch_test_fill_bracket.py`**: Test script for end-to-end form bracket filling and validation.
- **`scratch_test_delete_draft.py` / `scratch_test_confirm_delete.py` / `scratch_test_delete_one.py` / `scratch_test_delete_flow.py`**: Iterative test scripts for verifying targeted draft removal.
- **`scratch_test_mark_as_sold.py`**: Discovered that clicking "Markera som såld" without a Blocket chat thread fails, proving that `...` -> `Ta bort` is the required method for external unlisting.
- **`scratch_test_publish_flow.py`**: Tests the direct publish flow on Blocket.

*Production replacement*: `src/blocket/drafter.py`, `src/blocket/unlister.py`, `src/blocket/cleaner.py`.

---

### 2. `tradera/` (Tradera Extraction Research)
- **`scratch_inspect_tradera_attrs.py`**: Probes JSON-LD metadata, translation seed push events, and breadcrumbs on Tradera product pages.
- **`scratch_test_tradera_extraction.py`**: Tests attribute extraction, brand recognition, and size parsing logic against live item URLs.

*Production replacement*: `src/tradera/parser.py`, `src/tradera/client.py`.

---

### 3. `facebook/` (Facebook Marketplace Research)
- **`scratch_check_fb_cookies.py`**: Validates the presence and validity of `c_user` and `xs` session cookies.
- **`scratch_inspect_fb_selling.py`**: Probes the Facebook Marketplace seller dashboard (`/marketplace/you/selling`) for listing cards and action menus.

*Production replacement*: `src/facebook/session.py`, `src/facebook/drafter.py`, `src/facebook/unlister.py`.

---

### 4. `database/` (Data & Tracking Diagnostics)
- **`scratch_audit_db.py`**: Quick summary of database item statuses, prices, and platform sync mappings.
- **`scratch_view_attrs.py`**: Dumps attribute JSON schemas for existing database entries to verify taxonomy normalization.

*Production replacement*: `src/storage/repository.py`, `src/storage/dedupe.py`, `python -m src.cli list`.
