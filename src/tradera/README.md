# Tradera Sourcing & Ingestion Subsystem

The `src/tradera/` package handles discovering, scraping, and parsing active seller inventory from Tradera into structured domain models.

---

## Architecture & Modules

```
src/tradera/
├── __init__.py
├── client.py     # Network client with rate-limiting & session management
├── models.py     # Domain models for item cards & full detailed listings
└── parser.py     # HTML & JSON-LD parser extracting metadata, attributes & photos
```

### 1. `client.py` (`TraderaClient`)
- **`get_profile_items(profile_url)`**: Fetches the public seller profile page (e.g., `ODENPLAN SALES`, ID `2195678`) and extracts all active item cards.
- **`get_item_detail(item_url)`**: Fetches an individual listing page with a gentle delay (default 0.2s–0.5s) to avoid triggering rate limits.

### 2. `models.py`
- **`TraderaItemCard`**: Lightweight card model containing `item_id`, `title`, `url`, `thumbnail_url`, `leading_bid`, `starting_price`, `buy_now_price`, and `category_id`.
- **`TraderaItemDetail`**: Full item schema including high-res image URLs (`images`), full description, attribute dictionary (brand, size, color, condition, material), shipping cost, pickup availability, and computed `target_blocket_price`.

### 3. `parser.py` (`TraderaParser`)
- **Profile Card Parser**: Extracts items from `[data-item-card-id]` attributes and parses prices.
- **Detail Page Parser**:
  - **Photos**: Converts thumbnail/medium URLs to high-res `large-fit` images (`img.tradera.net/.../large-fit/...`) and deduplicates by image content hash.
  - **Attributes**: Combines breadcrumb hierarchy links, filter query parameters (`af-` links), JSON-LD `Product` schema, and title heuristics to extract brand, size, color, condition, and material.
  - **Prices**: Detects Buy Now (*Köp nu*) vs auction starting bids and shipping costs.

---

## Usage Example

```python
from src.tradera.client import TraderaClient

client = TraderaClient()
cards = client.get_profile_items()
print(f"Found {len(cards)} active items on Tradera profile.")

detail = client.get_item_detail(cards[0].url)
print(f"Title: {detail.title} | Price: {detail.target_blocket_price} SEK")
print(f"Images: {len(detail.images)} | Brand: {detail.attributes.get('brand')}")
```
