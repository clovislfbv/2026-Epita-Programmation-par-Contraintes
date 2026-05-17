"""Modele de reference manuel : carre magique 3x3."""

from ortools.sat.python import cp_model

N = 3
MAGIC_SUM = N * (N * N + 1) // 2  # 15 pour N=3


def solve() -> dict:
    model = cp_model.CpModel()

    cells = [[model.NewIntVar(1, N * N, f"c_{i}_{j}") for j in range(N)] for i in range(N)]
    flat = [cells[i][j] for i in range(N) for j in range(N)]

    model.AddAllDifferent(flat)

    for i in range(N):
        model.Add(sum(cells[i][j] for j in range(N)) == MAGIC_SUM)
        model.Add(sum(cells[j][i] for j in range(N)) == MAGIC_SUM)

    model.Add(sum(cells[i][i] for i in range(N)) == MAGIC_SUM)
    model.Add(sum(cells[i][N - 1 - i] for i in range(N)) == MAGIC_SUM)

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": solver.StatusName(status), "grid": None}

    return {
        "status": solver.StatusName(status),
        "grid": [[solver.Value(cells[i][j]) for j in range(N)] for i in range(N)],
    }


if __name__ == "__main__":
    print(solve())
