"""Modele de reference manuel : job shop scheduling avec minimisation du makespan."""

from ortools.sat.python import cp_model

# (machine_id, duree) par operation, dans l'ordre du job.
JOBS = [
    [(0, 10), (1, 5), (2, 20)],   # Job 1 : M1->M2->M3
    [(1, 10), (0, 10), (2, 10)],  # Job 2 : M2->M1->M3
    [(2, 5), (0, 15), (1, 10)],   # Job 3 : M3->M1->M2
]
N_MACHINES = 3
HORIZON = sum(d for job in JOBS for _, d in job)


def solve() -> dict:
    model = cp_model.CpModel()

    starts: dict[tuple[int, int], cp_model.IntVar] = {}
    intervals_by_machine: dict[int, list] = {m: [] for m in range(N_MACHINES)}
    job_ends: list = []

    for j, ops in enumerate(JOBS):
        prev_end = None
        for k, (m, d) in enumerate(ops):
            s = model.NewIntVar(0, HORIZON, f"s_{j}_{k}")
            e = model.NewIntVar(0, HORIZON, f"e_{j}_{k}")
            iv = model.NewIntervalVar(s, d, e, f"iv_{j}_{k}")
            starts[(j, k)] = s
            intervals_by_machine[m].append(iv)
            if prev_end is not None:
                model.Add(s >= prev_end)
            prev_end = e
        job_ends.append(prev_end)

    for m in range(N_MACHINES):
        model.AddNoOverlap(intervals_by_machine[m])

    makespan = model.NewIntVar(0, HORIZON, "makespan")
    model.AddMaxEquality(makespan, job_ends)
    model.Minimize(makespan)

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": solver.StatusName(status), "objective": None}

    schedule = {
        f"job_{j+1}_op_{k+1}": solver.Value(starts[(j, k)])
        for (j, k) in starts
    }

    return {
        "status": solver.StatusName(status),
        "objective": int(solver.ObjectiveValue()),
        "schedule": schedule,
    }


if __name__ == "__main__":
    print(solve())
