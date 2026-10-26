# Taxonomy, Formatting & Image Staging Subsystem

The `src/mapper/` package transforms raw Tradera item schemas into structured, marketplace-specific listing payloads for Blocket.se and Facebook Marketplace.

---

## Architecture & Modules

```
src/mapper/
├── __init__.py
├── category_mapper.py    # Blocket 3-level taxonomy, conditions & color normalization
├── fb_category_mapper.py # Facebook Marketplace category, condition & copy mapper
├── formatter.py          # Ad copy composer, pricing resolution & pickup notes
└── image_downloader.py   # Secure concurrent high-res image downloader
```

### 1. `category_mapper.py`
- Maps Tradera category paths, breadcrumbs, and item titles to Blocket's 3-level recommerce taxonomy:
  - `Huvudkategori` (e.g. `Personligt`, `Sport och friluftsliv`, `För hemmet`)
  - `Underkategori` (e.g. `Kläder och skor`, `Hemelektronik och vitvaror`)
  - `Produktkategori` (e.g. `Tröjor och stickat`, `Skjortor`, `Kavajer och kostymer`, `Jackor och ytterplagg`, `Träningskläder och skor`)
- **`map_condition(condition_str)`**: Maps raw condition strings to Blocket standard chips (`Nytt`, `Nyskick`, `Mycket bra skick`, `Bra skick`, `Okej skick`).
- **`map_color(color_str)`**: Maps diverse color names to Blocket standard palette.

### 2. `fb_category_mapper.py`
- Maps Tradera items to Facebook Marketplace standard categories (`Mäns kläder och skor`, `Sport och friluftsliv`, `Hushållsapparater`, etc.).
- Maps condition values to Facebook formats (`Nytt`, `Som nytt`, `Bra skick`, `Godtagbart skick`).

### 3. `formatter.py`
- **`format_blocket_payload(item)`**: Composes standardized listing descriptions including brand, condition, size, material, and standard local pickup text ("Finns att hämta nära Odenplan").
- **`resolve_target_price(buy_now_price, starting_price, leading_bid)`**: Computes optimal fixed listing price with fallback to starting auction bid.

### 4. `image_downloader.py`
- **`download_item_images(images, item_id)`**: Concurrently downloads high-resolution photos and stages them under `data/staged_images/<item_id>/` for fast browser upload.
