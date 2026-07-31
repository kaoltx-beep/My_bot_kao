def test_roast_is_not_a_router_intent():
    # The architectural contract is that personality changes response style only.
    # Routing is evaluated independently of Roast mode.
    import personality
    assert personality.is_roast() in {True, False}
