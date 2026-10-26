# Sold Item Reconciliation Subsystem

The `src/reconciliation/` package orchestrates multi-platform unlisting when items sell on Tradera (and handles bidirectional synchronization).

---

## Architecture & Modules

```
src/reconciliation/
├── __init__.py
└── sold_checker.py   # SoldReconciler: Tradera sold detection & multi-channel unlisting
```

### 1. `sold_checker.py` (`SoldReconciler`)
Coordinates the end-to-end unlisting workflow across platforms:

1. **Profile Delta Comparison**:
   - Compares active listings on the public seller profile (`TraderaClient.get_profile_items()`) against non-sold database inventory.
   - Any item present on the profile is actively for sale and immediately skipped.

2. **Sold Signal Verification**:
   - For items missing from the active profile, fetches the live Tradera listing URL:
   - **Genuine Sales**: Matched by `såld med köp nu` (Buy Now), `vann auktionen` (Winning Bidder), `slutpris`, or `vinnande bud`.
   - **Expired / Relisting Candidates**: If marked `avslutades utan bud` (ended without bids) or `avslutades utan köp`, the item is **not** treated as sold, preserving the user's active listings on external marketplaces.

3. **Multi-Channel Unlisting**:
   - For all confirmed sold items:
     - Calls `BlocketUnlister.unlist_items()` to remove both live ads (**`Aktiva`**) and saved drafts (**`Utkast`**).
     - Calls `FacebookUnlister.unlist_items()` to delete the listing from the Marketplace seller dashboard.
     - Updates SQLite database to `status='sold'` and `facebook_status='sold'`, and writes audit entries to `sync_logs`.

---

## CLI Integration

- **Dry-run mode (safe preview)**:
  ```bash
  python -m src.cli sync-sold --dry-run
  ```
- **Live execution**:
  ```bash
  python -m src.cli sync-sold --headless
  ```
- **Integrated into Daily Sync**: Executed automatically on every scheduled daily sync before drafting new items.
