from src.mapper.category_mapper import guess_blocket_category, map_condition, map_color

def test_shoe_category_mapping():
    # Trail shoes / running shoes -> Sport och friluftsliv -> Träningskläder och skor
    res1 = guess_blocket_category("Kalenji XT7 löparskor trailskor svart gul strl 41")
    assert res1["main"] == "Sport och friluftsliv"
    assert res1["sub"] == "Träningskläder och skor"

    res2 = guess_blocket_category("Nike Pegasus Trail 5 Gore-Tex löparskor, svarta, storlek 43")
    assert res2["main"] == "Sport och friluftsliv"
    assert res2["sub"] == "Träningskläder och skor"

    # Regular dress shoes -> Herrskor
    res3 = guess_blocket_category("Steptronic Falcon finskor - Brun - Storlek 41")
    assert res3["main"] == "Kläder, kosmetika och accessoarer"
    assert res3["sub"] == "Skor"
    assert res3["prod"] == "Herrskor"

def test_condition_mapping():
    assert map_condition("Mycket bra skick") == "Mycket bra skick - som ny"
    assert map_condition("Gott skick") == "Bra skick - varsamt använd"
    assert map_condition(None) == "Bra skick - varsamt använd"
    assert map_condition("oanvänt") == "Nytt skick - helt ny"

def test_color_mapping():
    assert map_color("svart") == "Svart"
    assert map_color("ljusblå") == "Blå"
    assert map_color("mörkgrå") == "Grå"
    assert map_color("random") is None
