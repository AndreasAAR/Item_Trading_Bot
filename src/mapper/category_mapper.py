import re
from typing import Optional, Dict, Any

# Map Tradera condition strings to exact Blocket dropdown values
BLOCKET_CONDITIONS = {
    "nytt": "Nytt skick - helt ny",
    "oanvänt": "Nytt skick - helt ny",
    "som ny": "Mycket bra skick - som ny",
    "mycket gott skick": "Mycket bra skick - som ny",
    "mycket bra skick": "Mycket bra skick - som ny",
    "gott skick": "Bra skick - varsamt använd",
    "gott använt skick": "Bra skick - varsamt använd",
    "bra skick": "Bra skick - varsamt använd",
    "använt skick": "Bra skick - varsamt använd",
    "okej skick": "Okej skick - synligt använd",
    "synligt använt": "Okej skick - synligt använd",
    "defekt": "Funkar inte - kan fixas",
    "reparationsobjekt": "Funkar inte - kan fixas",
}

BLOCKET_COLORS = [
    "Svart", "Grå", "Vit", "Beige", "Gul", "Orange", "Röd", "Rosa", "Lila", "Blå", "Grön", "Brun", "Flerfärgad"
]

def map_condition(tradera_cond: Optional[str]) -> str:
    """Maps a Tradera condition string to the corresponding Blocket dropdown value."""
    if not tradera_cond:
        return "Bra skick - varsamt använd"
    c_lower = tradera_cond.strip().lower()
    for k, v in BLOCKET_CONDITIONS.items():
        if k in c_lower:
            return v
    return "Bra skick - varsamt använd"

def map_color(color_val: Optional[str]) -> Optional[str]:
    """Maps a color string to a Blocket color choice."""
    if not color_val:
        return None
    c_lower = color_val.strip().lower()
    mapping = {
        "svart": "Svart", "black": "Svart",
        "grå": "Grå", "mörkgrå": "Grå", "ljusgrå": "Grå", "gray": "Grå", "grey": "Grå",
        "vit": "Vit", "white": "Vit",
        "blå": "Blå", "navy": "Blå", "marinblå": "Blå", "ljusblå": "Blå", "blue": "Blå",
        "brun": "Brun", "brown": "Brun",
        "grön": "Grön", "green": "Grön", "olivgrön": "Grön", "mörkgrön": "Grön",
        "beige": "Beige", "sand": "Beige",
        "röd": "Röd", "red": "Röd",
        "gul": "Gul", "yellow": "Gul",
        "rosa": "Rosa", "pink": "Rosa",
        "lila": "Lila", "purple": "Lila",
        "orange": "Orange",
        "flerfärgad": "Flerfärgad", "mönstrad": "Flerfärgad", "randig": "Flerfärgad",
    }
    for k, v in mapping.items():
        if k in c_lower:
            return v
    return None

def guess_blocket_category(title: str, category_path: Optional[str] = None, tradera_cat_id: Optional[str] = None) -> Dict[str, Optional[str]]:
    """
    Determines 3-level Blocket category:
      - main: Huvudkategori (Select 0)
      - sub: Underkategori (Select 1)
      - prod: Produktkategori (Select 2)
    """
    t_lower = title.lower()
    path_lower = (category_path or "").lower()

    # 1. Sport trail shoes / running shoes -> per user instruction: 'Trail shoes can go träningskläder'
    if any(k in t_lower for k in ["trailsko", "löparsko", "trail", "running", "kalenji", "pegasus"]) and any(k in t_lower for k in ["sko", "skor"]):
        return {
            "main": "Sport och friluftsliv",
            "sub": "Träningskläder och skor",
            "prod": None
        }

    # 2. General shoes (finskor, kängor, sneakers etc.)
    if any(k in t_lower or k in path_lower for k in ["finskor", "loafers", "stövlar", "kängor", "boots", "sandaler"]) or ("skor" in t_lower and "träning" not in t_lower):
        prod = "Finskor" if "finskor" in t_lower else "Sneakers" if "sneakers" in t_lower else None
        return {
            "main": "Kläder, kosmetika och accessoarer",
            "sub": "Skor",
            "prod": "Herrskor"  # under Skor, Select 2 is Herrskor / Damskor
        }

    # 3. Bags / Duffle / Torrsäck
    if any(k in t_lower for k in ["duffle", "duffel", "torrsäck", "ryggsäck", "väska", "bag"]):
        if any(k in t_lower for k in ["decathlon", "itiwit", "quechua", "torrsäck", "duffle", "duffel"]):
            return {
                "main": "Sport och friluftsliv",
                "sub": "Jakt, fiske och camping",
                "prod": None
            }
        return {
            "main": "Kläder, kosmetika och accessoarer",
            "sub": "Väskor och plånböcker",
            "prod": None
        }

    # 4. Träningsmaskiner (Maxi Climber etc.)
    if any(k in t_lower for k in ["climber", "träningsmaskin", "crosstrainer", "löpband", "motionscykel", "hantlar"]):
        return {
            "main": "Sport och friluftsliv",
            "sub": "Träningsmaskiner och -redskap",
            "prod": None
        }

    # 5. Baby / Barn (Skip Hop Babylekcenter etc.)
    if any(k in t_lower for k in ["babylekcenter", "skip hop", "leksak", "barn", "baby"]):
        return {
            "main": "Föräldrar och barn",
            "sub": "Leksaker",
            "prod": None
        }

    # 6. Lampor / Belysning
    if any(k in t_lower for k in ["lampa", "bordslampa", "skrivbordslampa", "golvlampa", "taklampa"]):
        return {
            "main": "Möbler och inredning",
            "sub": "Lampor",
            "prod": "Bordslampor" if any(k in t_lower for k in ["bordslampa", "skrivbordslampa"]) else None
        }

    # 7. Möbler (pall, rullgardin, bord, stol etc.)
    if any(k in t_lower for k in ["kökspall", "pall", "rullgardin", "hoppvals", "stol", "bord", "hylla", "byrå"]):
        return {
            "main": "Möbler och inredning",
            "sub": "Bord och stolar" if "pall" in t_lower or "stol" in t_lower or "bord" in t_lower else "Övriga möbler och inredning",
            "prod": None
        }

    # 8. Vitvaror / Elektronik (Sharp Mikrovågsugn etc.)
    if any(k in t_lower for k in ["mikrovågsugn", "ugn", "mikro", "grillfunktion"]):
        return {
            "main": "Elektronik och vitvaror",
            "sub": "Vitvaror",
            "prod": None
        }

    # 9. Musikinstrument (Ukulele, gitarr etc.)
    if any(k in t_lower for k in ["ukulele", "gitarr", "bas", "piano", "synth", "trummor"]):
        return {
            "main": "Underhållning och hobby",
            "sub": "Musikinstrument",
            "prod": None
        }

    # 10. Clothing - Herrkläder
    # Specific garment types (Produktkategori)
    prod = None
    if any(k in t_lower or k in path_lower for k in ["tröja", "pullover", "stickat", "kofta", "cardigan", "stickade"]):
        prod = "Tröjor och stickat"
    elif any(k in t_lower or k in path_lower for k in ["skjorta", "oxford", "linneskjorta"]):
        prod = "Skjortor"
    elif any(k in t_lower or k in path_lower for k in ["jacka", "trenchcoat", "kappa", "puffertech", "väst", "overshirt", "ytterkläder"]):
        prod = "Jackor och kappor"
    elif any(k in t_lower or k in path_lower for k in ["jeans"]):
        prod = "Jeans"
    elif any(k in t_lower or k in path_lower for k in ["byxor", "chinos", "shorts"]):
        prod = "Byxor och shorts"
    elif any(k in t_lower or k in path_lower for k in ["kavaj", "kostym"]):
        prod = "Kostymer"
    elif any(k in t_lower or k in path_lower for k in ["t-shirt", "piké", "linne"]):
        prod = "T-shirts och linnen"

    res = {
        "main": "Kläder, kosmetika och accessoarer",
        "sub": "Herrkläder",
        "prod": prod or "Tröjor och stickat",
        "type": "Herrkläder"
    }
    return res
