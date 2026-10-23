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


