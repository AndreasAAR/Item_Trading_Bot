import re
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher

def normalize_title(title: str) -> str:
    """
    Normalizes a product title for consistent deduplication comparison.
    - Converts to lowercase
    - Replaces punctuation, dashes, brackets, and separators with single spaces
    - Preserves Swedish characters (å, ä, ö)
    - Trims excess whitespace
    """
    if not title:
        return ""
    s = title.strip().lower()
    # Replace common punctuation and separators with a space
    s = re.sub(r'[\s\-_,.:;!?/\\|()[\]{}"]+', ' ', s)
    return ' '.join(s.split())

def title_similarity(t1: str, t2: str) -> float:
    """Calculates string similarity ratio (0.0 to 1.0) between two normalized titles."""
    n1 = normalize_title(t1)
    n2 = normalize_title(t2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0
    return SequenceMatcher(None, n1, n2).ratio()

def extract_image_signatures(images: List[str]) -> set:
    """
    Extracts filename signatures from image URLs.
    Example: 'https://img.tradera.net/.../664381630_6b9bdde2.jpg' -> '664381630_6b9bdde2.jpg'
    """
    sigs = set()
    for img in images:
        if not img or not isinstance(img, str):
            continue
        filename = img.split("?")[0].split("/")[-1]
        if filename:
            sigs.add(filename.lower())
    return sigs

def is_same_listing(
    title1: str,
    images1: List[str],
    title2: str,
    images2: List[str],
    price1: Optional[int] = None,
    price2: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Determines if two items represent the same physical listing.
    Returns (is_match, reason).
    """
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)

    # 1. Exact normalized title match
    if norm1 and norm2 and norm1 == norm2:
        return True, "exact_title_match"

    # 2. Shared Tradera image signature match
    sigs1 = extract_image_signatures(images1)
    sigs2 = extract_image_signatures(images2)
    shared_sigs = sigs1.intersection(sigs2)
    if shared_sigs:
        return True, f"shared_image_match ({len(shared_sigs)} images)"

    # 3. High fuzzy title similarity (>= 0.92)
    sim = title_similarity(title1, title2)
    if sim >= 0.92:
        return True, f"fuzzy_title_match ({sim:.2f})"

    # 4. Moderate fuzzy similarity (>= 0.85) with compatible pricing (within 25%)
    if sim >= 0.85 and price1 and price2 and price1 > 0 and price2 > 0:
        price_diff = abs(price1 - price2) / max(price1, price2)
        if price_diff <= 0.25:
            return True, f"fuzzy_title_price_match ({sim:.2f}, price diff {price_diff:.0%})"

    return False, "no_match"

def find_matching_existing_item(
    item_title: str,
    item_images: List[str],
    item_price: Optional[int],
    existing_items: List[Dict[str, Any]]
) -> Optional[Tuple[Dict[str, Any], str]]:
    """
    Scans a list of existing database items to find a matching listing.
    Returns (matched_item_dict, match_reason) if found, else None.
    """
    for ex in existing_items:
        ex_title = ex.get("title", "")
        ex_images = ex.get("images", [])
        ex_price = ex.get("target_price") or ex.get("buy_now_price")

        is_match, reason = is_same_listing(
            title1=item_title,
            images1=item_images,
            title2=ex_title,
            images2=ex_images,
            price1=item_price,
            price2=ex_price
        )
        if is_match:
            return ex, reason

    return None
