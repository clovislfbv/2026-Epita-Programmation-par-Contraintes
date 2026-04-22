from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from ortools.sat.python import cp_model
from .grid import Grid, Pos
from .astar import astar


@dataclass
class Drone:
    id: int
    start: Pos
    goal: Pos


@dataclass
class Solution:
    status: str
    makespan: int
    solve_time_ms: float
    paths: Dict[int, List[Pos]]
    conflicts_avoided: int


class MAPFSolver:
    def __init__(self, grid: Grid, drones: List[Drone], time_limit_s: float = 10.0):
        self.grid = grid
        self.drones = drones
        self.time_limit_s = time_limit_s

    def solve(self) -> Solution:
        positions = self.grid.positions
        pos_to_idx = {p: i for i, p in enumerate(positions)}
        N = len(self.drones)
        P = len(positions)

        # A* individual paths — tighten horizon and provide warm-start hints
        astar_paths: List[Optional[List[Pos]]] = [
            astar(self.grid, d.start, d.goal) for d in self.drones
        ]
        # Horizon: max individual A* path + slack (agents need to wait for each other)
        # Slack = N-1 covers the worst case where all agents block one agent sequentially
        astar_lens = [len(p) - 1 for p in astar_paths if p is not None]
        if astar_lens:
            T = max(astar_lens) + max(N - 1, 3)
        else:
            T = 2 * (self.grid.rows + self.grid.cols) + N

        model = cp_model.CpModel()
        t0 = time.time()

        x = [
            [[model.NewBoolVar(f'x_{a}_{p}_{t}') for t in range(T + 1)]
             for p in range(P)]
            for a in range(N)
        ]

        nbrs: List[List[int]] = [
            [pos_to_idx[nb] for nb in self.grid.neighbors(positions[p]) if nb in pos_to_idx]
            for p in range(P)
        ]

        for a in range(N):
            for t in range(T + 1):
                model.AddExactlyOne(x[a][p][t] for p in range(P))

        for a, drone in enumerate(self.drones):
            start_idx = pos_to_idx.get(drone.start)
            if start_idx is None:
                return Solution("infeasible", 0, 0.0, {}, 0)
            model.Add(x[a][start_idx][0] == 1)

        for a in range(N):
            for t in range(T):
                for p in range(P):
                    model.Add(sum(x[a][q][t + 1] for q in nbrs[p]) >= x[a][p][t])

        for t in range(T + 1):
            for p in range(P):
                model.AddAtMostOne(x[a][p][t] for a in range(N))

        for t in range(T):
            for a in range(N):
                for b in range(a + 1, N):
                    for p in range(P):
                        for q in nbrs[p]:
                            model.Add(
                                x[a][p][t] + x[b][q][t] +
                                x[a][q][t + 1] + x[b][p][t + 1] <= 3
                            )

        for a, drone in enumerate(self.drones):
            goal_idx = pos_to_idx.get(drone.goal)
            if goal_idx is None:
                return Solution("infeasible", 0, 0.0, {}, 0)
            for t in range(T):
                model.Add(x[a][goal_idx][t + 1] >= x[a][goal_idx][t])

        makespan_var = model.NewIntVar(0, T, 'makespan')
        arrival_vars = []
        for a, drone in enumerate(self.drones):
            goal_idx = pos_to_idx[drone.goal]
            arr = model.NewIntVar(0, T, f'arrival_{a}')
            model.Add(arr == T + 1 - sum(x[a][goal_idx][t] for t in range(T + 1)))
            arrival_vars.append(arr)
        model.AddMaxEquality(makespan_var, arrival_vars)
        model.Minimize(makespan_var)

        # Warm-start: inject A* individual paths as hints for CP-SAT
        for a, path in enumerate(astar_paths):
            if path is None:
                continue
            for t in range(T + 1):
                pos = path[min(t, len(path) - 1)]  # stay at goal after arrival
                hint_idx = pos_to_idx.get(pos)
                if hint_idx is None:
                    continue
                for p in range(P):
                    model.AddHint(x[a][p][t], 1 if p == hint_idx else 0)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_s
        solver.parameters.num_search_workers = 4

        status_code = solver.Solve(model)
        solve_time_ms = (time.time() - t0) * 1000

        status_map = {
            cp_model.OPTIMAL: "optimal",
            cp_model.FEASIBLE: "feasible",
            cp_model.INFEASIBLE: "infeasible",
            cp_model.UNKNOWN: "timeout",
            cp_model.MODEL_INVALID: "infeasible",
        }

        if status_code not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return Solution(status_map.get(status_code, "unknown"), 0, solve_time_ms, {}, 0)

        makespan_val = int(solver.ObjectiveValue())

        paths: Dict[int, List[Pos]] = {}
        for a, drone in enumerate(self.drones):
            path: List[Pos] = []
            for t in range(makespan_val + 1):
                for p in range(P):
                    if solver.Value(x[a][p][t]):
                        path.append(positions[p])
                        break
            paths[drone.id] = path

        return Solution(
            status=status_map.get(status_code, "unknown"),
            makespan=makespan_val,
            solve_time_ms=solve_time_ms,
            paths=paths,
            conflicts_avoided=self._near_passes(paths),
        )

    def _near_passes(self, paths: Dict[int, List[Pos]]) -> int:
        ids = list(paths.keys())
        max_t = max(len(p) for p in paths.values())
        count = 0
        for t in range(max_t):
            for i, a in enumerate(ids):
                for b in ids[i + 1:]:
                    pa = paths[a][min(t, len(paths[a]) - 1)]
                    pb = paths[b][min(t, len(paths[b]) - 1)]
                    dist = sum(abs(pa[k] - pb[k]) for k in range(len(pa)))
                    if dist == 1:
                        count += 1
        return count
