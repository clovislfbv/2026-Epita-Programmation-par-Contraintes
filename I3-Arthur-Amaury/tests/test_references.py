"""Verifie que les modeles manuels de reference produisent des solutions valides."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REFERENCES = ROOT / "benchmark" / "references"


def _run(name: str) -> dict:
    return runpy.run_path(str(REFERENCES / f"{name}.py"))["solve"]()


def test_nqueens():
    result = _run("nqueens")
    assert result["status"] in ("OPTIMAL", "FEASIBLE")
    assignment = result["assignment"]
    assert len(assignment) == 8
    assert len(set(assignment)) == 8  # toutes colonnes differentes
    diag1 = [assignment[i] + i for i in range(8)]
    diag2 = [assignment[i] - i for i in range(8)]
    assert len(set(diag1)) == 8
    assert len(set(diag2)) == 8


def test_knapsack():
    result = _run("knapsack")
    assert result["status"] == "OPTIMAL"
    weights = [10, 20, 30, 15, 25, 5, 12]
    capacity = 50
    selection = result["selection"]
    total_weight = sum(weights[i] for i in selection)
    assert total_weight <= capacity
    assert result["value"] > 0


def test_graph_coloring():
    result = _run("graph_coloring")
    edges = [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4), (3, 5), (4, 5)]
    assert result["status"] == "OPTIMAL"
    coloring = result["coloring"]
    for u, v in edges:
        assert coloring[u] != coloring[v], f"Arete ({u},{v}) avec meme couleur"
    assert result["n_colors"] >= 3  # contient un triangle (0,1,2) -> >=3 couleurs


if __name__ == "__main__":
    test_nqueens()
    test_knapsack()
    test_graph_coloring()
    print("Tous les tests de reference passent.")
