import re
import json
import urllib.parse
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from typing import List, Optional, Dict
from src.tradera.models import TraderaItemCard, TraderaItemDetail

class TraderaParser:
    @staticmethod
    def parse_profile_page(html_content: str, base_url: str = "https://www.tradera.com") -> List[TraderaItemCard]:
        soup = BeautifulSoup(html_content, "html.parser")
        cards = soup.find_all(attrs={"data-item-card-id": True})
        items: List[TraderaItemCard] = []

        for card in cards:
            item_id = card.get("data-item-card-id")
            if not item_id:
                continue

            # Link & Title
            link_el = card.find("a", href=lambda h: h and f"/{item_id}/" in h)
            rel_url = link_el["href"] if link_el else ""
            full_url = urllib.parse.urljoin(base_url, rel_url)

            # Extract category ID from url /item/<cat_id>/<item_id>/...
            cat_match = re.search(r'/item/(\d+)/', rel_url)
            cat_id = cat_match.group(1) if cat_match else None

            # Find title
            # In Tradera cards, title is usually inside the link or aria-label or heading
            title = ""
            if link_el:
                title = link_el.get_text(strip=True)
            if not title:
                # Try finding text inside card
                card_text = list(card.stripped_strings)
                for t in card_text:
                    if len(t) > 10 and not any(k in t.lower() for k in ["sluttid", "pris", "köp nu", "badge", "bud"]):
                        title = t
                        break

            # Thumbnail image
            img = card.find("img")
            thumb_url = img["src"] if img and img.has_attr("src") else None

            # Prices
            card_raw = " ".join(card.stripped_strings)
            buy_now = None
            starting_price = None
            leading_bid = None

            bn_match = re.search(r'(?:Köp nu|Eller Köp nu)\s*[:]?\s*(\d+[\s\d]*)\s*kr', card_raw, re.I)
            if bn_match:
                buy_now = int(re.sub(r'\s+', '', bn_match.group(1)))

            start_match = re.search(r'(?:Utropspris|Startpris)\s*[:]?\s*(\d+[\s\d]*)\s*kr', card_raw, re.I)
            if start_match:
                starting_price = int(re.sub(r'\s+', '', start_match.group(1)))

            bid_match = re.search(r'(?:Ledande bud|Pris)\s*[:]?\s*(\d+[\s\d]*)\s*kr', card_raw, re.I)
            if bid_match:
                price_val = int(re.sub(r'\s+', '', bid_match.group(1)))
                if starting_price is None:
                    starting_price = price_val
                leading_bid = price_val

            item_type = card.get("data-item-type")

            items.append(
                TraderaItemCard(
                    item_id=str(item_id),
                    title=title or f"Tradera Item {item_id}",
                    url=full_url,
                    thumbnail_url=thumb_url,
                    leading_bid=leading_bid,
                    starting_price=starting_price,
                    buy_now_price=buy_now,
                    item_type=item_type,
                    category_id=cat_id,
                )
            )

        return items

    @staticmethod
    def parse_item_page(html_content: str, item_url: str) -> TraderaItemDetail:
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract item ID
        id_match = re.search(r'/item/(\d+)/(\d+)/', item_url)
        if id_match:
            cat_id = id_match.group(1)
            item_id = id_match.group(2)
        else:
            cat_id = None
            alt_match = re.search(r'/item/.*?(\d{7,12})', item_url)
            item_id = alt_match.group(1) if alt_match else "unknown"

        # Title
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else ""

        # Description
        desc_div = soup.find(id="item-description") or soup.find(attrs={"data-testid": "item-description"})
        if not desc_div:
            # Fallback to description container
            desc_div = soup.find("div", class_=re.compile(r"description|item-desc", re.I))

        description = desc_div.get_text(separator="\n", strip=True) if desc_div else ""

        # Images - Extract large-fit image URLs and deduplicate by image hash/ID
        image_urls = []
        seen_img_keys = set()

        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if "img.tradera.net" in src:
                # Convert small-square / medium-fit to large-fit
                large_url = re.sub(r'/(?:small-square|medium-fit|thumbnail|small-fit)/', '/large-fit/', src)
                # Key by filename/hash
                img_key = large_url.split("/")[-1].split("?")[0]
                if img_key and img_key not in seen_img_keys:
                    seen_img_keys.add(img_key)
                    image_urls.append(large_url)

        # 1. Breadcrumbs
        category_path: List[str] = []
        bc_nav = soup.find("nav", {"aria-label": re.compile(r"breadcrumb|brödsmul", re.I)}) or soup.find(class_=re.compile(r"breadcrumb", re.I))
        if bc_nav:
            category_path = [a.get_text(strip=True) for a in bc_nav.find_all("a") if a.get_text(strip=True)]
        if not category_path:
            for a in soup.find_all("a", href=re.compile(r"/category/\d+$")):
                t = a.get_text(strip=True)
                if t and t not in category_path and not any(k in t.lower() for k in ["sveriges", "vykort", "övrigt", "alla kategorier"]):
                    category_path.append(t)

        # 2. Extract filter attribute links
        raw_attrs: Dict[str, str] = {}
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "?" in href and ("af-" in href or "brand=" in href):
                parsed = urlparse(href)
                qs = parse_qs(parsed.query)
                text = a.get_text(strip=True)
                for k, vs in qs.items():
                    val = text if text else vs[0]
                    raw_attrs[k] = val

        for dl in soup.find_all(["dl", "table"]):
            dts = dl.find_all(["dt", "th"])
            dds = dl.find_all(["dd", "td"])
            if len(dts) == len(dds):
                for dt, dd in zip(dts, dds):
                    k = dt.get_text(strip=True)
                    v = dd.get_text(strip=True)
                    if k and v:
                        raw_attrs[k] = v

        # 3. JSON-LD fallback for brand, color, condition
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(s.string)
                if data.get("@type") == "Product":
                    b = data.get("brand")
                    if b and "brand" not in raw_attrs:
                        raw_attrs["brand"] = b.get("name") if isinstance(b, dict) else b
                    c = data.get("color")
                    if c and "af-color" not in raw_attrs:
                        raw_attrs["af-color"] = c
                    cond = data.get("itemCondition")
                    if cond and "af-condition" not in raw_attrs:
                        raw_attrs["af-condition"] = "Begagnat" if "Used" in cond else "Nytt"
            except Exception:
                pass

        # 4. Standardized attribute dictionary
        attributes: Dict[str, str] = {}

        # Brand
        brand = raw_attrs.get("brand")
        # Check title if title specifies a known brand
        known_brands = [
            "Arket", "Massimo Dutti", "COS", "Uniqlo", "Sharp", "Kalenji", "Nike", "Adidas",
            "Steptronic", "Haglöfs", "IKEA", "Ikea", "Skip Hop", "Quechua", "Decathlon", "Zara",
            "Filippa K", "Tiger of Sweden", "Oscar Jacobson", "Gant", "Peak Performance", "Patagonia"
        ]
        title_lower = title.lower()
        for kb in known_brands:
            if kb.lower() in title_lower:
                brand = kb
                break
        if not brand and title:
            first_w = title.split()[0]
            if first_w.lower() not in ["ny", "fin", "snygg", "svart", "vit", "vintage", "retro", "mörkgrå"]:
                brand = first_w
        if brand:
            attributes["brand"] = brand

        # Size
        size = raw_attrs.get("af-clothes_size") or raw_attrs.get("af-shoe_size") or raw_attrs.get("Klädstorlek") or raw_attrs.get("Skostorlek")
        if not size:
            sz_match = re.search(r'(?:storlek|strl|stl|size)\s*[:]?\s*([A-Za-z0-9/]+)', title, re.I)
            if sz_match:
                size = sz_match.group(1).upper()
        if size:
            attributes["size"] = size
            attributes["Klädstorlek"] = size

        # Color
        color = raw_attrs.get("af-color")
        color_swaps = {
            "black": "Svart", "svart": "Svart",
            "gray": "Grå", "grey": "Grå", "grå": "Grå", "mörkgrå": "Grå",
            "white": "Vit", "vit": "Vit",
            "blue": "Blå", "blå": "Blå", "navy": "Blå", "marinblå": "Blå", "ljusblå": "Blå",
            "brown": "Brun", "brun": "Brun",
            "green": "Grön", "grön": "Grön",
            "beige": "Beige",
            "red": "Röd", "röd": "Röd",
            "yellow": "Gul", "gul": "Gul",
            "pink": "Rosa", "rosa": "Rosa",
            "orange": "Orange"
        }
        if color and color.lower() in color_swaps:
            color = color_swaps[color.lower()]
        elif not color:
            for k_col, v_col in color_swaps.items():
                if re.search(rf'\b{k_col}\b', title_lower):
                    color = v_col
                    break
        if color:
            attributes["color"] = color

        # Condition (defaults to 'Bra skick - varsamt använd')
        cond = raw_attrs.get("af-condition")
        if cond:
            attributes["condition"] = cond
        else:
            attributes["condition"] = "Bra skick"

        # Material
        material = raw_attrs.get("af-clothes_material")
        if not material:
            for mat in ["merinoull", "ull", "bomull", "silke", "linne", "polyester", "dun", "skinn", "läder", "metall"]:
                if mat in title_lower or mat in description.lower():
                    material = mat.capitalize()
                    break
        if material:
            attributes["material"] = material

        # Fit (Default to Normal unless specified)
        if any(k in description.lower() or k in title_lower for k in ["liten i storleken", "små i storleken"]):
            attributes["fit"] = "Liten i storleken"
        elif any(k in description.lower() or k in title_lower for k in ["stor i storleken", "stora i storleken"]):
            attributes["fit"] = "Stor i storleken"
        else:
            attributes["fit"] = "Normal i storleken"

        # Preserve category_path in attributes
        if category_path:
            attributes["category_path"] = " > ".join(category_path)

        # Localized aliases for Swedish compatibility
        if "brand" in attributes:
            attributes["Varumärke"] = attributes["brand"]
        if "size" in attributes:
            attributes["Storlek"] = attributes["size"]
        if "color" in attributes:
            attributes["Färg"] = attributes["color"]
        if "condition" in attributes:
            attributes["Skick"] = attributes["condition"]
        if "material" in attributes:
            attributes["Material"] = attributes["material"]

        # Pricing from item page
        page_text = soup.get_text()
        buy_now = None
        starting_price = None
        leading_bid = None

        bn_match = re.search(r'(?:Köp nu|Eller Köp nu)\s*[:]?\s*(\d+[\s\d]*)\s*kr', page_text, re.I)
        if bn_match:
            buy_now = int(re.sub(r'\s+', '', bn_match.group(1)))

        start_match = re.search(r'(?:Utropspris|Startpris)\s*[:]?\s*(\d+[\s\d]*)\s*kr', page_text, re.I)
        if start_match:
            starting_price = int(re.sub(r'\s+', '', start_match.group(1)))

        bid_match = re.search(r'(?:Ledande bud|Högsta bud)\s*[:]?\s*(\d+[\s\d]*)\s*kr', page_text, re.I)
        if bid_match:
            leading_bid = int(re.sub(r'\s+', '', bid_match.group(1)))

        # Shipping & pickup
        shipping_cost = None
        cost_match = re.search(r'(?:Frakt|Fraktkostnad)\s*[:]?\s*(\d+[\s\d]*)\s*kr', page_text, re.I)
        if cost_match:
            shipping_cost = int(re.sub(r'\s+', '', cost_match.group(1)))

        pickup_available = bool(re.search(r'avhämtning|kan hämtas', page_text, re.I))

        return TraderaItemDetail(
            item_id=str(item_id),
            title=title,
            url=item_url,
            description=description,
            images=image_urls,
            buy_now_price=buy_now,
            starting_price=starting_price,
            leading_bid=leading_bid,
            attributes=attributes,
            shipping_cost=shipping_cost,
            pickup_available=pickup_available,
            category_id=cat_id,
        )
