"""Modele de reference manuel : Sudoku 9x9."""

from ortools.sat.python import cp_model

GRID = [
    [5, 3, 0, 0, 7, 0, 0, 0, 0],
    [6, 0, 0, 1, 9, 5, 0, 0, 0],
    [0, 9, 8, 0, 0, 0, 0, 6, 0],
    [8, 0, 0, 0, 6, 0, 0, 0, 3],
    [4, 0, 0, 8, 0, 3, 0, 0, 1],
    [7, 0, 0, 0, 2, 0, 0, 0, 6],
    [0, 6, 0, 0, 0, 0, 2, 8, 0],
    [0, 0, 0, 4, 1, 9, 0, 0, 5],
    [0, 0, 0, 0, 8, 0, 0, 7, 9],
]


def solve() -> dict:
    model = cp_model.CpModel()

    cells = [[model.NewIntVar(1, 9, f"c_{r}_{c}") for c in range(9)] for r in range(9)]

    for r in range(9):
        for c in range(9):
            if GRID[r][c] != 0:
                model.Add(cells[r][c] == GRID[r][c])

    for r in range(9):
        model.AddAllDifferent(cells[r])
    for c in range(9):
        model.AddAllDifferent([cells[r][c] for r in range(9)])
    for br in range(3):
        for bc in range(3):
            block = [cells[3 * br + i][3 * bc + j] for i in range(3) for j in range(3)]
            model.AddAllDifferent(block)

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": solver.StatusName(status), "grid": None}

    return {
        "status": solver.StatusName(status),
        "grid": [[solver.Value(cells[r][c]) for c in range(9)] for r in range(9)],
    }


if __name__ == "__main__":
    print(solve())
