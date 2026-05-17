import numpy as np
import heapq
from ortools.sat.python import cp_model
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from shapely.geometry import Point, LineString, Polygon

@dataclass
class DroneInstance:
    depot: Tuple[float, float, float]
    clients: List[Tuple[float, float, float]]
    demands: List[int]      # Weight demands
    volumes: List[int]      # Volume demands
    notam_zones: List[List[Tuple[float, float]]]
    num_drones: int
    battery_capacity: int
    max_load: int           # Max weight capacity
    max_volume: int         # Max volume capacity
    wind_coeff: float = 1.0
    unloading_time: int = 5
    grid_res: int = 30

class WaypointNavigator:
    """Gère le contournement intelligent : Direct si possible, sinon Waypoints."""
    def __init__(self, instance: DroneInstance):
        self.inst = instance
        self.zones = [Polygon(z) for z in instance.notam_zones]
        self.interest_points = [instance.depot] + instance.clients
        self.waypoints = self._generate_safe_waypoints()
        self.all_nodes = self.interest_points + self.waypoints
        # On construit le graphe d'adjacence pour la grille
        self.adj = self._build_adjacency_list()

    def _generate_safe_waypoints(self) -> List[Tuple]:
        pts = np.array(self.interest_points)
        x_min, y_min = np.min(pts[:,0]) - 20, np.min(pts[:,1]) - 20
        x_max, y_max = np.max(pts[:,0]) + 20, np.max(pts[:,1]) + 20
        safe_pts = []
        for x in np.linspace(x_min, x_max, self.inst.grid_res):
            for y in np.linspace(y_min, y_max, self.inst.grid_res):
                p = Point(x, y)
                if not any(p.within(zone) for zone in self.zones):
                    safe_pts.append((float(x), float(y), 10.0))
        return safe_pts

    def is_safe(self, p1: Tuple, p2: Tuple) -> bool:
        """Vérifie si la ligne directe (x,y) est libre de NOTAM."""
        line = LineString([(p1[0], p1[1]), (p2[0], p2[1])])
        return not any(line.intersects(zone) for zone in self.zones)

    def _build_adjacency_list(self) -> Dict:
        adj = {i: [] for i in range(len(self.all_nodes))}
        for i in range(len(self.all_nodes)):
            for j in range(i + 1, len(self.all_nodes)):
                p1, p2 = self.all_nodes[i], self.all_nodes[j]
                dist = np.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))
                # Connexions locales pour Dijkstra
                if dist < 35 and self.is_safe(p1, p2):
                    adj[i].append((j, dist))
                    adj[j].append((i, dist))
        return adj

    def get_shortest_path_data(self, start_idx: int, end_idx: int) -> Tuple[float, List[Tuple]]:
        """Logique : Direct d'abord, Dijkstra sinon."""
        p_start = self.all_nodes[start_idx]
        p_end = self.all_nodes[end_idx]

        # 1. TENTATIVE DIRECTE (Règle d'or)
        if self.is_safe(p_start, p_end):
            dist = np.sqrt(sum((a - b) ** 2 for a, b in zip(p_start, p_end)))
            return dist, [p_start, p_end]

        # 2. REPLI SUR DIJKSTRA VIA WAYPOINTS
        queue = [(0.0, start_idx, [p_start])]
        visited = {start_idx: 0.0}
        while queue:
            (d, curr, path) = heapq.heappop(queue)
            if curr == end_idx: return d, path
            
            for (nxt, weight) in self.adj[curr]:
                new_dist = d + weight
                if nxt not in visited or new_dist < visited[nxt]:
                    visited[nxt] = new_dist
                    heapq.heappush(queue, (new_dist, nxt, path + [self.all_nodes[nxt]]))
                    
        return 999999.0, []

class DroneRoutingSolver:
    def __init__(self, instance: DroneInstance):
        self.inst = instance
        self.navigator = WaypointNavigator(instance)
        self.num_interest = len(instance.clients) + 1
        self.full_paths = {}
        self.dist_matrix = self._compute_matrix()
        
    def _compute_matrix(self) -> np.ndarray:
        n = self.num_interest
        matrix = np.zeros((n, n), dtype=int)
        for i in range(n):
            for j in range(i + 1, n):
                dist, path = self.navigator.get_shortest_path_data(i, j)
                matrix[i][j] = matrix[j][i] = int(dist * self.inst.wind_coeff * 100)
                self.full_paths[(i, j)] = path
                self.full_paths[(j, i)] = path[::-1]
        return matrix

    def solve(self, time_limit=30.0):
        model = cp_model.CpModel()
        n_n, n_k = self.num_interest, self.inst.num_drones
        arcs = {(i, j, k): model.NewBoolVar(f'a_{i}_{j}_{k}') for i in range(n_n) for j in range(n_n) for k in range(n_k) if i != j}
        battery = {(i, k): model.NewIntVar(0, self.inst.battery_capacity, f'b_{i}_{k}') for i in range(1, n_n) for k in range(n_k)}
        load = {(i, k): model.NewIntVar(0, self.inst.max_load, f'l_{i}_{k}') for i in range(1, n_n) for k in range(n_k)}
        vol_load = {(i, k): model.NewIntVar(0, self.inst.max_volume, f'v_{i}_{k}') for i in range(1, n_n) for k in range(n_k)}
        
        # Chaque client est visité exactement une fois
        for i in range(1, n_n):
            model.Add(sum(arcs[i, j, k] for j in range(n_n) for k in range(n_k) if i != j) == 1)
            
        for k in range(n_k):
            # Conservation du flux (pour chaque noeud, dont le dépôt)
            for j in range(n_n):
                model.Add(sum(arcs[i, j, k] for i in range(n_n) if i != j) == sum(arcs[j, l, k] for l in range(n_n) if j != l))
            
            # Contraintes pour batterie et charge (MTZ)
            for i in range(n_n):
                for j in range(1, n_n):
                    if i == j: continue
                    if i == 0:
                        # Départ du dépôt : reset complet (énergie + colis)
                        model.Add(battery[j, k] == self.inst.battery_capacity - self.dist_matrix[0, j]).OnlyEnforceIf(arcs[0, j, k])
                        model.Add(load[j, k] == self.inst.demands[j-1]).OnlyEnforceIf(arcs[0, j, k])
                        model.Add(vol_load[j, k] == self.inst.volumes[j-1]).OnlyEnforceIf(arcs[0, j, k])
                    else:
                        # Entre deux clients
                        model.Add(battery[j, k] == battery[i, k] - self.dist_matrix[i, j]).OnlyEnforceIf(arcs[i, j, k])
                        model.Add(load[j, k] == load[i, k] + self.inst.demands[j-1]).OnlyEnforceIf(arcs[i, j, k])
                        model.Add(vol_load[j, k] == vol_load[i, k] + self.inst.volumes[j-1]).OnlyEnforceIf(arcs[i, j, k])
            
            # Retour au dépôt : assez de batterie pour le trajet final
            for i in range(1, n_n):
                model.Add(battery[i, k] >= self.dist_matrix[i, 0]).OnlyEnforceIf(arcs[i, 0, k])

        model.Minimize(sum(arcs[i, j, k] * self.dist_matrix[i, j] for i, j, k in arcs))
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit
        status = solver.Solve(model)
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            routes = []
            for k in range(n_k):
                starts = [j for j in range(1, n_n) if solver.Value(arcs[0, j, k])]
                if not starts: continue
                
                drone_trips = []
                for start_node in starts:
                    trip_nodes = [0, start_node]
                    curr = start_node
                    while curr != 0:
                        found_next = False
                        for j in range(n_n):
                            if curr != j and solver.Value(arcs[curr, j, k]):
                                trip_nodes.append(j)
                                curr = j
                                found_next = True
                                break
                        if not found_next: break
                    
                    trip_geo = []
                    trip_dist, trip_w, trip_v = 0, 0, 0
                    for idx in range(len(trip_nodes) - 1):
                        u, v = trip_nodes[idx], trip_nodes[idx+1]
                        seg = self.full_paths[(u, v)]
                        if not trip_geo: trip_geo.extend(seg)
                        else: trip_geo.extend(seg[1:])
                        trip_dist += self.dist_matrix[u, v] / 100.0
                        if v > 0:
                            trip_w += self.inst.demands[v-1]
                            trip_v += self.inst.volumes[v-1]
                    
                    drone_trips.append({
                        'geometry': trip_geo,
                        'distance': round(trip_dist, 2),
                        'weight': trip_w,
                        'volume': trip_v
                    })
                
                if drone_trips:
                    routes.append({
                        'drone_id': k,
                        'trips': drone_trips,
                        'total_distance': round(sum(t['distance'] for t in drone_trips), 2),
                        'total_weight': sum(t['weight'] for t in drone_trips),
                        'total_volume': sum(t['volume'] for t in drone_trips)
                    })
            return routes
        return None

if __name__ == "__main__":
    print("--- DÉMARRAGE DU TEST ---")
    data = DroneInstance(
        depot=(20, 50, 0), 
        clients=[(10, 50, 10), (90, 50, 10), (20, 20, 10), (80, 80, 10)],
        demands=[50, 50, 50, 50],
        volumes=[100, 100, 100, 100],
        notam_zones=[],
        num_drones=2,
        battery_capacity=3000,
        max_load=150,
        max_volume=300
    )
    res = DroneRoutingSolver(data).solve()
    if res:
        for r in res:
            print(f"\nDrone {r['drone_id']} (Total dist: {r['total_distance']}km) :")
            for t_idx, t in enumerate(r['trips']):
                print(f"  Trip {t_idx}: {t['distance']}km, {t['weight']/10}kg, {t['volume']/10}L")
