# Item Trading Bot (Tradera -> Blocket Sync)

An automated cross-listing utility designed to fetch active articles from **Tradera** ([ODENPLAN SALES](https://www.tradera.com/profile/items/2195678/odenplan-sales)) and draft matching listings on **Blocket.se**.

---

## Features
- **Tradera Scraper**: Automatically retrieves all active items, descriptions, attributes (size, brand, condition), and high-resolution images.
- **Smart Pricing**: Translates Tradera Buy-Now ("Köp nu") prices to Blocket fixed prices with fallback to auction starting bids.
- **SQLite Sync Database**: Tracks discovered, drafted, and published items to guarantee idempotency and avoid duplicates.
- **Cloud Draft Engine**: Automatically populates Blocket ad forms with high-resolution photos and copy, and triggers cloud persistence to your account (**Mitt Blocket -> Mina annonser -> Utkast**) for instant acceptance in the Blocket mobile app.
- **Interactive CLI**: Easy terminal commands to discover, inspect, and draft items.

---

## Quickstart

### 1. Requirements
- Python 3.10+
- Chrome / Chromium

### 2. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Usage

#### 🚀 One-Click Pipeline (Recommended)
Automatically checks authentication, fetches newly posted items from Tradera, and batch-drafts all unsynced items directly into your Blocket cloud drafts:
```bash
# Run full pipeline
python -m src.cli sync

# Or run in background (headless)
python -m src.cli sync --headless

# Or sync next 5 items
python -m src.cli sync --limit 5
```

#### Granular Commands (Optional)
```bash
# 1. Discover Active Items on Tradera
python -m src.cli fetch

# 2. List Items & Sync Status
python -m src.cli list

# 3. Login to Blocket (One-time session save)
python -m src.cli login
```


#### Draft Items to Blocket (Ready for Acceptance in Mobile App)
```bash
# Draft a specific item directly to your Blocket account
python -m src.cli draft --item-id 756934350

# Draft next 5 items in batch to review in Blocket app
python -m src.cli draft --limit 5

# Draft all unsynced items
python -m src.cli draft --all

# Optional: Inspect in desktop browser before saving
python -m src.cli draft --item-id 756934350 --pause
```


---

## Documentation
- [docs/goal.md](docs/goal.md) — Project vision, requirements, and constraints.
- [docs/roadmap.md](docs/roadmap.md) — Phased delivery plan.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Subsystems, data pipelines, and execution flows.
- [docs/CODEMAP.md](docs/CODEMAP.md) — Directory layout and code symbol index.
- [docs/DECISIONS.md](docs/DECISIONS.md) — Architectural decision records (ADRs).
