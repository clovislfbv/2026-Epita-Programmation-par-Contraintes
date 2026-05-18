import pytest
from solver.grid import Grid
from solver.mapf import Drone
from solver.od_astar import ODAstarSolver


def test_od_single_drone():
    g = Grid(rows=4, cols=4)
    sol = ODAstarSolver(g, [Drone(0, (0, 0), (3, 3))]).solve()
    assert sol.status == "optimal"
    assert sol.paths[0][-1] == (3, 3)


def test_od_two_drones_no_vertex_conflict():
    g = Grid(rows=4, cols=4)
    drones = [Drone(0, (0, 0), (3, 3)), Drone(1, (3, 3), (0, 0))]
    sol = ODAstarSolver(g, drones).solve()
    assert sol.status == "optimal"
    max_t = max(len(p) for p in sol.paths.values())
    for t in range(max_t):
        positions = [sol.paths[d.id][min(t, len(sol.paths[d.id]) - 1)] for d in drones]
        assert len(positions) == len(set(positions))


def test_od_all_goals_reached():
    g = Grid(rows=5, cols=5)
    drones = [Drone(0, (0, 0), (4, 4)), Drone(1, (0, 4), (4, 0))]
    sol = ODAstarSolver(g, drones).solve()
    assert sol.status == "optimal"
    for d in drones:
        assert sol.paths[d.id][-1] == d.goal


def test_od_timeout():
    g = Grid(rows=5, cols=5)
    drones = [Drone(0, (0, 0), (4, 4)), Drone(1, (0, 4), (4, 0))]
    sol = ODAstarSolver(g, drones, time_limit_s=0.0).solve()
    assert sol.status == "timeout"
