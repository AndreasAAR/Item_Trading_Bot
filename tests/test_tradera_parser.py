from src.tradera.parser import TraderaParser

SAMPLE_PROFILE_HTML = """
<html>
<body>
    <div id="item-card-754152529" data-item-card-id="754152529" data-item-type="PureBin">
        <a href="/item/1000678/754152529/uniqlo-denim-bla-skjorta-storlek-m">UNIQLO denim blå skjorta, storlek M</a>
        <img src="https://img.tradera.net/small-square/079/test.jpg" />
        <div>Pris: 199 kr</div>
        <div>Eller Köp nu: 299 kr</div>
    </div>
</body>
</html>
"""

SAMPLE_ITEM_HTML = """
<html>
<body>
    <h1>UNIQLO denim blå skjorta, storlek M</h1>
    <div id="item-description">Fin blå skjorta från Uniqlo i bra skick.</div>
    <img src="https://img.tradera.net/large-fit/079/test1.jpg" />
    <img src="https://img.tradera.net/small-square/079/test2.jpg" />
    <dl>
        <dt>Varumärke</dt><dd>Uniqlo</dd>
        <dt>Klädstorlek</dt><dd>M</dd>
    </dl>
    <div>Köp nu: 299 kr</div>
    <div>Frakt: 59 kr</div>
</body>
</html>
"""

def test_parse_profile():
    items = TraderaParser.parse_profile_page(SAMPLE_PROFILE_HTML)
    assert len(items) == 1
    item = items[0]
    assert item.item_id == "754152529"
    assert "UNIQLO" in item.title
    assert item.buy_now_price == 299
    assert item.starting_price == 199

def test_parse_item_page():
    detail = TraderaParser.parse_item_page(SAMPLE_ITEM_HTML, "https://www.tradera.com/item/1000678/754152529/slug")
    assert detail.item_id == "754152529"
    assert "uniqlo" in detail.title.lower()
    assert "Fin blå skjorta" in detail.description
    assert len(detail.images) == 2
    assert all("large-fit" in img for img in detail.images)
    assert detail.attributes.get("Varumärke") == "Uniqlo"
    assert detail.attributes.get("Klädstorlek") == "M"
    assert detail.buy_now_price == 299
    assert detail.target_blocket_price == 299
