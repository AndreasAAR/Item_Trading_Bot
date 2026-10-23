from src.mapper.category_mapper import guess_blocket_category
from src.mapper.formatter import format_blocket_title, format_blocket_description

def test_category_mapper():
    res1 = guess_blocket_category("ARKET svart merino tröja storlek M", tradera_cat_id="1000656")
    assert res1["type"] == "Herrkläder"

    res2 = guess_blocket_category("Kala Ukulele med fodral", tradera_cat_id="210407")
    assert res2["sub"] == "Musikinstrument"

    res3 = guess_blocket_category("Decathlon Träningsmaskin", tradera_cat_id=None)
    assert res3["main"] == "Sport och friluftsliv"
    assert res3["sub"] == "Träningsmaskiner och -redskap"

def test_formatter():
    title = format_blocket_title("En väldigt lång titel som kanske överskrider gränsen för vad som är lämpligt", max_length=30)
    assert len(title) <= 30
    assert title.endswith("...")

    desc = format_blocket_description({
        "description": "Klassisk skjorta.",
        "attributes": {"Storlek": "M", "Färg": "Blå"}
    })
    assert "Klassisk skjorta." in desc
    assert "• Storlek: M" in desc
    assert "• Färg: Blå" in desc
    assert "Stockholm (Odenplan)" in desc
