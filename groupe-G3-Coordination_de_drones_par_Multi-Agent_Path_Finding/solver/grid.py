# solver/grid.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Set, Tuple

Pos = Tuple[int, ...]  # (row, col) pour 2D ; (row, col, alt) pour 3D


@dataclass
class Grid:
    rows: int
    cols: int
    alts: int = 1
    obstacles: Set[Pos] = field(default_factory=set)

    @property
    def positions(self) -> List[Pos]:
        if self.alts == 1:
            return [
                (r, c)
                for r in range(self.rows)
                for c in range(self.cols)
                if (r, c) not in self.obstacles
            ]
        return [
            (r, c, a)
            for r in range(self.rows)
            for c in range(self.cols)
            for a in range(self.alts)
            if (r, c, a) not in self.obstacles
        ]

    def neighbors(self, pos: Pos) -> List[Pos]:
        if len(pos) == 2:
            r, c = pos
            candidates = [(r, c), (r-1, c), (r+1, c), (r, c-1), (r, c+1)]
            return [
                (nr, nc) for nr, nc in candidates
                if 0 <= nr < self.rows and 0 <= nc < self.cols
                and (nr, nc) not in self.obstacles
            ]
        r, c, a = pos
        candidates = [
            (r, c, a), (r-1, c, a), (r+1, c, a),
            (r, c-1, a), (r, c+1, a),
            (r, c, a-1), (r, c, a+1),
        ]
        return [
            (nr, nc, na) for nr, nc, na in candidates
            if 0 <= nr < self.rows and 0 <= nc < self.cols and 0 <= na < self.alts
            and (nr, nc, na) not in self.obstacles
        ]

    def add_building(self, row: int, col: int, height: int) -> None:
        if self.alts == 1:
            self.obstacles.add((row, col))
        else:
            for a in range(height):
                self.obstacles.add((row, col, a))
