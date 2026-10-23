import json
from typing import List, Optional, Dict, Any
from config.settings import DB_PATH
from src.storage.database import get_db, init_db
from src.tradera.models import TraderaItemDetail

class SyncRepository:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def upsert_item(self, item: TraderaItemDetail, default_status: str = "discovered") -> bool:
        """Insert or update Tradera item. If item already exists, preserves non-discovered status."""
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM items WHERE item_id = ?", (item.item_id,))
            row = cursor.fetchone()

            images_json = json.dumps(item.images)
            attrs_json = json.dumps(item.attributes)
            target_price = item.target_blocket_price

            if row is None:
                cursor.execute("""
                    INSERT INTO items (
                        item_id, title, url, description, category_id,
                        buy_now_price, starting_price, leading_bid, target_price,
                        images_json, attributes_json, shipping_cost, pickup_available,
                        status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.item_id, item.title, item.url, item.description, item.category_id,
                    item.buy_now_price, item.starting_price, item.leading_bid, target_price,
                    images_json, attrs_json, item.shipping_cost, int(item.pickup_available),
                    default_status
                ))
                return True
            else:
                cursor.execute("""
                    UPDATE items SET
                        title = ?, url = ?, description = ?, category_id = ?,
                        buy_now_price = ?, starting_price = ?, leading_bid = ?, target_price = ?,
                        images_json = ?, attributes_json = ?, shipping_cost = ?, pickup_available = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE item_id = ?
                """, (
                    item.title, item.url, item.description, item.category_id,
                    item.buy_now_price, item.starting_price, item.leading_bid, target_price,
                    images_json, attrs_json, item.shipping_cost, int(item.pickup_available),
                    item.item_id
                ))
                return False

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM items WHERE item_id = ?", (item_id,))
            row = cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            data["images"] = json.loads(data["images_json"]) if data["images_json"] else []
            data["attributes"] = json.loads(data["attributes_json"]) if data["attributes_json"] else {}
            return data

    def list_items(self, status: Optional[str] = None, platform: str = "blocket") -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            status_col = "facebook_status" if platform == "facebook" else "status"
            if status:
                cursor.execute(f"SELECT * FROM items WHERE {status_col} = ? ORDER BY item_id DESC", (status,))
            else:
                cursor.execute("SELECT * FROM items ORDER BY item_id DESC")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["images"] = json.loads(d["images_json"]) if d["images_json"] else []
                d["attributes"] = json.loads(d["attributes_json"]) if d["attributes_json"] else {}
                results.append(d)
            return results

    def update_status(self, item_id: str, new_status: str, blocket_ad_id: Optional[str] = None, blocket_ad_url: Optional[str] = None) -> None:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE items SET
                    status = ?,
                    blocket_ad_id = COALESCE(?, blocket_ad_id),
                    blocket_ad_url = COALESCE(?, blocket_ad_url),
                    updated_at = CURRENT_TIMESTAMP
                WHERE item_id = ?
            """, (new_status, blocket_ad_id, blocket_ad_url, item_id))
            cursor.execute("""
                INSERT INTO sync_logs (item_id, action, status, message)
                VALUES (?, 'status_change', ?, ?)
            """, (item_id, new_status, f"Status updated to {new_status}"))

    def update_facebook_status(self, item_id: str, new_status: str, facebook_ad_url: Optional[str] = None) -> None:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE items SET
                    facebook_status = ?,
                    facebook_ad_url = COALESCE(?, facebook_ad_url),
                    updated_at = CURRENT_TIMESTAMP
                WHERE item_id = ?
            """, (new_status, facebook_ad_url, item_id))
            cursor.execute("""
                INSERT INTO sync_logs (item_id, action, status, message)
                VALUES (?, 'fb_status_change', ?, ?)
            """, (item_id, new_status, f"Facebook status updated to {new_status}"))

    def update_price(self, item_id: str, new_price: int) -> None:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE items SET target_price = ?, updated_at = CURRENT_TIMESTAMP WHERE item_id = ?", (new_price, item_id))

