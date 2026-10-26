# Repository Codemap

## 1. Directory Structure

```
Item_Trading_bot/
├── docs/
│   ├── ARCHITECTURE.md     # Subsystem designs, state machines, and execution flows
│   ├── CODEMAP.md          # File directory map and entry points
│   ├── DECISIONS.md        # Architectural decision records (ADRs)
│   ├── goal.md             # High-level project goals and requirements
│   └── roadmap.md          # Phased implementation plan and progress
├── config/
│   └── settings.py         # Configurable parameters (profile URLs, paths, selectors)
├── data/                   # Local data (SQLite db, sessions, staged images)
│   ├── sync_store.db       # Local SQLite tracking database
│   ├── blocket_auth_state.json # Saved Blocket Playwright session state
│   ├── fb_auth_state.json  # Saved Facebook session state
│   └── staged_images/      # Downloaded image files for uploading
├── scripts/                # Automated execution and maintenance scripts
│   ├── run_daily_sync.bat  # Daily scheduled execution script
│   ├── setup_windows_task.ps1 # PowerShell script to register Windows Scheduled Task
│   └── scratch/            # Organized diagnostic and reverse-engineering research scripts
│       ├── blocket/        # Blocket DOM, modal, and action menu tests
│       ├── tradera/        # Tradera metadata and attribute tests
│       ├── facebook/       # Facebook session and listing tests
│       └── database/       # Database inspection and attribute audit scripts
├── src/
│   ├── __init__.py
│   ├── cli/                # Command line interface commands
│   │   ├── __init__.py
│   │   └── main.py
│   ├── tradera/            # Tradera fetching, models, and parsing
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── models.py
│   │   └── parser.py
│   ├── storage/            # SQLite storage, repository, and deduplication engine
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── dedupe.py       # Title normalization, fuzzy matching & duplicate clustering
│   │   └── repository.py   # State machine, relist handling, and CRUD operations
│   ├── reconciliation/     # Cross-platform sold reconciliation pipeline
│   │   ├── __init__.py
│   │   └── sold_checker.py # Tradera sold detection & multi-channel unlisting orchestrator
│   ├── mapper/             # Data transformation & copy formatting
│   │   ├── __init__.py
│   │   ├── category_mapper.py    # Blocket 3-level category & attribute mapper
│   │   ├── fb_category_mapper.py # Facebook category, condition & copy mapper
│   │   ├── formatter.py          # Titles, descriptions, and pricing calculations
│   │   └── image_downloader.py   # Secure concurrent image downloader
│   ├── blocket/            # Blocket automation with Playwright
│   │   ├── __init__.py
│   │   ├── session.py      # Session persistence and stealth browser context
│   │   ├── drafter.py      # Form filler for cloud drafts (Utkast) and publishing
│   │   ├── unlister.py     # Targeted deletion of both active ads and saved drafts
│   │   └── cleaner.py      # Bulk draft cleaner for Blocket cloud account
│   └── facebook/           # Facebook Marketplace automation with Playwright
│       ├── __init__.py
│       ├── session.py      # Persistent profile & stealth bypass context
│       ├── drafter.py      # Automated listing creation and submission
│       └── unlister.py     # Deletes / marks sold listings on Facebook Marketplace
├── tests/                  # Unit and integration test suites
│   ├── test_tradera_parser.py
│   ├── test_storage.py
│   ├── test_mapper.py
│   ├── test_category_mapper.py
│   ├── test_fb_mapper.py
│   ├── test_fb_session.py
│   ├── test_dedupe.py      # 18 unit tests for fuzzy matching & duplicate merges
│   └── test_unlister.py    # Unlister title matching and sold reconciliation tests
├── AGENTS.md               # Repository navigation and agent guidelines
├── SKILL.md                # Repo architect and documentation rules
└── README.md               # Project overview and quickstart guide
```

---

## 2. Key Modules & Entry Points

| Module | Key Class / Function | Responsibility |
|---|---|---|
| `src.cli.main` | `main()` | CLI dispatcher (`sync`, `sync-sold`, `dedupe`, `fetch`, `list`, `login`, `fb-login`, `draft`, `publish`, `fb-draft`) |
| `src.tradera.client` | `TraderaClient.get_profile_items()`, `get_item_detail()` | Fetches HTML from public Tradera seller page and individual listings |
| `src.tradera.parser` | `TraderaParser.parse_profile_page()`, `parse_item_page()` | Converts raw HTML into structured `TraderaItemCard` and `TraderaItemDetail` models |
| `src.storage.repository` | `SyncRepository` | Idempotent state storage, relist recognition, duplicate merging, and sync log tracking |
| `src.storage.dedupe` | `find_matching_existing_item()`, `find_all_duplicates()` | Normalized title, fuzzy similarity (>90%), and image signature clustering |
| `src.reconciliation.sold_checker` | `SoldReconciler.reconcile_sold_items()` | Detects sold items on Tradera and coordinates removal from Blocket and Facebook |
| `src.mapper.category_mapper` | `guess_blocket_category()`, `map_condition()` | 3-level Blocket category, condition, and color mapping |
| `src.mapper.fb_category_mapper`| `guess_fb_category()`, `map_fb_condition()` | Facebook category, condition, and copy formatting |
| `src.mapper.formatter` | `format_blocket_payload()` | Formats titles, descriptions, and resolves pricing |
| `src.blocket.session` | `BlocketSessionManager` | Manages persistent login context with Playwright |
| `src.blocket.drafter` | `BlocketDrafter.draft_item()`, `draft_batch()` | Injects images and fills bracket form for cloud drafts or publishing |
| `src.blocket.unlister` | `BlocketUnlister.unlist_items()` | Unlists sold items from both **Aktiva** (live ads) and **Utkast** (drafts) |
| `src.blocket.cleaner` | `BlocketDraftCleaner.clean_all_drafts()` | Purges outdated cloud drafts from Blocket account |
| `src.facebook.session` | `FacebookSessionManager` | Manages persistent Facebook login context and stealth overrides |
| `src.facebook.drafter` | `FacebookDrafter.draft_item()`, `draft_batch()` | Fills Facebook Marketplace listing form and submits |
| `src.facebook.unlister` | `FacebookUnlister.unlist_items()` | Removes / deletes listings from Facebook Marketplace seller dashboard |

---

## 3. Placement Rules for New Code
- **Marketplace scrapers**: Place under `src/<marketplace>/` with clean separation between network client and HTML parsing.
- **Reconciliation & Unlisting**: Keep platform-agnostic reconciliation logic in `src/reconciliation/` and platform-specific removal in `src/<marketplace>/unlister.py`.
- **Deduplication**: Place matching algorithms and duplicate clustering in `src/storage/dedupe.py`.
- **Data models**: Keep schemas in `src/<domain>/models.py`.
- **Database logic**: All SQL queries and migrations reside in `src/storage/`.
- **Browser automation**: Keep Playwright interactions isolated in `src/blocket/` and `src/facebook/`.
- **Tests**: Mirror `src/` hierarchy inside `tests/` and use mock fixtures where external HTTP calls are involved.
