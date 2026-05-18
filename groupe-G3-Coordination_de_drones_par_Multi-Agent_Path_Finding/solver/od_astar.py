# solver/od_astar.py
from __future__ import annotations
import heapq
import time
from typing import Dict, List, Tuple
from .grid import Grid, Pos
from .astar import astar, heuristic, bfs_dist
from .mapf import Drone, Solution
from .cbs import _near_passes


class ODAstarSolver:
    """
    A* with Operator Decomposition for MAPF.

    State: (positions: Tuple[Pos,...], prev_positions: Tuple[Pos,...], agent_idx: int, t: int)
    - positions[i] is the NEW position for agent i if i < agent_idx,
      the CURRENT (old) position if i >= agent_idx.
    - prev_positions: positions at start of current timestep (for edge-conflict checks).
    - agent_idx == N means all agents have been assigned their next positions.

    Cost increments by 1 only when transitioning from agent_idx==N to agent_idx==0
    (one full timestep completed).

    Heuristic: sum of individual BFS distances from each agent's position to its goal.
    """

    def __init__(self, grid: Grid, drones: List[Drone], time_limit_s: float = 30.0):
        self.grid = grid
        self.drones = drones
        self.time_limit_s = time_limit_s

    def solve(self) -> Solution:
        t0 = time.time()
        N = len(self.drones)
        starts = tuple(d.start for d in self.drones)
        goals = tuple(d.goal for d in self.drones)
        drone_ids = [d.id for d in self.drones]

        h_maps = [bfs_dist(self.grid, goals[i]) for i in range(N)]
        INF = 10 ** 9

        def h(positions: Tuple[Pos, ...]) -> int:
            return sum(h_maps[i].get(positions[i], INF) for i in range(N))

        # State: (positions, prev_positions, agent_idx, t)
        init = (starts, starts, 0, 0)
        g_score: Dict = {init: 0}
        came_from: Dict = {init: None}
        counter = 0
        open_heap = [(h(starts), 0, counter, init)]

        while open_heap:
            if time.time() - t0 > self.time_limit_s:
                return Solution("timeout", 0, 0, (time.time() - t0) * 1000, {}, 0)

            _, g, _, state = heapq.heappop(open_heap)
            positions, prev_positions, agent_idx, t = state

            if g > g_score.get(state, INF):
                continue

            # Goal check: standard state (agent_idx==0) with all agents at goals
            if agent_idx == 0 and positions == goals:
                paths = _reconstruct(came_from, state, drone_ids)
                makespan = max(len(p) for p in paths.values()) - 1
                flowtime = sum(len(p) - 1 for p in paths.values())
                return Solution(
                    status="optimal",
                    makespan=makespan,
                    flowtime=flowtime,
                    solve_time_ms=(time.time() - t0) * 1000,
                    paths=paths,
                    conflicts_avoided=_near_passes(paths),
                )

            if agent_idx < N:
                # Assign next position for agent agent_idx
                agent_pos = positions[agent_idx]
                for nb in self.grid.neighbors(agent_pos):
                    # Vertex conflict: nb already assigned to an earlier agent
                    if any(nb == positions[j] for j in range(agent_idx)):
                        continue
                    # Edge conflict (swap) with earlier agents
                    if any(
                        nb == prev_positions[j] and positions[j] == prev_positions[agent_idx]
                        for j in range(agent_idx)
                    ):
                        continue

                    new_pos = list(positions)
                    new_pos[agent_idx] = nb
                    new_positions = tuple(new_pos)
                    new_idx = agent_idx + 1
                    # Cost increases by 1 only on full timestep completion
                    ng = g + (1 if new_idx == N else 0)
                    new_state = (new_positions, prev_positions, new_idx, t)

                    if ng < g_score.get(new_state, INF):
                        g_score[new_state] = ng
                        came_from[new_state] = state
                        counter += 1
                        heapq.heappush(
                            open_heap,
                            (ng + h(new_positions), ng, counter, new_state),
                        )

            else:
                # agent_idx == N: advance timestep
                new_state = (positions, positions, 0, t + 1)
                ng = g
                if ng < g_score.get(new_state, INF):
                    g_score[new_state] = ng
                    came_from[new_state] = state
                    counter += 1
                    heapq.heappush(
                        open_heap,
                        (ng + h(positions), ng, counter, new_state),
                    )

        return Solution("infeasible", 0, 0, (time.time() - t0) * 1000, {}, 0)


def _reconstruct(
    came_from: Dict,
    final_state: Tuple,
    drone_ids: List[int],
) -> Dict[int, List[Pos]]:
    """Walk came_from backwards, collect only standard states (agent_idx==0)."""
    standard_positions: List[Tuple[Pos, ...]] = []
    cur = final_state
    while cur is not None:
        positions, _, agent_idx, _ = cur
        if agent_idx == 0:
            standard_positions.append(positions)
        cur = came_from.get(cur)
    standard_positions.reverse()

    paths: Dict[int, List[Pos]] = {did: [] for did in drone_ids}
    for positions in standard_positions:
        for i, did in enumerate(drone_ids):
            paths[did].append(positions[i])
    return paths
