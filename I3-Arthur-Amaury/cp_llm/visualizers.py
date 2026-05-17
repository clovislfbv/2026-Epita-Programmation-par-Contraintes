"""Visualiseurs de solutions par type de probleme.

Chaque fonction prend le dict resultat (issu du solver, soit LLM soit reference)
et retourne un matplotlib.Figure prete a etre passee a st.pyplot. Si la donnee
attendue n'est pas presente dans le dict, retourne None (l'app affiche alors
juste le JSON brut).

Les fonctions sont tolerantes aux variations de clefs : le LLM utilise les
noms de variables de son VariableSet (ex: 'queens'), la reference utilise
ceux du modele manuel (ex: 'assignment'). On scanne en consequence.
"""

from __future__ import annotations

from typing import Any, Optional

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle


# ---------- utilitaires de recuperation tolerante ----------


def _find_list(result: dict, *candidates: str, item_type: type | None = None) -> list | None:
    for k in candidates:
        v = result.get(k)
        if isinstance(v, list) and (item_type is None or all(isinstance(x, item_type) for x in v)):
            return v
    for v in result.values():
        if isinstance(v, list) and v and (item_type is None or all(isinstance(x, item_type) for x in v)):
            return v
    return None


def _find_grid(result: dict, *candidates: str) -> list[list[int]] | None:
    for k in candidates:
        v = result.get(k)
        if isinstance(v, list) and v and isinstance(v[0], list):
            return v
    for v in result.values():
        if isinstance(v, list) and v and isinstance(v[0], list):
            return v
    return None


def _find_dict(result: dict, *candidates: str) -> dict | None:
    for k in candidates:
        v = result.get(k)
        if isinstance(v, dict):
            return v
    return None


def _reconstruct_grid(result: dict, *prefixes: str) -> Optional[list[list[int]]]:
    """Reconstruit une grille 2D depuis des clefs aplaties type `prefix_i_j: val`."""
    cells: dict[tuple[int, int], int] = {}
    for k, v in result.items():
        if not isinstance(v, (int, float)):
            continue
        for p in prefixes:
            pref = p + "_"
            if k.startswith(pref):
                tail = k[len(pref):]
                parts = tail.split("_")
                if len(parts) == 2:
                    try:
                        i, j = int(parts[0]), int(parts[1])
                        cells[(i, j)] = int(v)
                        break
                    except ValueError:
                        continue
    if not cells:
        return None
    n_rows = max(i for i, _ in cells) + 1
    n_cols = max(j for _, j in cells) + 1
    n = max(n_rows, n_cols)
    return [[cells.get((i, j), 0) for j in range(n)] for i in range(n)]


def _reconstruct_schedule(result: dict) -> Optional[dict]:
    """Reconstruit un schedule depuis des clefs LLM type `..._J_K: {start, end}`."""
    schedule: dict[str, int] = {}
    for k, v in result.items():
        start: Any = None
        if isinstance(v, dict):
            start = v.get("start", v.get("s"))
        elif isinstance(v, (int, float)):
            start = v
        else:
            continue
        if start is None:
            continue
        parts = k.rsplit("_", 2)
        if len(parts) == 3:
            try:
                j, op = int(parts[1]), int(parts[2])
                schedule[f"job_{j + 1}_op_{op + 1}"] = int(start)
            except ValueError:
                continue
    return schedule or None


def _reconstruct_scalars_with_prefix(result: dict, prefix: str) -> Optional[dict]:
    """Reconstruit un dict {nom: valeur} depuis des clefs `prefix_NAME: int`."""
    out: dict[str, int] = {}
    pref = prefix + "_"
    for k, v in result.items():
        if k.startswith(pref) and isinstance(v, (int, float)):
            name = k[len(pref):]
            out[name] = int(v)
    return out or None


# ---------- visualiseurs ----------


def viz_nqueens(result: dict) -> Optional[Figure]:
    assignment = _find_list(result, "assignment", "queens", "q", item_type=int)
    if not assignment:
        return None
    n = len(assignment)
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    for i in range(n):
        for j in range(n):
            color = "#f0d9b5" if (i + j) % 2 == 0 else "#b58863"
            ax.add_patch(Rectangle((j, n - 1 - i), 1, 1, facecolor=color, edgecolor="none"))
    for row, col in enumerate(assignment):
        ax.text(col + 0.5, n - 1 - row + 0.5, "♛", ha="center", va="center",
                fontsize=22, color="#222")
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"N-Queens (N={n})")
    return fig


def viz_sudoku(result: dict) -> Optional[Figure]:
    grid = _find_grid(result, "grid", "cells", "solution")
    if not grid:
        grid = _reconstruct_grid(result, "cell", "c", "x")
    if not grid:
        return None
    n = len(grid)
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.set_xlim(0, n); ax.set_ylim(0, n)
    ax.set_aspect("equal")
    for i in range(n):
        for j in range(n):
            v = grid[i][j]
            ax.text(j + 0.5, n - 1 - i + 0.5, str(v) if v else "",
                    ha="center", va="center", fontsize=14)
    for k in range(n + 1):
        lw = 2.0 if k % 3 == 0 else 0.4
        ax.plot([k, k], [0, n], color="#333", linewidth=lw)
        ax.plot([0, n], [k, k], color="#333", linewidth=lw)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Sudoku 9x9")
    return fig


def viz_graph_coloring(result: dict) -> Optional[Figure]:
    coloring = _find_list(result, "coloring", "color", "colors", "c", item_type=int)
    if not coloring:
        return None
    # Aretes hardcodees (correspond a l'enonce). Si l'enonce change, adapter ici.
    edges = [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (2, 4), (3, 4), (3, 5), (4, 5)]
    n = len(coloring)
    g = nx.Graph()
    g.add_nodes_from(range(n))
    g.add_edges_from(edges)
    palette = plt.get_cmap("tab10")
    node_colors = [palette(c % 10) for c in coloring]
    fig, ax = plt.subplots(figsize=(5, 4.5))
    nx.draw(g, pos=nx.spring_layout(g, seed=42), with_labels=True, ax=ax,
            node_color=node_colors, node_size=700, font_color="white",
            font_weight="bold", edge_color="#666")
    n_colors = result.get("n_colors") or (max(coloring) + 1)
    ax.set_title(f"Coloration ({n_colors} couleurs)")
    return fig


def viz_knapsack(result: dict) -> Optional[Figure]:
    selection = _find_list(result, "selection", "take", "selected", item_type=int)
    if selection is None:
        return None
    weights = [10, 20, 30, 15, 25, 5, 12]
    values = [60, 100, 120, 80, 110, 30, 50]
    n = len(weights)
    sel_set = set(selection) if selection and max(selection, default=-1) < n else set()
    if not sel_set and len(selection) == n:
        sel_set = {i for i, v in enumerate(selection) if v}
    colors = ["#2a9d8f" if i in sel_set else "#dddddd" for i in range(n)]
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    x = list(range(n))
    ax.bar(x, values, color=colors, edgecolor="#222")
    for i in range(n):
        ax.text(i, values[i] + 2, f"v{values[i]}\nw{weights[i]}",
                ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([f"Obj {i+1}" for i in range(n)])
    ax.set_ylabel("Valeur")
    total_v = sum(values[i] for i in sel_set)
    total_w = sum(weights[i] for i in sel_set)
    ax.set_title(f"Knapsack — selection : valeur={total_v}, poids={total_w}/50")
    return fig


def viz_bin_packing(result: dict) -> Optional[Figure]:
    assignment = _find_list(result, "assignment", "bin", "bins", item_type=int)
    if not assignment:
        return None
    sizes = [10, 20, 30, 40, 50]
    n_bins = max(assignment) + 1
    fig, ax = plt.subplots(figsize=(5, 4))
    palette = plt.get_cmap("Set3")
    bottom = [0] * n_bins
    for i, b in enumerate(assignment):
        ax.bar(b, sizes[i], bottom=bottom[b],
               color=palette(i % 12), edgecolor="#222",
               label=f"Obj{i+1} ({sizes[i]})")
        ax.text(b, bottom[b] + sizes[i] / 2, f"{sizes[i]}",
                ha="center", va="center", fontsize=10)
        bottom[b] += sizes[i]
    ax.axhline(60, color="red", linestyle="--", linewidth=1, label="capacite=60")
    ax.set_xticks(range(n_bins)); ax.set_xticklabels([f"Boite {b+1}" for b in range(n_bins)])
    ax.set_ylabel("Remplissage")
    ax.set_title(f"Bin packing — {n_bins} boites")
    ax.legend(loc="upper right", fontsize=7, ncol=2)
    return fig


def viz_tsp(result: dict) -> Optional[Figure]:
    route = _find_list(result, "route", "tour", "path")
    if not route:
        return None
    cities = ["A", "B", "C", "D"]
    # Coordonnees placebo (forme de carre)
    coords = {"A": (0, 1), "B": (1, 1), "C": (0, 0), "D": (1, 0)}
    fig, ax = plt.subplots(figsize=(5, 4.5))
    for c, (x, y) in coords.items():
        ax.scatter(x, y, s=600, c="#264653", edgecolors="black", zorder=2)
        ax.text(x, y, c, ha="center", va="center", color="white", fontsize=12,
                fontweight="bold", zorder=3)
    # Route : convertir indices -> noms
    if route and isinstance(route[0], int):
        route = [cities[i] for i in route]
    for a, b in zip(route, route[1:]):
        x1, y1 = coords[a]; x2, y2 = coords[b]
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color="#e76f51", lw=2),
                    zorder=1)
    ax.set_xlim(-0.3, 1.3); ax.set_ylim(-0.3, 1.3)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    obj = result.get("objective", "?")
    ax.set_title(f"TSP — circuit de longueur {obj}")
    return fig


def viz_vrp(result: dict) -> Optional[Figure]:
    routes = result.get("routes")
    if not isinstance(routes, list):
        return None
    # 6 noeuds : D=0, C1..C5
    labels = ["D", "C1", "C2", "C3", "C4", "C5"]
    coords = {0: (0.5, 0.5), 1: (0, 1), 2: (1, 1), 3: (1, 0.3), 4: (0.5, 0), 5: (0, 0.3)}
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    for i, (x, y) in coords.items():
        c = "#2a9d8f" if i == 0 else "#264653"
        ax.scatter(x, y, s=700 if i == 0 else 500, c=c, edgecolors="black", zorder=2)
        ax.text(x, y, labels[i], ha="center", va="center", color="white",
                fontsize=11, fontweight="bold", zorder=3)
    palette = ["#e76f51", "#f4a261", "#e9c46a"]
    for k, route in enumerate(routes):
        if len(route) <= 1:
            continue
        color = palette[k % len(palette)]
        for a, b in zip(route, route[1:]):
            x1, y1 = coords[a]; x2, y2 = coords[b]
            ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                        arrowprops=dict(arrowstyle="->", color=color, lw=2.2),
                        zorder=1)
    ax.set_xlim(-0.3, 1.3); ax.set_ylim(-0.3, 1.3)
    ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    obj = result.get("objective", "?")
    ax.set_title(f"VRP — {len([r for r in routes if len(r) > 1])} tournees, distance={obj}")
    return fig


def viz_job_shop(result: dict) -> Optional[Figure]:
    schedule = _find_dict(result, "schedule", "starts", "start")
    if not schedule:
        schedule = _reconstruct_schedule(result)
    if not schedule:
        return None
    # JOBS hardcodes (correspond a l'enonce). machine_id, duration.
    jobs = [
        [(0, 10), (1, 5), (2, 20)],
        [(1, 10), (0, 10), (2, 10)],
        [(2, 5), (0, 15), (1, 10)],
    ]
    palette = ["#e63946", "#2a9d8f", "#264653"]
    fig, ax = plt.subplots(figsize=(7, 3.5))
    for j, ops in enumerate(jobs):
        for k, (m, d) in enumerate(ops):
            # cle souple : job_1_op_1, j0_o0, etc.
            candidates = [
                f"job_{j+1}_op_{k+1}",
                f"j{j}_o{k}",
                f"start_{j}_{k}",
                f"s_{j}_{k}",
            ]
            s = next((schedule[c] for c in candidates if c in schedule), None)
            if s is None:
                continue
            ax.barh(m, d, left=s, color=palette[j % len(palette)],
                    edgecolor="#222", height=0.7)
            ax.text(s + d / 2, m, f"J{j+1}.{k+1}", ha="center", va="center",
                    color="white", fontsize=9, fontweight="bold")
    ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["M1", "M2", "M3"])
    ax.set_xlabel("Temps")
    obj = result.get("objective", "?")
    ax.set_title(f"Job-shop — makespan = {obj}")
    ax.invert_yaxis()
    return fig


def viz_diet(result: dict) -> Optional[Figure]:
    portions = _find_dict(result, "portions", "quantities", "x")
    if not portions:
        portions = _reconstruct_scalars_with_prefix(result, "portions")
    if not portions:
        portions = _reconstruct_scalars_with_prefix(result, "x")
    if not portions:
        return None
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    names = list(portions.keys())
    vals = [portions[n] for n in names]
    ax.barh(names, vals, color="#2a9d8f", edgecolor="#222")
    for i, v in enumerate(vals):
        ax.text(v + 0.05, i, str(v), va="center", fontsize=10)
    ax.set_xlabel("Portions")
    obj = result.get("objective", "?")
    ax.set_title(f"Diet — cout total = {obj} EUR")
    ax.invert_yaxis()
    return fig


def viz_magic_square(result: dict) -> Optional[Figure]:
    grid = _find_grid(result, "grid", "square", "cells")
    if not grid:
        grid = _reconstruct_grid(result, "cell", "c", "x", "m")
    if not grid:
        return None
    n = len(grid)
    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    ax.set_xlim(0, n); ax.set_ylim(0, n); ax.set_aspect("equal")
    cmap = plt.get_cmap("YlOrRd")
    vmax = n * n
    for i in range(n):
        for j in range(n):
            v = grid[i][j]
            ax.add_patch(Rectangle((j, n - 1 - i), 1, 1,
                                   facecolor=cmap(v / vmax), edgecolor="#222"))
            ax.text(j + 0.5, n - 1 - i + 0.5, str(v),
                    ha="center", va="center", fontsize=18, fontweight="bold")
    ax.set_xticks([]); ax.set_yticks([])
    total = sum(grid[0])
    ax.set_title(f"Carre magique {n}x{n} (somme={total})")
    return fig


# ---------- dispatcher ----------


_VIZ: dict[str, Any] = {
    "nqueens": viz_nqueens,
    "sudoku": viz_sudoku,
    "graph_coloring": viz_graph_coloring,
    "knapsack": viz_knapsack,
    "bin_packing": viz_bin_packing,
    "tsp": viz_tsp,
    "vrp": viz_vrp,
    "job_shop": viz_job_shop,
    "diet": viz_diet,
    "magic_square": viz_magic_square,
}


def render(problem_name: str, result: dict) -> Optional[Figure]:
    """Retourne une Figure matplotlib si un visualiseur existe pour le probleme."""
    fn = _VIZ.get(problem_name)
    if fn is None or not isinstance(result, dict):
        return None
    try:
        return fn(result)
    except Exception:
        return None
