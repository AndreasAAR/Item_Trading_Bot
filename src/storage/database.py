import sqlite3
from pathlib import Path
from contextlib import contextmanager
from config.settings import DB_PATH

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS items (
    item_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT,
    category_id TEXT,
    buy_now_price INTEGER,
    starting_price INTEGER,
    leading_bid INTEGER,
    target_price INTEGER NOT NULL,
    images_json TEXT,
    attributes_json TEXT,
    shipping_cost INTEGER,
    pickup_available INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'discovered', -- 'discovered', 'staged', 'drafted', 'published', 'ignored'
    blocket_ad_id TEXT,
    blocket_ad_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sync_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(item_id) REFERENCES items(item_id)
);

CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
"""

@contextmanager
def get_db(db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_db(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        # Migrate facebook columns if not present
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(items)")
        columns = [row[1] for row in cursor.fetchall()]
        if "facebook_status" not in columns:
            cursor.execute("ALTER TABLE items ADD COLUMN facebook_status TEXT NOT NULL DEFAULT 'discovered'")
        if "facebook_ad_url" not in columns:
            cursor.execute("ALTER TABLE items ADD COLUMN facebook_ad_url TEXT")
