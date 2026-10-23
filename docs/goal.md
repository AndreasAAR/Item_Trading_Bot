# Project Goal: Tradera-to-Blocket Item Sync Bot

## 1. High-Level Objective
Create an automated cross-listing utility that fetches active articles posted by **"ODENPLAN SALES"** on [Tradera](https://www.tradera.com/profile/items/2195678/odenplan-sales) and synchronizes them to [Blocket](https://www.blocket.se/) under the user's account (`andreas.ahrlund@gmail.com`).

## 2. Core Capabilities
1. **Tradera Scraper & Extractor**:
   - Fetches all active listings from the public profile.
   - For each listing, extracts:
     - Item ID, Title, Description
     - Images in high resolution (`img.tradera.net/large-fit/...`)
     - Category and item attributes (Brand, Size, Condition, Material, etc.)
     - Pricing: Buy-Now price ("Köp nu") with fallback to starting auction price ("Utropspris").
     - Shipping and pickup parameters.

2. **Sync State Management**:
   - SQLite-backed local tracking database (`data/sync_store.db`).
   - Tracks item IDs, Tradera hash/updated timestamp, Blocket ad status (`pending`, `drafted`, `published`, `ignored`), and Blocket ad URL/ID.
   - Prevents duplicate postings and enables re-running sync safely.

3. **Semi-Automated Blocket Poster**:
   - Uses Playwright browser automation with persistent session state (profile / cookies) to maintain login without repeated credential entries.
   - Navigates to Blocket's "Ny annons" (create listing) flow.
   - Fills in ad details: Title, Description, Category suggestion/selection, Price, and uploads high-resolution images.
   - Saves or leaves the ad in a ready-to-review draft state for the user to verify, choose shipping/Blocketpaket options, and confirm/publish.

4. **Interactive CLI / Dashboard**:
   - Command-line interface to:
     - Fetch/refresh Tradera listings.
     - Inspect pending vs synced items.
     - Trigger drafting of selected or all unsynced items on Blocket.
     - Manually override price or category if desired.
