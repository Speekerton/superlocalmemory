"""Forward-compatible Hopfield settings survive copying a loaded config."""

import json

from superlocalmemory.core.config import SLMConfig


def test_unknown_hopfield_keys_survive_save_to_new_path(tmp_path):
    source = tmp_path / "config.json"
    section = {"enabled": False, "future_kernel": {"beta": 7}, "vendor": [1, 2]}
    source.write_text(json.dumps({"mode": "a", "hopfield": section}))
    config = SLMConfig.load(source)
    destination = tmp_path / "copy" / "config.json"
    config.save(destination)
    assert json.loads(destination.read_text())["hopfield"] == section
