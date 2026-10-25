import json
from typing import List, Optional, Dict, Any, Tuple
from config.settings import DB_PATH
from src.storage.database import get_db, init_db
from src.tradera.models import TraderaItemDetail

from src.storage.dedupe import (
    normalize_title,
    title_similarity,
    find_matching_existing_item
)

class SyncRepository:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def upsert_item_detailed(
        self,
        item: TraderaItemDetail,
        default_status: str = "discovered"
    ) -> Tuple[str, Optional[Dict[str, Any]], Optional[str]]:
        """
        Insert, refresh, or relist a Tradera item.
        Returns (outcome, matched_item, reason) where outcome is:
          - 'new': Completely new item inserted
          - 'updated': Existing item with same item_id refreshed
          - 'relisted': Relisted item detected (matched by title/images to an old item_id);
                       item_id and listing details updated while preserving draft/publish status!
        """
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            images_json = json.dumps(item.images)
            attrs_json = json.dumps(item.attributes)
            target_price = item.target_blocket_price

            # 1. Direct item_id check
            cursor.execute("SELECT * FROM items WHERE item_id = ?", (item.item_id,))
            row = cursor.fetchone()

            if row is not None:
                # Same Tradera item_id already exists -> update details
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
                return "updated", dict(row), "exact_id"

            # 2. Relist / Deduplication check across all existing items
            cursor.execute("SELECT * FROM items")
            existing_rows = cursor.fetchall()
            existing_items = []
            for r in existing_rows:
                d = dict(r)
                d["images"] = json.loads(d["images_json"]) if d["images_json"] else []
                d["attributes"] = json.loads(d["attributes_json"]) if d["attributes_json"] else {}
                existing_items.append(d)

            match = find_matching_existing_item(
                item_title=item.title,
                item_images=item.images,
                item_price=target_price,
                existing_items=existing_items
            )

            if match:
                matched_item, reason = match
                old_id = matched_item["item_id"]

                # Relisted item detected! Update existing row to the new Tradera item_id and new URLs,
                # while preserving status, blocket_ad_id, blocket_ad_url, facebook_status, facebook_ad_url!
                cursor.execute("""
                    UPDATE items SET
                        item_id = ?, title = ?, url = ?, description = ?, category_id = ?,
                        buy_now_price = ?, starting_price = ?, leading_bid = ?, target_price = ?,
                        images_json = ?, attributes_json = ?, shipping_cost = ?, pickup_available = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE item_id = ?
                """, (
                    item.item_id, item.title, item.url, item.description, item.category_id,
                    item.buy_now_price, item.starting_price, item.leading_bid, target_price,
                    images_json, attrs_json, item.shipping_cost, int(item.pickup_available),
                    old_id
                ))

                # Update sync_logs foreign keys to point to the new item_id
                cursor.execute("UPDATE sync_logs SET item_id = ? WHERE item_id = ?", (item.item_id, old_id))

                # Log the relist detection
                cursor.execute("""
                    INSERT INTO sync_logs (item_id, action, status, message)
                    VALUES (?, 'relist_detected', ?, ?)
                """, (
                    item.item_id,
                    matched_item.get("status", default_status),
                    f"Relist detected ({reason}): ID changed from #{old_id} to #{item.item_id}. Preserved Blocket [{matched_item.get('status')}] and Facebook [{matched_item.get('facebook_status')}]."
                ))
                return "relisted", matched_item, reason

            # 3. Completely new item -> insert fresh record
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
            return "new", None, None

    def upsert_item(self, item: TraderaItemDetail, default_status: str = "discovered") -> bool:
        """Insert or update Tradera item. If item already exists or is a relist, preserves non-discovered status."""
        outcome, _, _ = self.upsert_item_detailed(item, default_status)
        return outcome == "new"

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

    def find_all_duplicates(self) -> List[Dict[str, Any]]:
        """
        Scans all items in the repository to identify duplicate or relisted listings.
        Returns a list of duplicate clusters with matching reasons.
        """
        items = self.list_items()
        duplicates = []
        seen = set()

        for i, item_a in enumerate(items):
            id_a = item_a["item_id"]
            if id_a in seen:
                continue

            matches = []
            for j in range(i + 1, len(items)):
                item_b = items[j]
                id_b = item_b["item_id"]
                if id_b in seen:
                    continue

                from src.storage.dedupe import is_same_listing
                is_match, reason = is_same_listing(
                    title1=item_a["title"],
                    images1=item_a.get("images", []),
                    title2=item_b["title"],
                    images2=item_b.get("images", []),
                    price1=item_a.get("target_price"),
                    price2=item_b.get("target_price")
                )

                if is_match:
                    matches.append({"item": item_b, "reason": reason})
                    seen.add(id_b)

            if matches:
                seen.add(id_a)
                duplicates.append({
                    "primary_item": item_a,
                    "duplicate_items": matches
                })

        return duplicates

    def merge_duplicate_items(self, primary_id: str, duplicate_id: str) -> bool:
        """
        Merges a duplicate item into a primary item:
        - Keeps the primary item as the active record
        - Inherits the highest status (e.g. published > drafted > discovered)
        - Inherits ad URLs if primary is missing them
        - Migrates sync_logs from duplicate_id to primary_id
        - Deletes the duplicate row from items table
        """
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM items WHERE item_id = ?", (primary_id,))
            primary = cursor.fetchone()
            cursor.execute("SELECT * FROM items WHERE item_id = ?", (duplicate_id,))
            duplicate = cursor.fetchone()

            if not primary or not duplicate:
                return False

            p_dict = dict(primary)
            d_dict = dict(duplicate)

            # Determine best status: published > drafted > discovered
            def best_status(s1, s2):
                order = {"published": 3, "drafted": 2, "discovered": 1}
                return s1 if order.get(s1, 0) >= order.get(s2, 0) else s2

            merged_status = best_status(p_dict.get("status"), d_dict.get("status"))
            merged_fb_status = best_status(p_dict.get("facebook_status"), d_dict.get("facebook_status"))
            blocket_url = p_dict.get("blocket_ad_url") or d_dict.get("blocket_ad_url")
            fb_url = p_dict.get("facebook_ad_url") or d_dict.get("facebook_ad_url")
            blocket_id = p_dict.get("blocket_ad_id") or d_dict.get("blocket_ad_id")

            cursor.execute("""
                UPDATE items SET
                    status = ?,
                    facebook_status = ?,
                    blocket_ad_id = ?,
                    blocket_ad_url = ?,
                    facebook_ad_url = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE item_id = ?
            """, (merged_status, merged_fb_status, blocket_id, blocket_url, fb_url, primary_id))

            # Reassign sync_logs
            cursor.execute("UPDATE sync_logs SET item_id = ? WHERE item_id = ?", (primary_id, duplicate_id))

            # Log merge action
            cursor.execute("""
                INSERT INTO sync_logs (item_id, action, status, message)
                VALUES (?, 'merge_completed', ?, ?)
            """, (
                primary_id,
                merged_status,
                f"Merged duplicate item #{duplicate_id} into #{primary_id}. Active Blocket status: {merged_status}, Facebook: {merged_fb_status}."
            ))

            # Delete the duplicate row
            cursor.execute("DELETE FROM items WHERE item_id = ?", (duplicate_id,))
            return True

