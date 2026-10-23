import re
from typing import Optional, Dict, Any, List

# Facebook standard condition choices (Swedish and English equivalents)
FB_CONDITIONS = {
    "nytt": "Ny",
    "oanvänt": "Ny",
    "helt ny": "Ny",
    "som ny": "Som ny",
    "mycket bra skick": "Som ny",
    "mycket gott skick": "Som ny",
    "bra skick": "Bra skick",
    "gott skick": "Bra skick",
    "gott använt skick": "Bra skick",
    "använt skick": "Bra skick",
    "okej skick": "Okej skick",
    "synligt använt": "Okej skick",
    "defekt": "Okej skick",
}

def map_fb_condition(tradera_cond: Optional[str]) -> str:
    """Maps Tradera condition string to Facebook Marketplace condition."""
    if not tradera_cond:
        return "Bra skick"
    c_lower = tradera_cond.strip().lower()
    for k, v in FB_CONDITIONS.items():
        if k in c_lower:
            return v
    return "Bra skick"

def guess_fb_category(title: str, category_path: Optional[str] = None) -> str:
    """
    Determines category keyword for Facebook Marketplace search/selection.
    Matches standard Facebook Marketplace categories in Swedish.
    """
    t_lower = title.lower()
    path_lower = (category_path or "").lower()

    # 1. Shoes
    if any(k in t_lower or k in path_lower for k in ["sko", "skor", "sneakers", "boots", "kängor", "stövlar", "finskor"]):
        return "Skor för män"

    # 2. Sports, outdoor & gym
    if any(k in t_lower for k in ["duffle", "duffel", "torrsäck", "ryggsäck", "climber", "träningsmaskin", "crosstrainer", "löpband"]):
        return "Sport och friluftsliv"

    # 3. Furniture & Home / Lighting
    if any(k in t_lower for k in ["lampa", "bordslampa", "skrivbordslampa", "stol", "bord", "pall", "möbel", "inredning", "rullgardin"]):
        return "Möbler och heminredning"

    # 4. Baby & Kids / Toys
    if any(k in t_lower for k in ["babylekcenter", "skip hop", "leksak", "barn", "baby"]):
        return "Leksaker och spel"

    # 5. Default to Men's clothing for garments
    return "Kläder för män"

def format_fb_title(title: str, max_length: int = 100) -> str:
    """Formats title for Facebook Marketplace."""
    clean_title = " ".join(title.split())
    if len(clean_title) <= max_length:
        return clean_title
    return clean_title[:max_length - 3] + "..."

def format_fb_description(item_data: Dict[str, Any]) -> str:
    """Formats clean description for Facebook Marketplace."""
    original_desc = item_data.get("description", "").strip()
    attributes: Dict[str, str] = item_data.get("attributes", {})

    lines: List[str] = []
    if original_desc:
        lines.append(original_desc)
        lines.append("")

    spec_lines = []
    for k, v in attributes.items():
        spec_lines.append(f"• {k}: {v}")

    if spec_lines:
        lines.append("Detaljer:")
        lines.extend(spec_lines)
        lines.append("")

    pickup_note = "Finns för avhämtning i Stockholm (Odenplan) eller kan skickas mot fraktkostnad."
    lines.append(pickup_note)

    return "\n".join(lines).strip()
