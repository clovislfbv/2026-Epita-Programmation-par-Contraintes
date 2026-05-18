# solver/cbs.py
from __future__ import annotations
import heapq
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from .grid import Grid, Pos
from .mapf import Drone, Solution
from .astar import astar, heuristic

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


def _near_passes(paths: Dict[int, List[Pos]]) -> int:
    """Count (agent-pair, timestep) instances where two agents are in adjacent cells."""
    ids = list(paths.keys())
    if not ids:
        return 0
    max_t = max(len(p) for p in paths.values())
    count = 0
    for t in range(max_t):
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                pa = paths[a][min(t, len(paths[a]) - 1)]
                pb = paths[b][min(t, len(paths[b]) - 1)]
                if sum(abs(pa[k] - pb[k]) for k in range(len(pa))) == 1:
                    count += 1
    return count


def _count_conflicts(paths: Dict[int, List[Pos]]) -> int:
    """Count total conflicts in paths (used as ECBS tie-breaker)."""
    ids = list(paths.keys())
    if not ids:
        return 0
    max_t = max(len(p) for p in paths.values())
    count = 0
    for t in range(max_t):
        for i, a in enumerate(ids):
            pa = paths[a][min(t, len(paths[a]) - 1)]
            for b in ids[i + 1:]:
                pb = paths[b][min(t, len(paths[b]) - 1)]
                if pa == pb:
                    count += 1
                if t + 1 < len(paths[a]) and t + 1 < len(paths[b]):
                    pa1 = paths[a][t + 1]
                    pb1 = paths[b][t + 1]
                    if pa == pb1 and pb == pa1:
                        count += 1
    return count


@dataclass
class _CTNode:
    constraints: Dict[int, Set[Constraint]]
    paths: Dict[int, List[Pos]]
    cost: int  # sum of individual path lengths


def _compute_max_t(grid: Grid, drones: List[Drone]) -> int:
    lens = [len(astar(grid, d.start, d.goal) or [(None,)]) - 1 for d in drones]
    valid = [l for l in lens if l >= 0]
    return (max(valid) if valid else 0) + 2 * len(drones) + 10


class CBSSolver:
    def __init__(self, grid: Grid, drones: List[Drone], time_limit_s: float = 30.0):
        self.grid = grid
        self.drones = drones
        self.time_limit_s = time_limit_s

    def solve(self) -> Solution:
        t0 = time.time()
        max_t = _compute_max_t(self.grid, self.drones)
        counter = 0

        root_constraints: Dict[int, Set[Constraint]] = {d.id: set() for d in self.drones}
        root_paths: Dict[int, List[Pos]] = {}
        for drone in self.drones:
            path = astar_spacetime(self.grid, drone.start, drone.goal, set(), max_t)
            if path is None:
                return Solution("infeasible", 0, 0, (time.time() - t0) * 1000, {}, 0)
            root_paths[drone.id] = path

        root = _CTNode(root_constraints, root_paths, sum(len(p) for p in root_paths.values()))
        open_list: list = [(root.cost, counter, root)]
        counter += 1

        while open_list:
            if time.time() - t0 > self.time_limit_s:
                return Solution("timeout", 0, 0, (time.time() - t0) * 1000, {}, 0)

            _, _, node = heapq.heappop(open_list)
            conflict = find_first_conflict(node.paths)

            if conflict is None:
                makespan = max(len(p) for p in node.paths.values()) - 1
                flowtime = sum(len(p) - 1 for p in node.paths.values())
                return Solution(
                    status="optimal",
                    makespan=makespan,
                    flowtime=flowtime,
                    solve_time_ms=(time.time() - t0) * 1000,
                    paths=node.paths,
                    conflicts_avoided=_near_passes(node.paths),
                )

            if conflict[0] == 'vertex':
                _, a, b, pos, t = conflict
                new_constraints_list = [(a, (pos, t)), (b, (pos, t))]
            else:
                _, a, b, pos_a, pos_b, t = conflict
                new_constraints_list = [(a, (pos_b, t + 1)), (b, (pos_a, t + 1))]

            for agent_id, new_con in new_constraints_list:
                new_constraints = {d.id: set(node.constraints[d.id]) for d in self.drones}
                new_constraints[agent_id].add(new_con)
                drone = next(d for d in self.drones if d.id == agent_id)
                new_path = astar_spacetime(
                    self.grid, drone.start, drone.goal, new_constraints[agent_id], max_t
                )
                if new_path is None:
                    continue
                new_paths = dict(node.paths)
                new_paths[agent_id] = new_path
                child = _CTNode(new_constraints, new_paths, sum(len(p) for p in new_paths.values()))
                heapq.heappush(open_list, (child.cost, counter, child))
                counter += 1

        return Solution("infeasible", 0, 0, (time.time() - t0) * 1000, {}, 0)


class ECBSSolver:
    """
    Enhanced CBS: picks from FOCAL (nodes with cost <= w * f_min) the node with
    fewest conflicts. Guarantees w-suboptimal solution. w=1.0 reduces to CBS.
    """
    def __init__(self, grid: Grid, drones: List[Drone], w: float = 1.3, time_limit_s: float = 30.0):
        self.grid = grid
        self.drones = drones
        self.w = w
        self.time_limit_s = time_limit_s

    def solve(self) -> Solution:
        t0 = time.time()
        max_t = _compute_max_t(self.grid, self.drones)
        counter = 0

        root_constraints: Dict[int, Set[Constraint]] = {d.id: set() for d in self.drones}
        root_paths: Dict[int, List[Pos]] = {}
        for drone in self.drones:
            path = astar_spacetime(self.grid, drone.start, drone.goal, set(), max_t)
            if path is None:
                return Solution("infeasible", 0, 0, (time.time() - t0) * 1000, {}, 0)
            root_paths[drone.id] = path

        root = _CTNode(root_constraints, root_paths, sum(len(p) for p in root_paths.values()))
        open_list: List[Tuple[int, int, _CTNode]] = [(root.cost, counter, root)]
        counter += 1
        deleted_ids: set = set()

        while open_list:
            if time.time() - t0 > self.time_limit_s:
                return Solution("timeout", 0, 0, (time.time() - t0) * 1000, {}, 0)

            # Suppression paresseuse — retire les entrées supprimées du sommet
            while open_list and open_list[0][1] in deleted_ids:
                _, nid, _ = heapq.heappop(open_list)
                deleted_ids.discard(nid)
            if not open_list:
                break

            f_min = open_list[0][0]  # O(1) — le heap garantit le minimum en tête
            focal = [
                (c, nid, n) for c, nid, n in open_list
                if nid not in deleted_ids and c <= self.w * f_min
            ]

            _, chosen_id, node = min(focal, key=lambda x: _count_conflicts(x[2].paths))
            deleted_ids.add(chosen_id)

            conflict = find_first_conflict(node.paths)
            if conflict is None:
                makespan = max(len(p) for p in node.paths.values()) - 1
                flowtime = sum(len(p) - 1 for p in node.paths.values())
                return Solution(
                    status="feasible",
                    makespan=makespan,
                    flowtime=flowtime,
                    solve_time_ms=(time.time() - t0) * 1000,
                    paths=node.paths,
                    conflicts_avoided=_near_passes(node.paths),
                )

            if conflict[0] == 'vertex':
                _, a, b, pos, t = conflict
                new_constraints_list = [(a, (pos, t)), (b, (pos, t))]
            else:
                _, a, b, pos_a, pos_b, t = conflict
                new_constraints_list = [(a, (pos_b, t + 1)), (b, (pos_a, t + 1))]

            for agent_id, new_con in new_constraints_list:
                new_constraints = {d.id: set(node.constraints[d.id]) for d in self.drones}
                new_constraints[agent_id].add(new_con)
                drone = next(d for d in self.drones if d.id == agent_id)
                new_path = astar_spacetime(
                    self.grid, drone.start, drone.goal, new_constraints[agent_id], max_t
                )
                if new_path is None:
                    continue
                new_paths = dict(node.paths)
                new_paths[agent_id] = new_path
                child = _CTNode(new_constraints, new_paths, sum(len(p) for p in new_paths.values()))
                heapq.heappush(open_list, (child.cost, counter, child))
                counter += 1

        return Solution("infeasible", 0, 0, (time.time() - t0) * 1000, {}, 0)
