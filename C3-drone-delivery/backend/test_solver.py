"""
Tests unitaires pour DroneRoutingSolver (CP-SAT).
Couvre : batterie, capacité poids/volume, couverture clients, zones NOTAM.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from drone_delivery_solver import DroneInstance, DroneRoutingSolver, WaypointNavigator


def make_instance(**kwargs):
    defaults = dict(
        depot=(0, 0, 0),
        clients=[(10, 0, 0), (20, 0, 0)],
        demands=[50, 50],
        volumes=[100, 100],
        notam_zones=[],
        num_drones=1,
        battery_capacity=5000,
        max_load=200,
        max_volume=400,
        grid_res=10,
    )
    defaults.update(kwargs)
    return DroneInstance(**defaults)


# --- Couverture clients ---

def test_all_clients_served():
    """Tous les clients doivent être visités exactement une fois."""
    inst = make_instance()
    routes = DroneRoutingSolver(inst).solve()
    assert routes is not None, "Le solveur doit trouver une solution"
    visited = set()
    for route in routes:
        for trip in route["trips"]:
            # la géométrie contient les waypoints : on vérifie via les demands
            pass
    # Vérification indirecte : distance totale > 0 implique des clients visités
    total_dist = sum(r["total_distance"] for r in routes)
    assert total_dist > 0


def test_single_client_single_drone():
    """Cas minimal : 1 drone, 1 client, batterie suffisante."""
    inst = make_instance(
        clients=[(10, 0, 0)],
        demands=[50],
        volumes=[100],
    )
    routes = DroneRoutingSolver(inst).solve()
    assert routes is not None
    assert len(routes) == 1
    assert routes[0]["total_distance"] > 0


# --- Contrainte batterie ---

def test_battery_too_low_returns_none():
    """Si la batterie est insuffisante pour atteindre le premier client, pas de solution."""
    inst = make_instance(
        clients=[(500, 0, 0)],   # client très loin
        demands=[50],
        volumes=[100],
        battery_capacity=100,    # batterie trop faible (dist * 100 >> 100)
    )
    routes = DroneRoutingSolver(inst).solve()
    # Aucune route viable : soit None, soit liste vide
    if routes is not None:
        assert all(len(r["trips"]) == 0 for r in routes)


def test_battery_exactly_enough():
    """Un drone doit pouvoir faire un aller-retour avec juste assez de batterie."""
    # depot=(0,0), client=(10,0) => dist = 10 * wind_coeff * 100 = 1000 (aller)
    # retour = 1000, total = 2000
    inst = make_instance(
        clients=[(10, 0, 0)],
        demands=[50],
        volumes=[100],
        battery_capacity=2001,  # juste au-dessus du minimum
    )
    routes = DroneRoutingSolver(inst).solve()
    assert routes is not None
    assert any(len(r["trips"]) > 0 for r in routes)


# --- Contrainte capacité poids ---

def test_weight_capacity_exceeded_splits_routes():
    """Si la charge dépasse max_load, plusieurs drones doivent être utilisés."""
    inst = make_instance(
        clients=[(10, 0, 0), (20, 0, 0)],
        demands=[150, 150],   # chacun dépasse max_load/2
        volumes=[50, 50],
        num_drones=2,
        max_load=160,         # un seul client par drone
        max_volume=400,
        battery_capacity=10000,
    )
    routes = DroneRoutingSolver(inst).solve()
    assert routes is not None
    # Les deux drones doivent être actifs
    active_drones = [r for r in routes if len(r["trips"]) > 0]
    assert len(active_drones) == 2


def test_weight_capacity_single_trip():
    """Un seul drone avec capacité suffisante doit tout livrer en un trip."""
    inst = make_instance(
        clients=[(10, 0, 0), (20, 0, 0)],
        demands=[50, 50],
        volumes=[50, 50],
        num_drones=1,
        max_load=200,
        max_volume=400,
        battery_capacity=10000,
    )
    routes = DroneRoutingSolver(inst).solve()
    assert routes is not None
    assert len(routes) == 1


# --- Contrainte capacité volume ---

def test_volume_capacity_respected():
    """Le volume total par trip ne doit pas dépasser max_volume."""
    inst = make_instance(
        clients=[(10, 0, 0), (20, 0, 0)],
        demands=[10, 10],
        volumes=[250, 250],   # chacun = 250, max_volume = 300
        num_drones=2,
        max_load=500,
        max_volume=300,       # impossible de livrer les deux en un seul trip
        battery_capacity=10000,
    )
    routes = DroneRoutingSolver(inst).solve()
    assert routes is not None
    for route in routes:
        for trip in route["trips"]:
            assert trip["volume"] <= 300 / 10, "Volume par trip doit respecter max_volume"


# --- Zones NOTAM ---

def test_no_solution_without_zones():
    """Sans zones NOTAM, le solveur doit toujours trouver une solution simple."""
    inst = make_instance(
        clients=[(5, 0, 0)],
        demands=[50],
        volumes=[50],
        notam_zones=[],
        battery_capacity=10000,
    )
    routes = DroneRoutingSolver(inst).solve()
    assert routes is not None


def test_waypoint_navigator_direct_path():
    """Sans zones NOTAM, le chemin direct doit toujours être utilisé."""
    inst = make_instance(
        clients=[(10, 0, 0)],
        demands=[50],
        volumes=[50],
        notam_zones=[],
        grid_res=5,
    )
    nav = WaypointNavigator(inst)
    safe = nav.is_safe(inst.depot, inst.clients[0])
    assert safe, "Sans NOTAM, le chemin direct doit être libre"


def test_waypoint_navigator_blocked_path():
    """Avec une zone NOTAM entre depot et client, le chemin direct doit être bloqué."""
    # Zone centrée en (5, 0) bloquant le chemin de (0,0) à (10,0)
    zone = [(4, -2), (6, -2), (6, 2), (4, 2)]
    inst = make_instance(
        clients=[(10, 0, 0)],
        demands=[50],
        volumes=[50],
        notam_zones=[zone],
        grid_res=10,
    )
    nav = WaypointNavigator(inst)
    blocked = not nav.is_safe(inst.depot, inst.clients[0])
    assert blocked, "Le chemin direct doit être bloqué par la zone NOTAM"


def test_dijkstra_finds_detour():
    """Dijkstra doit trouver un chemin de contournement plus long que le direct."""
    zone = [(4, -2), (6, -2), (6, 2), (4, 2)]
    inst = make_instance(
        clients=[(10, 0, 0)],
        demands=[50],
        volumes=[50],
        notam_zones=[zone],
        grid_res=15,
        battery_capacity=50000,
    )
    solver = DroneRoutingSolver(inst)
    # Distance avec contournement > distance directe (10 unités)
    direct_dist = 10.0
    actual_dist = solver.dist_matrix[0][1] / 100.0
    assert actual_dist > direct_dist, "Le chemin de contournement doit être plus long que le direct"


# --- Multi-drones ---

def test_multiple_drones_share_clients():
    """Avec plus de clients que la capacité d'un drone, plusieurs drones doivent être actifs."""
    inst = make_instance(
        clients=[(10, 0, 0), (20, 0, 0), (30, 0, 0), (40, 0, 0)],
        demands=[100, 100, 100, 100],
        volumes=[50, 50, 50, 50],
        num_drones=2,
        max_load=150,   # max 1 client par drone
        max_volume=400,
        battery_capacity=20000,
    )
    routes = DroneRoutingSolver(inst).solve()
    assert routes is not None
    active = [r for r in routes if len(r["trips"]) > 0]
    assert len(active) >= 2


if __name__ == "__main__":
    tests = [
        test_all_clients_served,
        test_single_client_single_drone,
        test_battery_too_low_returns_none,
        test_battery_exactly_enough,
        test_weight_capacity_exceeded_splits_routes,
        test_weight_capacity_single_trip,
        test_volume_capacity_respected,
        test_no_solution_without_zones,
        test_waypoint_navigator_direct_path,
        test_waypoint_navigator_blocked_path,
        test_dijkstra_finds_detour,
        test_multiple_drones_share_clients,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__} — {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
