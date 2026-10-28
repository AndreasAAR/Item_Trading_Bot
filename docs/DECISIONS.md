# Architectural Decision Records (ADRs)

## ADR-001: Cloud Draft Mode & Mobile App Acceptance
- **Status**: Accepted
- **Context**: Blocket listings often require BankID verification or category package selection. Publishing directly via bot can cause unintended listing charges or bot verification blocks. Additionally, the user prefers reviewing and confirming drafts on their mobile phone via the official Blocket app.
- **Decision**: The bot operates in **cloud draft mode**. It fills in all listing fields, uploads high-resolution images, and triggers Blocket's server-side draft save by advancing to the summary review step. The draft is persisted to the user's Schibsted/Blocket account (**Mitt Blocket -> Mina annonser -> Utkast**).
- **Consequences**:
  - Eliminates 95% of tedious data entry and photo uploading.
  - Allows the user to open the **Blocket Mobile App** on their phone and publish each listing with BankID with a single tap whenever convenient.
  - Leaves complete control in the seller's hands.


---

## ADR-002: Pricing Strategy (Buy-Now with Starting Bid Fallback)
- **Status**: Accepted
- **Context**: Tradera listings often consist of auctions with a starting bid (e.g. 1 kr or 50 kr) alongside a Buy-Now ("Köp nu") price. Blocket only uses fixed pricing.
- **Decision**: If a Tradera item has a "Köp nu" price, that value is used as the Blocket fixed price. If only an auction starting bid exists, the starting bid is used as default, with the option for the user to override it in CLI before drafting.
- **Consequences**: Accurately reflects the seller's valuation without manual calculation for Buy-Now items, while handling pure auctions safely.

---

## ADR-003: SQLite-Backed Sync State Tracking
- **Status**: Accepted
- **Context**: Running synchronization repeatedly should be idempotent, never creating duplicate ads on Blocket and remembering previously drafted items.
- **Decision**: Use a zero-dependency local SQLite database (`data/sync_store.db`) containing item IDs, title, price, timestamps, and status flags (`discovered`, `pending`, `drafted`, `published`, `ignored`).
- **Consequences**: Fast, reliable, local storage without external database services. Can be easily inspected or reset.

---

## ADR-004: Python + Playwright Framework
- **Status**: Accepted
- **Context**: Blocket is a modern Single Page Application (SPA) with anti-scraping protections. Tradera uses Next.js server-side streaming.
- **Decision**: Build the application in Python using `requests` and `BeautifulSoup4` for high-speed public Tradera scraping, and `Playwright` for robust Chromium-based Blocket browser automation.
- **Consequences**: Scrapes Tradera in seconds without browser overhead, while leveraging full browser capabilities with stored cookies for Blocket.

---

## ADR-005: Lightweight Multi-Platform HTTP Profile Diff Listener (`watch`)
- **Status**: Accepted
- **Context**: None of the three platforms offer simple consumer webhooks for personal seller accounts. Launching full Playwright browsers on a frequent polling schedule wastes CPU/RAM and increases bot-detection risk.
- **Decision**: Poll all three platforms via lightweight HTTP requests (`requests` with saved session cookies):
  - **Tradera**: Public profile HTML (`GET /profile/items/...`) + item page sold markers.
  - **Blocket**: Authenticated internal JSON summary API (`GET /my-items/api/summary?facet=ACTIVE|DISPOSED|INACTIVE|DRAFT`).
  - **Facebook Marketplace**: Authenticated SSR Relay JSON extraction on `/marketplace/you/selling`.
  Playwright browsers are only launched when an actionable diff (new listing or sale) is detected that requires updating the other two platforms.
- **Consequences**: Full 3-platform diff checks complete in ~2–5 seconds with zero browser overhead until a real change occurs.
