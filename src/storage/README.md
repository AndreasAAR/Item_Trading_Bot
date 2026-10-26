# Storage, State Machine & Deduplication Subsystem

The `src/storage/` package provides persistent state storage, relist recognition, duplicate clustering, and audit logging for all tracked inventory.

---

## Architecture & Modules

```
src/storage/
├── __init__.py
├── database.py     # SQLite connection handling & schema initialization
├── dedupe.py       # Title normalization, fuzzy matching & duplicate clustering
└── repository.py   # State machine, relist handling & CRUD operations
```

### 1. `database.py`
- Manages the local SQLite database at `data/sync_store.db`.
- **`items` Table**: Stores item ID, titles, URLs, descriptions, prices, image arrays (JSON), attribute dictionaries (JSON), Blocket status (`discovered`, `drafted`, `published`, `sold`), and Facebook status (`discovered`, `drafted`, `published`, `sold`).
- **`sync_logs` Table**: Records structured audit events with action, status, item ID, and timestamps.

### 2. `dedupe.py`
- **`normalize_title(title)`**: Strips sizing, conditions, brands, noise punctuation, and converts Swedish characters to standard forms for robust comparison.
- **`title_similarity(t1, t2)`**: Computes sequence matcher similarity ratio between two titles.
- **`find_matching_existing_item(item_title, item_images, existing_items)`**:
  - Checks for exact title matches (>90% similarity).
  - Checks for matching image signature sets (e.g., matching image filenames/hashes across relists).
- **`find_all_duplicates(items)`**: Clusters all existing inventory into primary listings and duplicate variants.

### 3. `repository.py` (`SyncRepository`)
- **`upsert_item_detailed(item)`**:
  - If exact `item_id` exists: updates details and prices (`outcome='updated'`).
  - If item matches an existing item by title or image signatures: detects it as a **relist** (`outcome='relisted'`), updates the Tradera ID and URLs, but **preserves** the existing Blocket and Facebook sync statuses so the item is never duplicated!
  - If item is brand new: inserts with status `discovered` (`outcome='new'`).
- **`merge_duplicate_items(primary_id, duplicate_id)`**: Merges duplicate records in SQLite, retaining the highest progressed platform status and deleting redundant records.

---

## Usage Example

```python
from src.storage.repository import SyncRepository

repo = SyncRepository()

# List items ready for Blocket drafting
unsynced = repo.list_items(status="discovered", platform="blocket")
print(f"Found {len(unsynced)} discovered items.")

# Scan for duplicates
duplicates = repo.find_all_duplicates()
print(f"Found {len(duplicates)} duplicate cluster(s).")
```
