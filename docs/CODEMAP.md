# Repository Codemap

## 1. Directory Structure

```
Item_Trading_bot/
├── docs/
│   ├── ARCHITECTURE.md     # Subsystem designs and execution flows
│   ├── CODEMAP.md          # File directory map and entry points
│   ├── DECISIONS.md        # Architectural decision records (ADRs)
│   ├── goal.md             # High-level project goals and requirements
│   └── roadmap.md          # Phased implementation plan and progress
├── config/
│   └── settings.py         # Configurable parameters (profile URLs, paths, selectors)
├── data/                   # Git-ignored local data (SQLite db, sessions, staged images)
│   ├── sync_store.db       # Local SQLite tracking database
│   ├── blocket_auth_state.json # Saved Playwright session state
│   └── staged_images/      # Downloaded image files for uploading
├── src/
│   ├── __init__.py
│   ├── cli/                # Command line interface commands
│   │   ├── __init__.py
│   │   └── main.py
│   ├── tradera/            # Tradera fetching and parsing
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── models.py
│   │   └── parser.py
│   ├── storage/            # SQLite storage & sync repository
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── repository.py
│   ├── mapper/             # Data transformation & copy formatting
│   │   ├── __init__.py
│   │   ├── category_mapper.py
│   │   ├── fb_category_mapper.py
│   │   ├── formatter.py
│   │   └── image_downloader.py
│   ├── blocket/            # Blocket automation with Playwright
│   │   ├── __init__.py
│   │   ├── session.py
│   │   ├── drafter.py
│   │   └── cleaner.py
│   └── facebook/           # Facebook Marketplace automation with Playwright
│       ├── __init__.py
│       ├── session.py
│       └── drafter.py
├── tests/                  # Unit and integration test suites
│   ├── test_tradera_parser.py
│   ├── test_storage.py
│   ├── test_mapper.py
│   ├── test_category_mapper.py
│   └── test_fb_mapper.py
├── AGENTS.md               # Repository navigation and agent guidelines
├── SKILL.md                # Repo architect and documentation rules
└── README.md               # Project overview and quickstart guide
```

---

## 2. Key Modules & Entry Points

| Module | Key Class / Function | Responsibility |
|---|---|---|
| `src.cli.main` | `main()` | CLI interface dispatching commands (`fetch`, `list`, `login`, `fb-login`, `draft`, `fb-draft`, `sync`) |
| `src.tradera.client` | `TraderaClient.fetch_profile()` | Retrieves HTML from public Tradera seller page |
| `src.tradera.parser` | `TraderaParser.parse_item_card()`, `parse_item_page()` | Converts raw HTML into `TraderaItem` models |
| `src.storage.repository` | `SyncRepository` | Saves and queries items and their multi-platform sync state |
| `src.mapper.category_mapper` | `guess_blocket_category()`, `map_condition()` | 3-level Blocket category, condition, and color mapping |
| `src.mapper.fb_category_mapper`| `guess_fb_category()`, `map_fb_condition()` | Facebook category, condition, and copy formatting |
| `src.mapper.formatter` | `format_blocket_payload()` | Formats titles, descriptions, and resolves pricing |
| `src.blocket.session` | `BlocketSessionManager` | Manages persistent login context with Playwright |
| `src.blocket.drafter` | `BlocketDrafter.draft_item()`, `draft_batch()` | Fills full bracket form and attaches images in browser |
| `src.blocket.cleaner` | `BlocketDraftCleaner.clean_all_drafts()` | Purges outdated cloud drafts from Blocket account |
| `src.facebook.session` | `FacebookSessionManager` | Manages persistent Facebook login context |
| `src.facebook.drafter` | `FacebookDrafter.draft_item()`, `draft_batch()` | Fills Facebook Marketplace listing form in browser |

---

## 3. Placement Rules for New Code
- **Marketplace scrapers**: Place under `src/<marketplace>/` with clean separation between network client and HTML parsing.
- **Data models**: Keep Pydantic schemas in `src/<domain>/models.py`.
- **Database logic**: All SQL queries and migrations reside in `src/storage/`.
- **Browser automation**: Keep Playwright-specific interactions isolated in `src/blocket/`.
- **Tests**: Mirror `src/` hierarchy inside `tests/` and use mock fixtures where external HTTP calls are involved.
