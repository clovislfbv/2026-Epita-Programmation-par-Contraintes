# tests/test_grid.py
import pytest
from solver.grid import Grid

def test_2d_positions_excludes_obstacles():
    g = Grid(rows=4, cols=4)
    g.obstacles.add((1, 1))
    assert (1, 1) not in g.positions
    assert len(g.positions) == 15

def test_2d_neighbors_center():
    g = Grid(rows=4, cols=4)
    nbrs = g.neighbors((1, 1))
    assert set(nbrs) == {(0,1), (2,1), (1,0), (1,2), (1,1)}  # 4-connected + wait

def test_2d_neighbors_corner():
    g = Grid(rows=4, cols=4)
    nbrs = g.neighbors((0, 0))
    assert set(nbrs) == {(0,0), (1,0), (0,1)}

def test_2d_neighbors_skip_obstacle():
    g = Grid(rows=4, cols=4)
    g.obstacles.add((0, 1))
    nbrs = g.neighbors((0, 0))
    assert (0, 1) not in nbrs

def test_2d_obstacle_excludes_positions():
    g = Grid(rows=4, cols=4)
    for r in range(1, 3):
        for c in range(1, 3):
            g.obstacles.add((r, c))
    for r in range(1, 3):
        for c in range(1, 3):
            assert (r, c) not in g.positions

def test_3d_positions():
    g = Grid(rows=4, cols=4, alts=3)
    assert len(g.positions) == 48

def test_3d_neighbors_include_altitude():
    g = Grid(rows=4, cols=4, alts=3)
    nbrs = g.neighbors((1, 1, 1))
    assert (1, 1, 0) in nbrs
    assert (1, 1, 2) in nbrs

def test_3d_neighbors_no_alt_below_zero():
    g = Grid(rows=4, cols=4, alts=3)
    nbrs = g.neighbors((1, 1, 0))
    assert (1, 1, -1) not in nbrs

def test_add_building():
    g = Grid(rows=4, cols=4, alts=4)
    g.add_building(row=2, col=2, height=3)
    for a in range(3):
        assert (2, 2, a) in g.obstacles
    assert (2, 2, 3) not in g.obstacles

def test_add_building_2d():
    g = Grid(rows=4, cols=4)          # alts=1 par défaut
    g.add_building(row=1, col=2, height=1)
    assert (1, 2) not in g.positions
    assert len(g.positions) == 15     # 16 - 1 obstacle
