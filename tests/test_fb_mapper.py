from src.mapper.fb_category_mapper import (
    guess_fb_category,
    map_fb_condition,
    format_fb_title,
    format_fb_description
)

def test_fb_condition_mapping():
    assert map_fb_condition("helt ny") == "Ny"
    assert map_fb_condition("oanvänt") == "Ny"
    assert map_fb_condition("mycket bra skick") == "Som ny"
    assert map_fb_condition("gott skick") == "Bra skick"
    assert map_fb_condition(None) == "Bra skick"
    assert map_fb_condition("synligt använt") == "Okej skick"

def test_fb_category_mapping():
    assert guess_fb_category("Kalenji XT7 löparskor trailskor") == "Skor för män"
    assert guess_fb_category("Steptronic Falcon finskor") == "Skor för män"
    assert guess_fb_category("Maxi Climber träningsmaskin") == "Sport och friluftsliv"
    assert guess_fb_category("Torrsäck decathlon Duffle Bag") == "Sport och friluftsliv"
    assert guess_fb_category("Bordslampa i metall ikea") == "Möbler och heminredning"
    assert guess_fb_category("Skip Hop Babylekcenter") == "Leksaker och spel"
    assert guess_fb_category("Uniqlo oxford slim ljusblå skjorta") == "Kläder för män"

def test_fb_formatting():
    title = format_fb_title("A" * 120, max_length=100)
    assert len(title) <= 100
    assert title.endswith("...")

    item = {
        "description": "Fint skick.",
        "attributes": {"Storlek": "M", "Färg": "Blå"}
    }
    desc = format_fb_description(item)
    assert "Fint skick." in desc
    assert "• Storlek: M" in desc
    assert "Odenplan" in desc
    assert "Blocketpaket" not in desc
