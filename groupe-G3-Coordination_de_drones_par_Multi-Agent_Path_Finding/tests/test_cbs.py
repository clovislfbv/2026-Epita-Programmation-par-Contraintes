import pytest
from solver.grid import Grid
from solver.mapf import Drone
from solver.cbs import astar_spacetime, find_first_conflict, CBSSolver


def test_spacetime_no_constraints():
    g = Grid(rows=4, cols=4)
    path = astar_spacetime(g, (0, 0), (3, 3), set(), max_t=20)
    assert path is not None
    assert path[0] == (0, 0)
    assert path[-1] == (3, 3)
    assert len(path) - 1 == 6  # Manhattan distance (no detour)


def test_spacetime_avoids_constraint():
    g = Grid(rows=4, cols=4)
    # Block (0,1) at t=1 — agent must wait or go around
    path = astar_spacetime(g, (0, 0), (0, 2), {((0, 1), 1)}, max_t=20)
    assert path is not None
    assert path[-1] == (0, 2)
    if len(path) > 1:
        assert path[1] != (0, 1)


def test_find_vertex_conflict():
    paths = {0: [(0, 0), (1, 0), (2, 0)], 1: [(2, 2), (2, 1), (2, 0)]}
    c = find_first_conflict(paths)
    assert c is not None
    assert c[0] == 'vertex'
    assert c[3] == (2, 0)  # position
    assert c[4] == 2       # timestep


def test_find_edge_conflict():
    paths = {0: [(0, 0), (0, 1)], 1: [(0, 1), (0, 0)]}
    c = find_first_conflict(paths)
    assert c is not None
    assert c[0] == 'edge'


def test_no_conflict():
    paths = {0: [(0, 0), (1, 0), (2, 0)], 1: [(3, 3), (3, 2), (3, 1)]}
    assert find_first_conflict(paths) is None


def test_cbs_single_drone():
    g = Grid(rows=4, cols=4)
    sol = CBSSolver(g, [Drone(0, (0, 0), (3, 3))]).solve()
    assert sol.status == "optimal"
    assert sol.paths[0][-1] == (3, 3)


def test_cbs_two_drones_no_vertex_conflict():
    g = Grid(rows=4, cols=4)
    drones = [Drone(0, (0, 0), (3, 3)), Drone(1, (3, 3), (0, 0))]
    sol = CBSSolver(g, drones).solve()
    assert sol.status == "optimal"
    max_t = max(len(p) for p in sol.paths.values())
    for t in range(max_t):
        positions = [sol.paths[d.id][min(t, len(sol.paths[d.id]) - 1)] for d in drones]
        assert len(positions) == len(set(positions)), f"Vertex conflict at t={t}"


def test_cbs_all_goals_reached():
    g = Grid(rows=5, cols=5)
    drones = [Drone(0, (0, 0), (4, 4)), Drone(1, (0, 4), (4, 0)), Drone(2, (4, 0), (0, 4))]
    sol = CBSSolver(g, drones).solve()
    assert sol.status == "optimal"
    for d in drones:
        assert sol.paths[d.id][-1] == d.goal


def test_cbs_makespan_positive():
    g = Grid(rows=4, cols=4)
    drones = [Drone(0, (0, 0), (3, 3)), Drone(1, (3, 3), (0, 0))]
    sol = CBSSolver(g, drones).solve()
    assert sol.makespan > 0
