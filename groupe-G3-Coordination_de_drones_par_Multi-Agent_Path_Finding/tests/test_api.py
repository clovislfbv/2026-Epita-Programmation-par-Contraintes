import json
import pytest
from api.server import create_app
from api.scenario_loader import load_all

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_get_scenarios(client):
    r = client.get("/scenarios")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert isinstance(data, list)
    assert any(s["name"] == "micro_flat" for s in data)
    assert len(data) == 11

def test_solve_small(client):
    payload = {
        "grid": {"rows": 4, "cols": 4, "alts": 1},
        "drones": [
            {"id": 0, "start": [0, 0], "goal": [3, 3]},
            {"id": 1, "start": [3, 0], "goal": [0, 3]},
        ],
        "buildings": [],
        "time_limit_s": 15,
    }
    r = client.post("/solve", json=payload)
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["status"] in ("optimal", "feasible")
    assert "paths" in data
    assert "0" in data["paths"] and "1" in data["paths"]

def test_solve_returns_solve_time(client):
    payload = {
        "grid": {"rows": 4, "cols": 4, "alts": 1},
        "drones": [{"id": 0, "start": [0, 0], "goal": [3, 3]}],
        "buildings": [], "time_limit_s": 15,
    }
    r = client.post("/solve", json=payload)
    data = json.loads(r.data)
    assert "solve_time_ms" in data
    assert data["solve_time_ms"] > 0


def test_load_all_returns_eleven_scenarios():
    scenarios = load_all()
    assert len(scenarios) == 11


def test_each_scenario_has_required_keys():
    for s in load_all():
        assert "name" in s
        assert "description" in s
        assert "grid" in s
        assert "drones" in s
        assert "buildings" in s
        assert {"rows", "cols", "alts"} == set(s["grid"].keys())
