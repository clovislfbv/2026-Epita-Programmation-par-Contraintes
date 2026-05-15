# solver/cbs.py
from __future__ import annotations
import heapq
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from .grid import Grid, Pos
from .mapf import Drone, Solution
from .astar import heuristic

# A vertex constraint: agent must not be at pos at time t
Constraint = Tuple[Pos, int]


def astar_spacetime(
    grid: Grid,
    start: Pos,
    goal: Pos,
    constraints: Set[Constraint],
    max_t: int,
) -> Optional[List[Pos]]:
    """Space-time A* — finds shortest path from start to goal respecting constraints."""
    open_heap: list = []
    heapq.heappush(open_heap, (heuristic(start, goal), 0, start, 0))
    came_from: Dict[Tuple[Pos, int], Optional[Tuple[Pos, int]]] = {(start, 0): None}
    g_score: Dict[Tuple[Pos, int], int] = {(start, 0): 0}

    while open_heap:
        _, g, pos, t = heapq.heappop(open_heap)

        if pos == goal:
            path: List[Pos] = []
            state: Optional[Tuple[Pos, int]] = (pos, t)
            while state is not None:
                path.append(state[0])
                state = came_from.get(state)
            path.reverse()
            return path

        if g > g_score.get((pos, t), float('inf')):
            continue
        if t >= max_t:
            continue

        for nb in grid.neighbors(pos):  # includes wait move (nb == pos)
            nt = t + 1
            if (nb, nt) in constraints:
                continue
            ng = g + 1
            new_state = (nb, nt)
            if ng < g_score.get(new_state, float('inf')):
                g_score[new_state] = ng
                came_from[new_state] = (pos, t)
                heapq.heappush(open_heap, (ng + heuristic(nb, goal), ng, nb, nt))

    return None


def find_first_conflict(paths: Dict[int, List[Pos]]):
    """
    Returns the first conflict found, or None.
    Vertex conflict: ('vertex', agent_a, agent_b, pos, t)
    Edge conflict:   ('edge',   agent_a, agent_b, pos_a, pos_b, t)
    """
    if not paths:
        return None
    ids = list(paths.keys())
    max_t = max(len(p) for p in paths.values())

    for t in range(max_t):
        for i, a in enumerate(ids):
            pa = paths[a][min(t, len(paths[a]) - 1)]
            for b in ids[i + 1:]:
                pb = paths[b][min(t, len(paths[b]) - 1)]
                if pa == pb:
                    return ('vertex', a, b, pa, t)
                if t + 1 < len(paths[a]) and t + 1 < len(paths[b]):
                    pa1 = paths[a][t + 1]
                    pb1 = paths[b][t + 1]
                    if pa == pb1 and pb == pa1:
                        return ('edge', a, b, pa, pb, t)
    return None
