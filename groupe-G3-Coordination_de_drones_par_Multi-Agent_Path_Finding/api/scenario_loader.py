import json
import pathlib

SCENARIOS_DIR = pathlib.Path(__file__).parent.parent / "scenarios"


def load_all():
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(SCENARIOS_DIR.glob("*.json"))
    ]
