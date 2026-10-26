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
        if "base_price" not in columns:
            cursor.execute("ALTER TABLE items ADD COLUMN base_price INTEGER")
            cursor.execute("UPDATE items SET base_price = target_price WHERE base_price IS NULL")
        if "floor_price" not in columns:
            cursor.execute("ALTER TABLE items ADD COLUMN floor_price INTEGER")
            # Default floor price: 70% of target price (max 30% drop)
            cursor.execute("UPDATE items SET floor_price = CAST(target_price * 0.7 AS INTEGER) WHERE floor_price IS NULL")
        if "cover_image_index" not in columns:
            cursor.execute("ALTER TABLE items ADD COLUMN cover_image_index INTEGER NOT NULL DEFAULT 0")
        if "relist_count" not in columns:
            cursor.execute("ALTER TABLE items ADD COLUMN relist_count INTEGER NOT NULL DEFAULT 0")
        if "pricing_phase" not in columns:
            cursor.execute("ALTER TABLE items ADD COLUMN pricing_phase TEXT NOT NULL DEFAULT 'anchor'")
        if "ladder_step" not in columns:
            cursor.execute("ALTER TABLE items ADD COLUMN ladder_step INTEGER NOT NULL DEFAULT 0")
        if "last_price_change_at" not in columns:
            cursor.execute("ALTER TABLE items ADD COLUMN last_price_change_at TIMESTAMP")
        if "last_relisted_at" not in columns:
            cursor.execute("ALTER TABLE items ADD COLUMN last_relisted_at TIMESTAMP")

        # Normalize floor prices and initial target prices to end in 9
        from src.pricing.ladder import round_to_nine, calculate_ladder_price
        cursor.execute("SELECT item_id, base_price, floor_price, ladder_step, target_price FROM items")
        rows = cursor.fetchall()
        for r in rows:
            i_id = r["item_id"]
            b_price = r["base_price"] or r["target_price"] or 100
            f_price = r["floor_price"]
            l_step = r["ladder_step"] or 0
            t_price = r["target_price"]

            # Fix floor price to end with 9
            proper_floor = round_to_nine(b_price * 0.70)
            if f_price is None or f_price % 10 != 9:
                cursor.execute("UPDATE items SET floor_price = ? WHERE item_id = ?", (proper_floor, i_id))

            # If item is at step 0 and target_price equals base_price, initialize to +30% anchor
            if l_step == 0 and t_price == b_price:
                step0_price, _ = calculate_ladder_price(b_price, step=0, custom_floor=proper_floor)
                cursor.execute("UPDATE items SET target_price = ? WHERE item_id = ?", (step0_price, i_id))


