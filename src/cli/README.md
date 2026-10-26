# Command-Line Interface (CLI)

The `src/cli/` package provides the primary user interface and execution entry point for the Item Trading Bot.

---

## Commands Reference

```bash
# General invocation
python -m src.cli <command> [options]
```

### 1. `sync` (One-Click Pipeline)
Runs the complete cross-listing workflow in a single command:
1. Fetches latest active inventory from Tradera.
2. Reconciles sold Tradera items (unlisting from Blocket and Facebook).
3. Drafts/publishes newly discovered items to the target platform.

```bash
# Sync both Blocket and Facebook
python -m src.cli sync --target all

# Sync only Blocket (default)
python -m src.cli sync --target blocket

# Run silently in background
python -m src.cli sync --target all --headless
```

---

### 2. `sync-sold` (Sold Item Reconciliation)
Detects items sold on Tradera and unlists them from Blocket (both **Aktiva** live ads and **Utkast** drafts) and Facebook Marketplace:

```bash
# Preview what would be unlisted without touching listings
python -m src.cli sync-sold --dry-run

# Execute unlisting in background
python -m src.cli sync-sold --headless
```

---

### 3. `dedupe` (Inventory Deduplication & Relist Scanner)
Scans tracked items for duplicate postings and relists:

```bash
# Scan and display duplicate clusters
python -m src.cli dedupe

# Automatically merge duplicates into primary listing and preserve statuses
python -m src.cli dedupe --merge
```

---

### 4. `list` (Inventory Status Table)
Displays a rich terminal table showing all tracked items, prices, photo counts, and multi-platform sync states (`discovered`, `drafted`, `published`, `sold`).

```bash
python -m src.cli list
```

---

### 5. `fetch` (Discover Active Inventory)
Retrieves active items directly from the Tradera seller profile and refreshes local SQLite database records.

```bash
python -m src.cli fetch
```

---

### 6. `login` & `fb-login` (Authentication Setup)
- **`python -m src.cli login`**: Opens a visible browser to authenticate once on Blocket via BankID/email.
- **`python -m src.cli fb-login`**: Opens an interactive browser profile or imports cookies for Facebook Marketplace.

---

### 7. `draft` & `publish` (Blocket Automation)
- **`python -m src.cli draft --all`**: Batch-drafts unsynced items to Blocket cloud drafts (*Utkast*).
- **`python -m src.cli publish --item-id <id>`**: Directly publishes an ad to Blocket *Aktiva*.
- **`python -m src.cli clean-drafts`**: Bulk-deletes all drafts from the Blocket account.

---

### 8. `fb-draft` (Facebook Marketplace Automation)
- **`python -m src.cli fb-draft --all --publish`**: Batch-publishes unsynced items to Facebook Marketplace.
