import json

import personality


def test_mode_persists(tmp_path, monkeypatch):
    mode_file = tmp_path / "jarvis_mode.json"
    monkeypatch.setattr(personality, "MODE_FILE", str(mode_file))

    assert personality.set_mode("ROAST") is True
    assert personality.is_roast() is True

    data = json.loads(mode_file.read_text(encoding="utf-8"))
    assert data["mode"] == "ROAST"

    assert personality.set_mode("NORMAL") is True
    assert personality.is_roast() is False
