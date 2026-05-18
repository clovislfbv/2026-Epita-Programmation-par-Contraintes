# tests/test_mapf.py
import pytest
from solver.grid import Grid
from solver.mapf import Drone, MAPFSolver

def _no_vertex_conflicts(paths):
    drone_ids = list(paths.keys())
    max_t = max(len(p) for p in paths.values())
    for t in range(max_t):
        seen = {}
        for did in drone_ids:
            path = paths[did]
            pos = path[min(t, len(path) - 1)]
            assert pos not in seen, f"Vertex conflict at t={t}, pos={pos}"
            seen[pos] = did

def _no_edge_conflicts(paths):
    drone_ids = list(paths.keys())
    max_t = max(len(p) for p in paths.values())
    for t in range(max_t - 1):
        for i, a in enumerate(drone_ids):
            for b in drone_ids[i+1:]:
                pa_t  = paths[a][min(t,   len(paths[a])-1)]
                pa_t1 = paths[a][min(t+1, len(paths[a])-1)]
                pb_t  = paths[b][min(t,   len(paths[b])-1)]
                pb_t1 = paths[b][min(t+1, len(paths[b])-1)]
                assert not (pa_t == pb_t1 and pb_t == pa_t1), \
                    f"Edge conflict between drone {a} and {b} at t={t}"

def test_single_drone_reaches_goal():
    g = Grid(rows=4, cols=4)
    drones = [Drone(id=0, start=(0, 0), goal=(3, 3))]
    sol = MAPFSolver(g, drones).solve()
    assert sol.status in ("optimal", "feasible")
    assert sol.paths[0][-1] == (3, 3)

def test_two_drones_no_conflict():
    g = Grid(rows=4, cols=4)
    drones = [
        Drone(id=0, start=(0, 0), goal=(3, 3)),
        Drone(id=1, start=(3, 3), goal=(0, 0)),
    ]
    sol = MAPFSolver(g, drones).solve()
    assert sol.status in ("optimal", "feasible")
    _no_vertex_conflicts(sol.paths)
    _no_edge_conflicts(sol.paths)

def test_three_drones_no_conflict():
    g = Grid(rows=4, cols=4)
    drones = [
        Drone(id=0, start=(0, 0), goal=(0, 3)),
        Drone(id=1, start=(0, 3), goal=(3, 3)),
        Drone(id=2, start=(3, 3), goal=(0, 0)),
    ]
    sol = MAPFSolver(g, drones).solve()
    assert sol.status in ("optimal", "feasible")
    _no_vertex_conflicts(sol.paths)
    _no_edge_conflicts(sol.paths)

def test_makespan_is_optimal_single():
    g = Grid(rows=4, cols=4)
    drones = [Drone(id=0, start=(0, 0), goal=(0, 3))]
    sol = MAPFSolver(g, drones).solve()
    assert sol.makespan == 3

def test_grid_has_no_nofly_field():
    g = Grid(rows=4, cols=4)
    g.add_building(1, 1, 1)
    assert hasattr(g, 'obstacles')
    assert not hasattr(g, '_nofly')
    assert (1, 1) in g.obstacles

def test_all_drones_reach_goal():
    g = Grid(rows=5, cols=5)
    drones = [
        Drone(id=0, start=(0, 0), goal=(4, 4)),
        Drone(id=1, start=(0, 4), goal=(4, 0)),
        Drone(id=2, start=(4, 0), goal=(0, 4)),
    ]
    sol = MAPFSolver(g, drones).solve()
    assert sol.status in ("optimal", "feasible")
    for d in drones:
        assert sol.paths[d.id][-1] == d.goal

def test_cpsat_domain_reduction_correct_paths():
    """Vérifie que le refactor domain-reduction ne casse pas les résultats."""
    g = Grid(rows=5, cols=5)
    g.add_building(2, 2, 1)  # obstacle central
    drones = [
        Drone(id=0, start=(0, 0), goal=(4, 4)),
        Drone(id=1, start=(4, 0), goal=(0, 4)),
    ]
    sol = MAPFSolver(g, drones, time_limit_s=30).solve()
    assert sol.status in ("optimal", "feasible")
    for d in drones:
        assert sol.paths[d.id][-1] == d.goal
    # Aucun chemin ne passe par l'obstacle
    for path in sol.paths.values():
        assert (2, 2) not in path
    # Vérification absence de conflits
    _no_vertex_conflicts(sol.paths)
    _no_edge_conflicts(sol.paths)

def test_3d_solver_avoids_building():
    g = Grid(rows=6, cols=6, alts=3)
    g.add_building(row=3, col=3, height=2)  # blocks (3,3,0) and (3,3,1)
    drones = [
        Drone(id=0, start=(0, 0, 0), goal=(5, 5, 0)),
        Drone(id=1, start=(5, 0, 0), goal=(0, 5, 0)),
    ]
    sol = MAPFSolver(g, drones, time_limit_s=30).solve()
    assert sol.status in ("optimal", "feasible")
    for path in sol.paths.values():
        for pos in path:
            assert pos not in g.obstacles, f"Path through obstacle: {pos}"
