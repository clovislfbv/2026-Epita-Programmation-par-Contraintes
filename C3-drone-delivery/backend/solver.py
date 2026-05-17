import math
import time
from typing import List, Dict, Tuple

from ortools.sat.python import cp_model
from shapely.geometry import LineString, Polygon

from models import (
    Client, Drone, DroneRoute, DroneStop,
    ForbiddenZone, SolveRequest, SolveResponse,
)

SCALE = 100  # km * SCALE → int


# ---------- geometry ----------

def euclidean_km(a, b) -> float:
    lat_km = 111.0
    lng_km = 111.0 * math.cos(math.radians((a.lat + b.lat) / 2))
    return math.sqrt(((b.lat - a.lat) * lat_km) ** 2 + ((b.lng - a.lng) * lng_km) ** 2)


def path_blocked(p1, p2, zones: List[ForbiddenZone]) -> bool:
    line = LineString([(p1.lng, p1.lat), (p2.lng, p2.lat)])
    for z in zones:
        poly = Polygon([(pt.lng, pt.lat) for pt in z.polygon])
        if line.crosses(poly) or line.within(poly):
            return True
    return False


# ---------- solver ----------

def solve(req: SolveRequest) -> SolveResponse:
    t0 = time.time()
    depot = req.depot.position
    drones = req.drones
    weather = req.weather
    zones = req.forbidden_zones
    K = len(drones)

    # Zone pre-filter
    reachable, unreachable_ids = [], []
    for c in req.clients:
        if not path_blocked(depot, c.position, zones) and not path_blocked(c.position, depot, zones):
            reachable.append(c)
        else:
            unreachable_ids.append(c.id)

    clients = reachable
    N = len(clients)

    if N == 0:
        return SolveResponse(
            status="OPTIMAL",
            routes=[DroneRoute(drone_id=d.id, stops=[], total_distance=0,
                               total_weight=0, battery_remaining=100.0) for d in drones],
            unserved_clients=unreachable_ids,
            total_distance=0.0,
            solve_time_seconds=round(time.time() - t0, 2),
        )

    # Node 0 = depot, nodes 1..N = clients
    pos = [depot] + [c.position for c in clients]
    dist = [[int(euclidean_km(pos[i], pos[j]) * SCALE) for j in range(N + 1)]
            for i in range(N + 1)]
    eff_range = [int(d.max_range * weather.wind_factor * SCALE) for d in drones]

    model = cp_model.CpModel()

    # visit[d][i] = drone d visits client i (0-indexed)
    visit = [[model.new_bool_var(f"v_{d}_{i}") for i in range(N)] for d in range(K)]

    # Each client visited at most once
    for i in range(N):
        model.add(cp_model.LinearExpr.Sum([visit[d][i] for d in range(K)]) <= 1)

    # served[i] = 1 iff client i is delivered
    served = [model.new_bool_var(f"s_{i}") for i in range(N)]
    for i in range(N):
        model.add(served[i] == cp_model.LinearExpr.Sum([visit[d][i] for d in range(K)]))

    # Per-drone: routing via AddCircuit + capacity constraints
    # arc_bools[d][(i,j)] = BoolVar for arc i→j on drone d
    arc_bools: List[Dict[Tuple[int, int], cp_model.IntVar]] = []

    for d in range(K):
        ab: Dict[Tuple[int, int], cp_model.IntVar] = {}
        circuit_arcs = []

        # Depot self-loop (drone stays home)
        home = model.new_bool_var(f"home_{d}")
        circuit_arcs.append((0, 0, home))

        for i in range(1, N + 1):
            # Client self-loop = not visited
            skip = model.new_bool_var(f"skip_{d}_{i}")
            model.add(skip == visit[d][i - 1].negated())
            circuit_arcs.append((i, i, skip))

            # Arcs to/from depot
            for j in range(N + 1):
                if i == j:
                    continue
                var = model.new_bool_var(f"a_{d}_{i}_{j}")
                ab[(i, j)] = var
                circuit_arcs.append((i, j, var))

        # Depot → client arcs
        for j in range(1, N + 1):
            var = model.new_bool_var(f"a_{d}_0_{j}")
            ab[(0, j)] = var
            circuit_arcs.append((0, j, var))

        model.add_circuit(circuit_arcs)
        arc_bools.append(ab)

        # Force depot into circuit if any client is visited (prevents isolated cycles)
        for i in range(N):
            model.add(home == 0).only_enforce_if(visit[d][i])

        # Autonomy
        model.add(
            cp_model.LinearExpr.WeightedSum(
                list(ab.values()),
                [dist[i][j] for (i, j) in ab.keys()]
            ) <= eff_range[d]
        )

        # Weight capacity
        model.add(
            cp_model.LinearExpr.WeightedSum(
                [visit[d][i] for i in range(N)],
                [int(clients[i].weight * SCALE) for i in range(N)]
            ) <= int(drones[d].max_weight * SCALE)
        )

        # Volume capacity
        model.add(
            cp_model.LinearExpr.WeightedSum(
                [visit[d][i] for i in range(N)],
                [int(clients[i].volume * SCALE) for i in range(N)]
            ) <= int(drones[d].max_volume * SCALE)
        )

    # Objective: maximize weighted deliveries, minimize travel
    all_ab_vars = [v for ab in arc_bools for v in ab.values()]
    all_ab_dists = [dist[i][j] for ab in arc_bools for (i, j) in ab.keys()]

    model.maximize(
        cp_model.LinearExpr.WeightedSum(
            served, [clients[i].priority * 100_000 for i in range(N)]
        ) - cp_model.LinearExpr.WeightedSum(all_ab_vars, all_ab_dists)
    )

    # -------- Solve --------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = req.time_limit_seconds
    solver.parameters.num_search_workers = 4

    status_code = solver.solve(model)
    STATUS = {cp_model.OPTIMAL: "OPTIMAL", cp_model.FEASIBLE: "FEASIBLE",
              cp_model.INFEASIBLE: "INFEASIBLE", cp_model.UNKNOWN: "UNKNOWN"}
    status = STATUS.get(status_code, "UNKNOWN")

    # -------- Reconstruct routes --------
    routes = []
    served_ids: set = set()

    if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for d in range(K):
            ab = arc_bools[d]

            # Walk circuit from depot
            stops = []
            route_dist = 0.0
            cur = 0
            visited_set: set = set()

            for _ in range(N):
                moved = False
                for j in range(1, N + 1):
                    if j in visited_set:
                        continue
                    if (cur, j) in ab and solver.value(ab[(cur, j)]) == 1:
                        seg = euclidean_km(pos[cur], pos[j])
                        route_dist += seg
                        c = clients[j - 1]
                        stops.append(DroneStop(
                            client_id=c.id,
                            position=c.position,
                            arrival_distance=round(seg, 3),
                            cumulative_distance=round(route_dist, 3),
                        ))
                        served_ids.add(c.id)
                        visited_set.add(j)
                        cur = j
                        moved = True
                        break
                if not moved:
                    break

            if stops:
                route_dist += euclidean_km(pos[cur], depot)

            eff_km = drones[d].max_range * weather.wind_factor
            battery = max(0.0, (1 - route_dist / eff_km) * 100) if eff_km > 0 else 0.0
            total_w = sum(clients[s.client_id - 1].weight
                          for s in stops
                          if 0 < s.client_id <= len(clients)) if stops else 0.0

            routes.append(DroneRoute(
                drone_id=drones[d].id,
                stops=stops,
                total_distance=round(route_dist, 3),
                total_weight=round(total_w, 3),
                battery_remaining=round(battery, 1),
            ))

    unserved = unreachable_ids + [c.id for c in clients if c.id not in served_ids]

    return SolveResponse(
        status=status,
        routes=routes,
        unserved_clients=unserved,
        total_distance=round(sum(r.total_distance for r in routes), 3),
        solve_time_seconds=round(time.time() - t0, 2),
    )
