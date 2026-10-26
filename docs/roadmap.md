# Project Roadmap: Tradera to Blocket Sync Bot

This document outlines the sequential phases of development, tracking current progress and upcoming deliverables.

---

## Phase 1: Planning, Documentation & Environment Setup
- [x] Gather requirements (Target profiles, pricing rules, sync strategy, automation mode).
- [x] Create core documentation (`goal.md`, `roadmap.md`, `ARCHITECTURE.md`, `CODEMAP.md`, `DECISIONS.md`, `README.md`).
- [x] Set up project structure (`src/`, `tests/`, `config/`, `data/`).
- [x] Install dependencies (`playwright`, `beautifulsoup4`, `requests`, `pydantic`, `rich`).
- [x] Initialize Playwright browsers (`playwright install chromium`).

---

## Phase 2: Tradera Scraper & Data Extractor
- [x] Implement `TraderaClient` to fetch active listings from profile (`odenplan-sales`, ID `2195678`).
- [x] Implement item parser to extract:
  - Title, full description, category ID / slug.
  - High-res images (`img.tradera.net/large-fit/...`).
  - Attributes: brand, size, color, condition, material.
  - Pricing logic: Buy-Now price with fallback to starting auction bid.
- [x] Add unit tests and local snapshot tests for parsing accuracy.
- [x] Live profile verification (Successfully fetched all 37 active items).

---

## Phase 3: SQLite Sync Storage & State Tracker
- [x] Design schema for `sync_store.db`:
  - `items`: item ID, title, price, images, attributes, status (`discovered`, `pending`, `drafted`, `published`, `ignored`).
  - `sync_logs`: timestamps, actions taken, errors, Blocket ad IDs / URLs.
- [x] Implement `SyncRepository` with CRUD and idempotency guarantees.
- [x] Verify duplicate runs update existing items without reverting draft/publish status.

---

## Phase 4: Blocket Category & Field Mapper
- [x] Build category mapper with dictionary and keyword heuristics (`src/mapper/category_mapper.py`).
- [x] Format descriptions cleanly for Blocket with item details and pickup notes (`src/mapper/formatter.py`).
- [x] Build high-resolution image downloader for staging uploads (`src/mapper/image_downloader.py`).

---

## Phase 5: Playwright Blocket Automation (Cloud Draft Engine)
- [x] Implement session manager to store and reuse Blocket authentication state (`data/blocket_auth_state.json`).
- [x] Implement interactive login helper (`src/blocket/session.py`).
- [x] Build listing drafter with form population, image upload, and cloud draft persistence (`src/blocket/drafter.py`).
- [x] Integrate cloud save so drafts appear in **Mitt Blocket -> Mina annonser -> Utkast** for mobile app acceptance.
- [x] User testing with active Blocket account.

---

## Phase 6: CLI & Workflow Orchestration
- [x] Build user-friendly CLI (`python -m src.cli`):
  - `sync`: Unified one-click pipeline (fetch Tradera & batch-draft all unsynced items into Blocket drafts).
  - `fetch`: Fetch latest Tradera items and update DB.
  - `list`: View discovered items, pricing, and sync status.
  - `login`: Open browser to authenticate with Blocket and save session.
  - `draft [--item-id <id> | --all]`: Launch browser automation to draft ads on Blocket.
  - `set-price <id> <price>`: Manually override target price.
- [x] Pass automated test suite (`pytest`).
- [x] Live user dry run on first item.
- [x] Pipelined batch drafting in single continuous browser session.

---

## Phase 7: Full Attribute Bracket & Cloud Management
- [x] Extract full attributes from Tradera (breadcrumbs, query filter links, JSON-LD schema, title heuristics).
- [x] Deep 3-level Blocket category mapping (main, sub, product).
- [x] Map Skick / Condition, Färg / Color, Passform / Fit ("Normal i storleken" default).
- [x] Map trail & running shoes to `Sport och friluftsliv` -> `Träningskläder och skor`.
- [x] Auto-fill text attributes (Storlek, Varumärke, Material).
- [x] Blocket cloud draft purging tool (`clean-drafts` in `src/blocket/cleaner.py`).
## Phase 8: Facebook Marketplace Integration
- [x] Create Facebook session manager (`src/facebook/session.py`) and auth state storage (`data/fb_auth_state.json`).
- [x] Database migration: multi-platform tracking (`facebook_status`, `facebook_ad_url`).
- [x] Facebook category and condition mapper (`src/mapper/fb_category_mapper.py`).
- [x] Facebook Marketplace ad creation automation (`src/facebook/drafter.py`).
- [x] CLI integration: `fb-login`, `fb-draft`, and multi-target `sync --target [blocket|facebook|all]`.
- [x] Automated test suite for Facebook mapping and formatting (`tests/test_fb_mapper.py`).

---

## Phase 9: Relist Detection & Deduplication Engine
- [x] Title normalization and tokenization (`src/storage/dedupe.py`).
- [x] Fuzzy string similarity matching (>90% threshold) using `SequenceMatcher`.
- [x] Image signature hashing for visual verification of relisted items.
- [x] Auto-updating repository relist handler: preserves `drafted` and `published` platform statuses when items relist under new Tradera IDs.
- [x] Duplicate clustering and CLI merge utility (`python -m src.cli dedupe [--merge]`).
- [x] 18 unit tests in `tests/test_dedupe.py`.

---

## Phase 10: Multi-Channel Sold Reconciliation & Unlisting
- [x] Tradera sold detection: distinguishes genuine sales (`såld med köp nu`, `vann auktionen`, `slutpris`) from expired auctions (`avslutades utan bud`).
- [x] Blocket double-tab unlisting: checks both **Aktiva** (live listings) and **Utkast** (drafts).
- [x] Safe active listing removal: uses 3-dots action menu (`...` -> `Ta bort` -> confirm modal) to bypass Blocket's conversation requirement.
- [x] Facebook Marketplace unlisting (`src/facebook/unlister.py`).
- [x] Full reconciliation pipeline (`src/reconciliation/sold_checker.py`).
- [x] CLI integration: `python -m src.cli sync-sold [--dry-run]` and automatic daily sync execution.
- [x] Automated unit tests in `tests/test_unlister.py`.

---

## Phase 11: Bidirectional Sold Sync (Blocket & Facebook ➔ Tradera)
- [x] Create `TraderaSessionManager` and interactive/manual cookie import (`tradera-login [--cookies|--trd-at]`).
- [x] Implement Blocket `Avslutade` sales detector (`get_ended_sold_titles()`).
- [x] Implement `TraderaUnlister` (`src/tradera/unlister.py`):
  - Primary flow: navigates to **Aktiva annonser** (`https://www.tradera.com/my/listings`), locates listing by formatted item ID or title, clicks **Mer** ➔ **Avsluta annons**.
  - Secondary fallback: direct item page with top seller banner (`Visa alternativ` ➔ `Avsluta`).
  - Batching: `end_listings()` shares single browser context across items.
- [x] Wire bidirectional reconciliation (`reconcile_all()`) into `sync-sold` and daily sync.
- [x] Integrated into GitHub Actions daily workflow (`.github/workflows/daily_sync.yml`) with `TRADERA_AUTH_STATE` secret restoration.
- [x] Comprehensive unit tests in `tests/test_unlister.py` (29 passed).

---

## Phase 12: Full-Spectrum Pricing Ladder (-30% to +30%) & Visual Image Rotation
- [x] Implemented **5-Phase Anti-Spam Pricing Ladder** (`src/pricing/ladder.py`):
  - `Step 0: Premium Anchor (+30%)`: Initial listing price above baseline.
  - `Step 1: Premium Buffer`: Same price, zero notifications sent.
  - `Step 2: Baseline Drop`: Dips to baseline price, triggering marketplace "Prissänkt" push alert #1.
  - `Step 3: Baseline Buffer`: Same price, zero notifications sent.
  - `Step 4: Bargain Floor (-30%)`: Dips to minimum floor, triggering clearance "Prissänkt" push alert #2.
  - Wraps back to `Step 0` upon next relist, creating buyer FOMO that the promotional discount ended.
- [x] **Digit-9 Rounding Rule** (`round_to_nine`):
  - All calculated prices round down to end with digit `9` (e.g. 455 -> 449 kr, 350 -> 349 kr, 245 -> 239 kr, 149 -> 99 kr).
  - Hard minimum floor enforced (default 59 kr).
- [x] **Visual Thumbnail Rotation**:
  - `cover_image_index` increments on each relist cycle.
  - Rotates primary upload photo for Blocket (`src/blocket/drafter.py`) and Facebook (`src/facebook/drafter.py`) to give fresh visual appeal.
  - Preserves canonical Tradera image URLs in SQLite, maintaining 100% deduplication accuracy.
- [x] **Database & Repository Integration** (`src/storage/database.py`, `src/storage/repository.py`):
  - Migrated schema with `base_price`, `floor_price`, `cover_image_index`, `relist_count`, `pricing_phase`, `ladder_step`, `last_price_change_at`, `last_relisted_at`.
  - Automatic ladder progression on relist detection in `upsert_item_detailed`.
- [x] **CLI Subcommands** (`src/cli/main.py`):
  - `python -m src.cli ladder`: Rich table showing items, current phase, target price, next transition, and image index.
  - `python -m src.cli advance-ladder [--item-id ID | --all]`: Advance ladder stages and rotate cover photo.
  - `python -m src.cli set-floor <ID> <PRICE>`: Set custom price floor (auto-rounded down to 9).
- [x] **Automated Test Suite**:
  - 36 total unit tests passing (`tests/test_pricing_ladder.py`, `tests/test_storage.py`, `tests/test_dedupe.py`, `tests/test_unlister.py`).

---

## Phase 13: Tradera 'Dolda' (Hidden) Reconciliation & Permanent Sold Protection
- [x] **Tradera 'Dolda' Scraper** (`TraderaUnlister.get_hidden_listings` in `src/tradera/unlister.py`):
  - Navigates to `https://www.tradera.com/my/listings?tab=hidden`.
  - Extracts all item IDs and titles that have been moved to the hidden list by the seller.
- [x] **Cross-Platform Auto-Unlisting & Reconciliation** (`reconcile_hidden_items` in `src/reconciliation/sold_checker.py`):
  - Automatically reconciles hidden Tradera items against local database inventory.
  - Automatically unlists any active/drafted ads on Blocket and Facebook Marketplace.
  - Permanently updates local DB status to `sold` across all platforms (`status='sold'`, `facebook_status='sold'`).
- [x] **Strict Sold/Restart Guard** (`SyncRepository` in `src/storage/repository.py`):
  - `upsert_item_detailed`: If an incoming listing matches an item marked as `sold`, it is permanently ignored (`outcome="ignored_sold"`). It will **never** be relisted, restarted, or resurrected.
  - `advance_item_ladder`: Explicitly rejects advancing ladder or prices on any item with `status="sold"`.
  - Added repository helper `mark_item_sold(item_id, reason)` with audit logging in `sync_logs`.
- [x] **CLI Integration** (`src/cli/main.py`):
  - `python -m src.cli mark-sold <item_id> [--reason REASON]`: Manually mark any item as permanently sold.
  - `python -m src.cli sync-sold`: Reconciles Tradera sales, Tradera Dolda hidden items, and Blocket sales.
- [x] **Automated Test Suite**:
  - 38 unit tests passing across all test modules (`tests/test_unlister.py`, `tests/test_pricing_ladder.py`, etc.).





