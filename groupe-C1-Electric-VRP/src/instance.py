from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional
from math import sqrt, ceil
import re
import numpy as np


def evrptw_instances_dir() -> Path:
    return Path(__file__).resolve().parent.parent / 'data' / 'evrptw_instances'
DEPOT = 0
CUSTOMER = 1
STATION = 2
DIST_SCALE = 10
ENERGY_SCALE = 100
SLOPE_SCALE = 1000

@dataclass
class EVRPInstance:
    coords: List[Tuple[float, float]]
    node_types: List[int]
    demands: List[int]
    time_windows: List[Tuple[int, int]]
    service_times: List[int]
    n_vehicles: int
    vehicle_capacity: int
    battery_capacity: int
    consumption_rate: int
    load_sensitivity: float = 0.1
    speed_kmh: float = 60.0
    slope_matrix: Optional[List[List[int]]] = None
    slope_factor: float = 0.15

    def __post_init__(self):
        n = len(self.coords)
        self.n_nodes = n
        self.customer_indices = [i for i, t in enumerate(self.node_types) if t == CUSTOMER]
        self.station_indices = [i for i, t in enumerate(self.node_types) if t == STATION]
        self.n_customers = len(self.customer_indices)
        self.n_stations = len(self.station_indices)
        if self.slope_matrix is None:
            self.slope_matrix = [[0] * n for _ in range(n)]
        self._dist = self._build_dist_matrix(n)
        self._energy = self._build_energy_matrix(n)
        self._time = self._build_time_matrix(n)

    def _build_dist_matrix(self, n: int) -> List[List[int]]:
        d = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    dx = self.coords[i][0] - self.coords[j][0]
                    dy = self.coords[i][1] - self.coords[j][1]
                    d[i][j] = int(round(sqrt(dx ** 2 + dy ** 2) * DIST_SCALE))
        return d

    def _build_energy_matrix(self, n: int) -> List[List[int]]:
        e = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    base = self.consumption_rate * self._dist[i][j] // DIST_SCALE
                    slope_pct = self.slope_matrix[i][j]
                    multiplier = 1.0 + self.slope_factor * slope_pct / SLOPE_SCALE
                    e[i][j] = max(0, int(round(base * multiplier)))
        return e

    def _build_time_matrix(self, n: int) -> List[List[int]]:
        t = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    real_km = self._dist[i][j] / DIST_SCALE
                    t[i][j] = int(ceil(real_km / self.speed_kmh * 60))
        return t

    def dist(self, i: int, j: int) -> int:
        return self._dist[i][j]

    def energy(self, i: int, j: int, load: int=0) -> int:
        base = self._energy[i][j]
        bonus = int(base * self.load_sensitivity * load / max(self.vehicle_capacity, 1))
        return base + bonus

    def travel_time(self, i: int, j: int) -> int:
        return self._time[i][j]

    def total_demand(self) -> int:
        return sum(self.demands)

    def with_n_vehicles(self, n_vehicles: int) -> 'EVRPInstance':
        k = max(1, int(n_vehicles))
        sm = self.slope_matrix
        if sm is not None:
            sm = [list(row) for row in sm]
        return type(self)(coords=list(self.coords), node_types=list(self.node_types), demands=list(self.demands), time_windows=list(self.time_windows), service_times=list(self.service_times), n_vehicles=k, vehicle_capacity=self.vehicle_capacity, battery_capacity=self.battery_capacity, consumption_rate=self.consumption_rate, load_sensitivity=self.load_sensitivity, speed_kmh=self.speed_kmh, slope_matrix=sm, slope_factor=self.slope_factor)

    @classmethod
    def random(cls, n_customers: int=10, n_stations: int=3, seed: int=42, n_vehicles: int=3, vehicle_capacity: int=100, with_slope: bool=True) -> EVRPInstance:
        rng = np.random.default_rng(seed)
        coords = [(50.0, 50.0)]
        node_types = [DEPOT]
        demands = [0]
        time_windows = [(0, 1440)]
        service_times = [0]
        for _ in range(n_customers):
            coords.append((float(rng.uniform(5, 95)), float(rng.uniform(5, 95))))
            node_types.append(CUSTOMER)
            demands.append(int(rng.integers(10, 40)))
            tw_open = int(rng.integers(0, 600))
            time_windows.append((tw_open, tw_open + int(rng.integers(120, 600))))
            service_times.append(15)
        for _ in range(n_stations):
            coords.append((float(rng.uniform(10, 90)), float(rng.uniform(10, 90))))
            node_types.append(STATION)
            demands.append(0)
            time_windows.append((0, 1440))
            service_times.append(0)
        n = 1 + n_customers + n_stations
        slope_matrix = None
        if with_slope:
            raw = rng.integers(-500, 500, size=(n, n))
            np.fill_diagonal(raw, 0)
            for i in range(n):
                for j in range(i + 1, n):
                    raw[j][i] = -raw[i][j]
            slope_matrix = raw.tolist()
        return cls(coords=coords, node_types=node_types, demands=demands, time_windows=time_windows, service_times=service_times, n_vehicles=n_vehicles, vehicle_capacity=vehicle_capacity, battery_capacity=4000, consumption_rate=2, load_sensitivity=0.1, slope_matrix=slope_matrix, slope_factor=0.15)

    @classmethod
    def schneider_like(cls, n_customers: int=10, seed: int=42, with_slope: bool=False) -> 'EVRPInstance':
        import math
        rng = np.random.default_rng(seed)
        n_stations = max(1, n_customers // 3)
        n_vehicles = math.ceil(n_customers / 5)
        coords = [(50.0, 50.0)]
        node_types = [DEPOT]
        demands = [0]
        time_windows = [(0, 1236)]
        service_times = [0]
        for _ in range(n_customers):
            coords.append((float(rng.uniform(0, 100)), float(rng.uniform(0, 100))))
            node_types.append(CUSTOMER)
            demands.append(int(rng.integers(1, 40)))
            tw_open = int(rng.integers(0, 900))
            time_windows.append((tw_open, min(1236, tw_open + int(rng.integers(90, 400)))))
            service_times.append(90)
        for _ in range(n_stations):
            coords.append((float(rng.uniform(0, 100)), float(rng.uniform(0, 100))))
            node_types.append(STATION)
            demands.append(0)
            time_windows.append((0, 1236))
            service_times.append(0)
        n = 1 + n_customers + n_stations
        slope_matrix = None
        if with_slope:
            raw = rng.integers(-300, 300, size=(n, n))
            np.fill_diagonal(raw, 0)
            for i in range(n):
                for j in range(i + 1, n):
                    raw[j][i] = -raw[i][j]
            slope_matrix = raw.tolist()
        return cls(coords=coords, node_types=node_types, demands=demands, time_windows=time_windows, service_times=service_times, n_vehicles=n_vehicles, vehicle_capacity=200, battery_capacity=7775, consumption_rate=10, load_sensitivity=0.0, slope_matrix=slope_matrix, slope_factor=0.15)

    @classmethod
    def from_file(cls, filepath: str) -> 'EVRPInstance':
        vehicle_capacity = 200
        battery_kwh = 77.75
        r_rate = 1.0
        v_speed = 1.0
        depot_block: List[Tuple[float, float, int, Tuple[int, int], int]] = []
        customers_raw: List[Tuple[int, float, float, int, Tuple[int, int], int]] = []
        stations_raw: List[Tuple[int, float, float, int, Tuple[int, int], int]] = []
        float_in_slashes = re.compile('/\\s*([+-]?\\d+(?:\\.\\d+)?(?:[eE][+-]?\\d+)?)\\s*/')
        with open(filepath, 'r', encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                parts = line.split()
                if not parts:
                    continue
                low0 = parts[0].lower()
                if low0 == 'q':
                    m = float_in_slashes.search(line)
                    if m:
                        battery_kwh = float(m.group(1))
                    continue
                if line.startswith('C Vehicle') or (low0 == 'c' and 'capacity' in line.lower()):
                    m = float_in_slashes.search(line)
                    if m:
                        vehicle_capacity = int(round(float(m.group(1))))
                    continue
                if low0 == 'r' and 'fuel' in line.lower():
                    m = float_in_slashes.search(line)
                    if m:
                        r_rate = float(m.group(1))
                    continue
                if low0 == 'g':
                    continue
                if low0 == 'v':
                    m = float_in_slashes.search(line)
                    if m:
                        v_speed = float(m.group(1))
                    continue
                if low0.startswith('string'):
                    continue
                if len(parts) < 8:
                    continue
                kind = parts[1].lower()
                if kind not in ('d', 'c', 'f'):
                    continue
                sid = parts[0]
                x = float(parts[2])
                y = float(parts[3])
                demand = int(round(float(parts[4])))
                a = int(round(float(parts[5])))
                b = int(round(float(parts[6])))
                serv = int(round(float(parts[7])))
                if kind == 'd':
                    depot_block.append((x, y, demand, (a, b), serv))
                elif kind == 'c':
                    num = int(sid[1:]) if sid.upper().startswith('C') and sid[1:].isdigit() else len(customers_raw)
                    customers_raw.append((num, x, y, demand, (a, b), serv))
                else:
                    num = int(sid[1:]) if sid.upper().startswith('S') and sid[1:].isdigit() else len(stations_raw)
                    stations_raw.append((num, x, y, demand, (a, b), serv))
        if len(depot_block) != 1:
            raise ValueError(f"{filepath}: un unique nœud de type 'd' (dépôt) est requis, trouvé {len(depot_block)}.")
        if not customers_raw:
            raise ValueError(f"{filepath}: aucun client ('c') n'a été lu.")
        customers_raw.sort(key=lambda t: t[0])
        stations_raw.sort(key=lambda t: t[0])
        dx, dy, dd, dtw, dsv = depot_block[0]
        coords = [(dx, dy)]
        node_types = [DEPOT]
        demands = [dd]
        time_windows = [dtw]
        service_times = [dsv]
        for _, cx, cy, dem, tw, sv in customers_raw:
            coords.append((cx, cy))
            node_types.append(CUSTOMER)
            demands.append(dem)
            time_windows.append(tw)
            service_times.append(sv)
        for _, sx, sy, dem, tw, sv in stations_raw:
            coords.append((sx, sy))
            node_types.append(STATION)
            demands.append(dem)
            time_windows.append(tw)
            service_times.append(sv)
        battery_capacity = max(1, int(round(battery_kwh * ENERGY_SCALE)))
        consumption_rate = max(1, int(round(r_rate * 10)))
        speed_kmh = 60.0 if abs(v_speed - 1.0) < 1e-09 else max(1.0, float(v_speed))
        n_cust = len(customers_raw)
        n_vehicles = max(1, ceil(n_cust / 5))
        return cls(coords=coords, node_types=node_types, demands=demands, time_windows=time_windows, service_times=service_times, n_vehicles=n_vehicles, vehicle_capacity=vehicle_capacity, battery_capacity=battery_capacity, consumption_rate=consumption_rate, load_sensitivity=0.0, speed_kmh=speed_kmh, slope_matrix=None, slope_factor=0.15)

    @classmethod
    def from_benchmark(cls, name: str) -> 'EVRPInstance':
        return load_benchmark(name)


def load_benchmark(name: str) -> EVRPInstance:
    stem = name.strip()
    if not stem.endswith('.txt'):
        stem = f'{stem}.txt'
    path = evrptw_instances_dir() / stem
    if not path.is_file():
        raise FileNotFoundError(f'Fichier instance introuvable : {path}')
    return EVRPInstance.from_file(str(path))
