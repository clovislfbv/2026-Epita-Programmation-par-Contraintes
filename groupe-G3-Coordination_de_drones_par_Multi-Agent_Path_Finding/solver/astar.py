from __future__ import annotations
import heapq
from typing import Dict, List, Optional
from .grid import Grid, Pos


def heuristic(a: Pos, b: Pos) -> int:
    return sum(abs(a[i] - b[i]) for i in range(len(a)))


def astar(grid: Grid, start: Pos, goal: Pos) -> Optional[List[Pos]]:
    """Shortest path for a single agent, ignoring other agents."""
    open_heap: list = []
    heapq.heappush(open_heap, (heuristic(start, goal), 0, start))
    came_from: Dict[Pos, Optional[Pos]] = {start: None}
    g_score: Dict[Pos, int] = {start: 0}

    while open_heap:
        _, g, current = heapq.heappop(open_heap)

        if current == goal:
            path = []
            node: Optional[Pos] = current
            while node is not None:
                path.append(node)
                node = came_from[node]
            path.reverse()
            return path

        if g > g_score.get(current, float('inf')):
            continue

        for nb in grid.neighbors(current):
            if nb == current:
                continue  # skip wait moves — we want shortest path length
            ng = g + 1
            if ng < g_score.get(nb, float('inf')):
                g_score[nb] = ng
                came_from[nb] = current
                heapq.heappush(open_heap, (ng + heuristic(nb, goal), ng, nb))

    return None  # no path found


def bfs_dist(grid: Grid, goal: Pos) -> Dict[Pos, int]:
    """BFS depuis le but — retourne le nombre minimal de pas depuis chaque position."""
    dist: Dict[Pos, int] = {goal: 0}
    queue = [goal]
    while queue:
        nxt = []
        for pos in queue:
            d = dist[pos]
            for nb in grid.neighbors(pos):
                if nb != pos and nb not in dist:
                    dist[nb] = d + 1
                    nxt.append(nb)
        queue = nxt
    return dist
