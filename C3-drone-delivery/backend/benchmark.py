"""
Benchmark de scalabilité : nb clients / nb drones vs temps de résolution.
Génère un tableau CSV + affiche les résultats dans le terminal.
"""
import time
import csv
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from drone_delivery_solver import DroneInstance, DroneRoutingSolver

TIME_LIMIT = 15.0  # secondes par instance


def make_instance(n_clients: int, n_drones: int, seed: int = 42) -> DroneInstance:
    import random
    rng = random.Random(seed)
    clients = [(rng.uniform(10, 90), rng.uniform(10, 90), 0.0) for _ in range(n_clients)]
    demands = [rng.randint(20, 80) for _ in range(n_clients)]
    volumes = [rng.randint(20, 80) for _ in range(n_clients)]
    return DroneInstance(
        depot=(50.0, 50.0, 0.0),
        clients=clients,
        demands=demands,
        volumes=volumes,
        notam_zones=[],
        num_drones=n_drones,
        battery_capacity=99999,
        max_load=500,
        max_volume=500,
        grid_res=5,  # grille petite pour le benchmark
    )


def run_benchmark():
    configs = [
        (2, 1), (4, 1), (4, 2), (6, 2), (6, 3),
        (8, 2), (8, 3), (10, 2), (10, 3), (12, 3),
    ]

    results = []
    print(f"\n{'Clients':>8}  {'Drones':>6}  {'Statut':>10}  {'Temps (s)':>10}  {'Dist totale':>12}")
    print("-" * 56)

    for n_clients, n_drones in configs:
        inst = make_instance(n_clients, n_drones)
        solver = DroneRoutingSolver(inst)

        t0 = time.time()
        routes = solver.solve(time_limit=TIME_LIMIT)
        elapsed = round(time.time() - t0, 2)

        if routes:
            status = "FEASIBLE"
            total_dist = round(sum(r["total_distance"] for r in routes), 2)
        else:
            status = "NO SOL"
            total_dist = "-"

        print(f"{n_clients:>8}  {n_drones:>6}  {status:>10}  {elapsed:>10}  {str(total_dist):>12}")
        results.append({
            "n_clients": n_clients,
            "n_drones": n_drones,
            "status": status,
            "time_s": elapsed,
            "total_dist": total_dist,
        })

    # Export CSV
    out_path = os.path.join(os.path.dirname(__file__), "..", "benchmark_results.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["n_clients", "n_drones", "status", "time_s", "total_dist"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResultats exportes dans : {os.path.abspath(out_path)}")
    return results


if __name__ == "__main__":
    print("Benchmark scalabilite CP-SAT — Drone Delivery Routing")
    print(f"Time limit par instance : {TIME_LIMIT}s")
    run_benchmark()
