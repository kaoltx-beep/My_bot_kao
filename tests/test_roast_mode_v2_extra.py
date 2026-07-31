from core.response_style import valid_base_reply, valid_roast_reply


def test_base_reply_rejects_empty_and_ack_only():
    assert not valid_base_reply("")
    assert not valid_base_reply("รับทราบครับ")
    assert valid_base_reply("เช้านี้กินข้าวกับไข่เจียวก็ได้ครับ")


def test_roast_reply_must_preserve_content():
    base = "เช้านี้กินข้าวกับไข่เจียวก็ได้ครับ"
    assert valid_roast_reply("ตอนเช้าทำอะไรกินดี", base, "เช้านี้กินข้าวกับไข่เจียวก็ได้ครับ ไอ้หิว")
    assert not valid_roast_reply("ตอนเช้าทำอะไรกินดี", base, "ไปนอนก่อนครับ เดี๋ยวค่อยคิด")
